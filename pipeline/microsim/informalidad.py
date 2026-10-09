"""Imputación de la informalidad laboral para la ENAHO 2024.

El INEI no incluyó la variable `ocupinf` en la base pública 2024. Se entrena un
logit sobre la ENAHO 2023 con las variables que determinan la definición oficial
(categoría ocupacional, registro en SUNAT, tipo de contrato, tamaño de la
empresa, afiliación a pensiones, sector, educación, edad y área) y se aplica a
2024. La precisión fuera de muestra se reporta en output/resumen_informalidad.json.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pyreadstat
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import config as C

VARS = ["conglome", "vivienda", "hogar", "codperso", "ocu500", "p507", "p510", "p510a1", "p511a", "p512a",
        "p558a1", "p558a2", "p558a3", "p558a4", "p558a5", "p506r4", "p208a", "p301a", "estrato", "fac500a"]


def _leer(anio: int) -> pd.DataFrame:
    import glob
    f = sorted(glob.glob(str(C.RAW / str(anio) / "enaho01a-*-500.dta")))[0]
    cols = VARS + (["ocupinf"] if anio != 2024 else [])
    df, _ = pyreadstat.read_dta(f, usecols=cols)
    df.columns = [c.lower() for c in df.columns]
    for k in ["conglome", "vivienda", "hogar", "codperso"]:
        df[k] = df[k].astype(str).str.strip()
    for c in df.columns:
        if c not in ["conglome", "vivienda", "hogar", "codperso"]:
            df[c] = df[c].astype(float)
    return df[df.ocu500 == 1].copy()


def _X(d: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame({"const": 1.0}, index=d.index)
    for v, vals in [("p507", range(1, 8)), ("p510", range(1, 8)), ("p510a1", range(1, 5)),
                    ("p511a", range(1, 8)), ("p512a", range(1, 8))]:
        for k in list(vals)[1:]:
            X[f"{v}_{k}"] = (d[v] == k).astype(float)
        X[f"{v}_na"] = d[v].isna().astype(float)
    X["afp"] = (d.p558a1 == 1).astype(float)
    X["onp"] = ((d.p558a2 == 1) | (d.p558a3 == 1) | (d.p558a4 == 1)).astype(float)
    X["sin_pension"] = (d.p558a5 == 1).astype(float)
    sec = d.p506r4.map(C.ciiu_a_sector)
    for s in range(2, 7):
        X[f"sec{s}"] = (sec == s).astype(float)
    X["edad"] = d.p208a
    X["edad2"] = d.p208a ** 2 / 100
    educ = d.p301a.map(C.educ_a_grupo)
    for e in (2, 3, 4):
        X[f"educ{e}"] = (educ == e).astype(float)
    X["urbano"] = (d.estrato <= 5).astype(float)
    return X


def imputar() -> pd.DataFrame:
    C.CLEAN.mkdir(parents=True, exist_ok=True)
    tr = _leer(2023)
    te = _leer(2024)
    y = (tr.ocupinf == 2).astype(int).values          # 1 = formal
    X = _X(tr).values
    rng = np.random.default_rng(7)
    val = rng.uniform(size=len(tr)) < 0.25
    sc = StandardScaler().fit(X[~val])
    mod = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X[~val]), y[~val])
    p_val = mod.predict_proba(sc.transform(X[val]))[:, 1]
    acc = float(((p_val > 0.5) == (y[val] == 1)).mean())
    w_val = tr.fac500a.values[val]
    inf_obs = float(np.average(y[val] == 0, weights=w_val))
    inf_pred = float(np.average(p_val < 0.5, weights=w_val))
    sc = StandardScaler().fit(X)
    mod = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X), y)
    p24 = mod.predict_proba(sc.transform(_X(te).values))[:, 1]
    te["formal_imp"] = (p24 > 0.5).astype(int)
    inf24 = float(np.average(te.formal_imp == 0, weights=te.fac500a))
    resumen = {"acierto_validacion": acc, "informalidad_validacion_obs": inf_obs,
               "informalidad_validacion_pred": inf_pred, "informalidad_2024_imputada": inf24, "n_2023": int(len(tr)),
               "n_2024": int(len(te))}
    C.OUT.mkdir(exist_ok=True)
    json.dump(resumen, open(C.OUT / "resumen_informalidad.json", "w"), indent=1)
    out = te[["conglome", "vivienda", "hogar", "codperso", "formal_imp"]]
    out.to_parquet(C.CLEAN / "informalidad_imputada_2024.parquet", index=False)
    print(resumen)
    return out
