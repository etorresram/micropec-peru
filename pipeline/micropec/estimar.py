"""Modelo base: elección ocupacional y ecuaciones de ingreso laboral (año base).

1. Logit multinomial del estado laboral (inactivo, desocupado, ocupado informal,
   ocupado formal) para las personas de 14 años y más.
2. Logit multinomial del sector de actividad (6 sectores) para los ocupados.
3. Ecuaciones de Mincer por segmento (informal / formal) del log del ingreso
   laboral mensual, con residuos conservados.

El producto es una base de personas con las probabilidades predichas (que ordenan
quién cambia de estado cuando cambian los agregados) y con los ingresos
potenciales en cada segmento (predicción + residuo propio o residuo sorteado).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import config as C

SEMILLA = 20261008


def _X(p: pd.DataFrame, con_sector: bool = False, con_formal: bool = False) -> pd.DataFrame:
    X = pd.DataFrame({
        "const": 1.0,
        "edad": p.edad, "edad2": p.edad ** 2 / 100,
        "mujer": p.mujer, "jefe": p.jefe, "conyuge": p.conyuge, "estudia": p.estudia,
        "educ2": (p.educ == 2).astype(int), "educ3": (p.educ == 3).astype(int), "educ4": (p.educ == 4).astype(int),
        "urbano": p.urbano, "n_menores": p.n_menores, "n_adultos": p.n_adultos,
        "mujer_menores": p.mujer * p.n_menores,
    }, index=p.index)
    for d in range(2, 9):
        X[f"dom{d}"] = (p.dominio == d).astype(int)
    if con_formal:
        X["formal"] = (p.estado == 4).astype(int)
    if con_sector:
        for s in range(2, 7):
            X[f"sec{s}"] = (p.sector == s).astype(int)
    return X.astype(float)


def _mnl(y: pd.Series, X: pd.DataFrame, nombre: str):
    cats = sorted(y.unique())
    ycode = y.map({c: i for i, c in enumerate(cats)})
    mod = sm.MNLogit(ycode.values, X.values)
    res = mod.fit(method="newton", maxiter=200, disp=False)
    probs = pd.DataFrame(res.predict(X.values), index=X.index, columns=[f"{nombre}_{c}" for c in cats])
    acc = float((probs.values.argmax(axis=1) == ycode.values).mean())
    return res, probs, cats, acc


def estimar(p: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(SEMILLA)
    q = p[p.edad >= 14].copy()
    resumen = {"n_14mas": int(len(q))}

    # 1. estado laboral --------------------------------------------------------
    X1 = _X(q)
    res1, pr1, cats1, acc1 = _mnl(q.estado, X1, "p_estado")
    q = q.join(pr1)
    q["p_ocupado"] = q.p_estado_3 + q.p_estado_4
    q["p_desocupado_c"] = q.p_estado_2 / (q.p_estado_1 + q.p_estado_2)          # P(desocupado | no ocupado)
    q["p_formal_c"] = q.p_estado_4 / (q.p_estado_3 + q.p_estado_4)              # P(formal | ocupado)
    resumen["mnl_estado"] = {"acierto": acc1, "pseudo_r2": float(res1.prsquared), "llf": float(res1.llf),
                             "variables": list(X1.columns), "categorias": [int(c) for c in cats1]}

    # 2. sector ----------------------------------------------------------------
    oc = q[q.estado.isin([3, 4]) & (q.sector > 0)]
    X2 = _X(oc, con_formal=True)
    res2, pr2, cats2, acc2 = _mnl(oc.sector, X2, "p_sector")
    # predicción para todos (ocupados y no ocupados); para no ocupados, formal según p_formal_c > 0.5
    X2all = _X(q, con_formal=True)
    noc = ~q.estado.isin([3, 4])
    X2all.loc[noc, "formal"] = (q.loc[noc, "p_formal_c"] > 0.5).astype(float)
    pr2all = pd.DataFrame(res2.predict(X2all.values), index=q.index, columns=[f"p_sector_{c}" for c in cats2])
    q = q.join(pr2all)
    resumen["mnl_sector"] = {"acierto": acc2, "pseudo_r2": float(res2.prsquared), "variables": list(X2.columns),
                             "categorias": [int(c) for c in cats2]}

    # 3. ecuaciones de ingreso por segmento -----------------------------------
    q["sector_pot"] = np.where(q.sector > 0, q.sector, pr2all.values.argmax(axis=1) + 1)
    coef_sector = {}
    for seg, nombre in [(3, "informal"), (4, "formal")]:
        m = q[(q.estado == seg) & (q.ing_lab > 0)]
        Xm = _X(m, con_sector=True)
        y = np.log(m.ing_lab)
        ols = sm.WLS(y, Xm, weights=m.peso).fit()
        resid = ols.resid
        # predicción para todos con el sector potencial
        qq = q.copy()
        qq["sector"] = q.sector_pot
        Xall = _X(qq, con_sector=True)
        xb = pd.Series(Xall.values @ ols.params.values, index=q.index)
        res_prop = pd.Series(np.nan, index=q.index)
        res_prop.loc[m.index] = resid.values
        # residuo sorteado (empírico) para quienes no están en el segmento
        falta = res_prop.isna()
        res_prop.loc[falta] = rng.choice(resid.values, size=int(falta.sum()), replace=True)
        q[f"y_pot_{nombre}"] = np.exp(xb + res_prop)
        coef_sector[nombre] = [0.0] + [float(ols.params[f"sec{s}"]) for s in range(2, 7)]
        resumen[f"mincer_{nombre}"] = {"n": int(len(m)), "r2": float(ols.rsquared), "sigma": float(resid.std()),
                                       "coef": {k: float(v) for k, v in ols.params.items()}}
    # para quienes están ocupados con ingreso, el potencial del propio segmento es el observado
    for seg, nombre in [(3, "informal"), (4, "formal")]:
        mask = (q.estado == seg) & (q.ing_lab > 0)
        q.loc[mask, f"y_pot_{nombre}"] = q.loc[mask, "ing_lab"]
    resumen["coef_sector"] = coef_sector
    q["u"] = rng.uniform(size=len(q))        # sorteo fijo para escenarios con cobertura parcial (p. ej. retiros AFP)

    cols = ["hhid", "codperso", "peso", "edad", "gedad", "mujer", "educ", "urbano", "dominio", "dpto", "estado",
            "sector", "sector_pot", "ing_lab", "afp", "p_ocupado", "p_desocupado_c", "p_formal_c",
            "y_pot_informal", "y_pot_formal", "u"] + [f"p_sector_{s}" for s in range(1, 7)]
    return q[cols].reset_index(drop=True), resumen


def guardar(p: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    q, resumen = estimar(p)
    C.CLEAN.mkdir(parents=True, exist_ok=True)
    q.to_parquet(C.CLEAN / f"base_modelo_{C.ANIO_BASE}.parquet", index=False)
    C.OUT.mkdir(parents=True, exist_ok=True)
    with open(C.OUT / "resumen_estimacion.json", "w") as f:
        json.dump(resumen, f, indent=1, ensure_ascii=False)
    return q, resumen
