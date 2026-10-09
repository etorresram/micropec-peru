"""Construcción de las bases persona y hogar para un año de la ENAHO.

Fuentes: módulos 200 (miembros), 300 (educación), 500 (empleo e ingresos) y
Sumaria (ingresos, gastos y pobreza del hogar). Todos los montos monetarios se
expresan en soles corrientes por mes (los anuales de la ENAHO se dividen por 12).
"""
from __future__ import annotations

import glob

import numpy as np
import pandas as pd
import pyreadstat

from . import config as C

KEYS = ["conglome", "vivienda", "hogar"]

# Componentes del ingreso laboral individual del módulo 500 (anualizados,
# deflactados espacialmente e imputados por el INEI).
ING_LABORAL = ["i524a1", "i530a", "i538a1", "i541a", "d529t", "d536", "d540t", "d543", "d544t"]


def _leer(anio: int, patron: str, cols: list[str] | None) -> pd.DataFrame:
    archivos = [f for f in sorted(glob.glob(str(C.RAW / str(anio) / patron))) if "12g" not in f]
    if not archivos:
        raise FileNotFoundError(f"no existe {patron} para {anio}; corre 00_descargar.py")
    df, _ = pyreadstat.read_dta(archivos[0], usecols=cols)
    df.columns = [c.lower() for c in df.columns]
    for k in KEYS + ["codperso"]:
        if k in df:
            df[k] = df[k].astype(str).str.strip()
    return df


def construir(anio: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    # --- hogares (sumaria) --------------------------------------------------
    cols34 = KEYS + ["ubigeo", "dominio", "estrato", "factor07", "mieperho", "gashog2d", "inghog2d",
                     "linea", "linpe", "pobreza", "ingtrahd", "ingtexhd", "ingrenhd", "ingoexhd",
                     "ingtprhd", "ingtpuhd", "ingtpu01", "ingtpu02", "ingtpu03", "ingtpu04", "ingtpu05",
                     "ia01hd", "ia02hd", "ingnethd", "pagesphd", "ingindhd", "ingauthd", "insedlhd",
                     "paesechd", "ingseihd", "isecauhd", "ingexthd"]
    h = _leer(anio, "sumaria-*.dta", cols34)
    h = h.rename(columns={"factor07": "peso"})
    num = [c for c in h.columns if c not in KEYS + ["ubigeo"]]
    h[num] = h[num].astype(float)
    h["hhid"] = h.conglome + h.vivienda + h.hogar
    h["dpto"] = h.ubigeo.str[:2].astype(int)
    h["urbano"] = (h.estrato <= 5).astype(int)
    h["dominio"] = h.dominio.astype(int)
    h["gasto_pc"] = h.gashog2d / h.mieperho / 12          # gasto per cápita mensual
    h["ing_pc"] = h.inghog2d / h.mieperho / 12
    h["pobre"] = (h.pobreza <= 2).astype(int)
    h["pobre_ext"] = (h.pobreza == 1).astype(int)
    # ingresos no laborales mensuales del hogar
    h["tr_juntos"] = h.ingtpu01 / 12
    h["tr_p65"] = h.ingtpu03 / 12
    h["tr_pub_otros"] = (h.ingtpuhd - h.ingtpu01 - h.ingtpu03) / 12   # Beca 18, bono gas, bonos extraordinarios
    h["tr_privadas"] = h.ingtprhd / 12                                 # pensiones y transferencias internas
    h["remesas"] = h.ingtexhd / 12
    h["rentas"] = h.ingrenhd / 12
    h["alq_imputado"] = (h.ia01hd + h.ia02hd) / 12
    h["extraord"] = h.ingoexhd / 12
    lab_sum = h[["ingnethd", "pagesphd", "ingindhd", "ingauthd", "insedlhd", "paesechd",
                 "ingseihd", "isecauhd", "ingexthd"]].sum(axis=1) / 12
    h["lab_sumaria"] = lab_sum
    nolab = h[["tr_juntos", "tr_p65", "tr_pub_otros", "tr_privadas", "remesas", "rentas",
               "alq_imputado", "extraord"]].sum(axis=1)
    h["otros_nolab"] = (h.inghog2d / 12 - lab_sum - nolab).clip(lower=0)   # residuo (donaciones, especie, etc.)

    # --- personas (200 + 300 + 500) ----------------------------------------
    p = _leer(anio, "enaho01-*-200.dta", KEYS + ["codperso", "p203", "p204", "p207", "p208a", "facpob07"])
    p = p[(p.p204.astype(float) == 1) & (~p.p203.astype(float).isin([8, 9]))].copy()
    p["hhid"] = p.conglome + p.vivienda + p.hogar
    p["edad"] = p.p208a.astype(float)
    p["mujer"] = (p.p207.astype(float) == 2).astype(int)
    p["jefe"] = (p.p203.astype(float) == 1).astype(int)
    p["conyuge"] = (p.p203.astype(float) == 2).astype(int)
    p["peso_pob"] = p.facpob07.astype(float)

    e = _leer(anio, "enaho01a-*-300.dta", KEYS + ["codperso", "p301a", "p307"])
    e["educ"] = e.p301a.astype(float).map(C.educ_a_grupo)
    e["estudia"] = (e.p307.astype(float) == 1).astype(int)
    p = p.merge(e[KEYS + ["codperso", "educ", "estudia"]], how="left", on=KEYS + ["codperso"])
    p["educ"] = p.educ.fillna(1).astype(int)
    p["estudia"] = p.estudia.fillna(0).astype(int)

    cols5 = KEYS + ["codperso", "ocu500", "p506r4", "p507", "fac500a", "p558a1"] + ING_LABORAL
    if anio != 2024:
        cols5.append("ocupinf")
    t = _leer(anio, "enaho01a-*-500.dta", cols5)
    for c in ING_LABORAL + ["ocu500", "p506r4", "p507", "p558a1", "fac500a"] + (["ocupinf"] if anio != 2024 else []):
        t[c] = t[c].astype(float)
    t["ing_lab"] = t[ING_LABORAL].fillna(0).sum(axis=1) / 12
    t["sector"] = t.p506r4.map(C.ciiu_a_sector).fillna(0).astype(int)
    ocu = t.ocu500
    if anio != 2024:
        formal = (t.ocupinf == 2)
    else:
        formal = pd.Series(np.nan, index=t.index)   # el INEI no publicó ocupinf en 2024
    t["estado"] = np.select(
        [ocu == 1, ocu.isin([2, 3]), ocu == 4],
        [np.where(formal == True, 4, 3), 2, 1], default=0)   # noqa: E712
    if anio == 2024:
        # sin `ocupinf` oficial: se usa la formalidad imputada (microsim/informalidad.py)
        imp = pd.read_parquet(C.CLEAN / "informalidad_imputada_2024.parquet")
        t = t.merge(imp, how="left", on=KEYS + ["codperso"])
        t.loc[ocu == 1, "estado"] = np.where(t.loc[ocu == 1, "formal_imp"] == 1, 4, 3)
    t["afp"] = (t.p558a1 == 1).astype(int)
    t["independiente"] = t.p507.isin([1, 2]).astype(int)
    t.loc[t.estado != 3, "estado"] = t.loc[t.estado != 3, "estado"]
    t.loc[~t.estado.isin([3, 4]), "sector"] = 0
    t.loc[~t.estado.isin([3, 4]), "ing_lab"] = 0.0
    p = p.merge(t[KEYS + ["codperso", "estado", "sector", "ing_lab", "afp", "independiente", "fac500a"]],
                how="left", on=KEYS + ["codperso"])
    p["estado"] = p.estado.fillna(0).astype(int)
    # Los adultos sin respuesta laboral se conservan como inactivos (supuesto
    # explícito; evita estimar una quinta categoría "menor de 14" entre adultos).
    p.loc[(p.edad >= 14) & (p.estado == 0), "estado"] = 1
    p.loc[p.edad < 14, "estado"] = 0
    p["sector"] = p.sector.fillna(0).astype(int)
    p["ing_lab"] = p.ing_lab.fillna(0.0)
    p["afp"] = p.afp.fillna(0).astype(int)
    p["independiente"] = p.independiente.fillna(0).astype(int)
    p["gedad"] = p.edad.map(C.grupo_edad).astype(int)

    # variables de hogar para los modelos
    p = p.merge(h[["hhid", "peso", "urbano", "dominio", "dpto"]], on="hhid", how="inner")
    comp = p.groupby("hhid").agg(n_menores=("edad", lambda s: (s < 14).sum()),
                                 n_adultos=("edad", lambda s: (s >= 14).sum()),
                                 n_ocupados=("estado", lambda s: s.isin([3, 4]).sum())).reset_index()
    p = p.merge(comp, on="hhid")
    p["otros_ocupados"] = p.n_ocupados - p.estado.isin([3, 4]).astype(int)

    # ingreso laboral agregado por hogar (módulo 500) para cerrar la cuenta del hogar
    lab_hh = p.groupby("hhid").ing_lab.sum().rename("lab_500")
    h = h.merge(lab_hh, on="hhid", how="left")
    h["lab_500"] = h.lab_500.fillna(0.0)
    # Mantener el ingreso individual observado y cerrar exactamente la Sumaria.
    # Es una discrepancia estadística firmada, no una transferencia ni renta.
    h["ajuste_contable"] = h.ing_pc * h.mieperho - h.lab_500 - h[[
        "tr_juntos", "tr_p65", "tr_pub_otros", "tr_privadas", "remesas", "rentas",
        "alq_imputado", "extraord", "otros_nolab"]].sum(axis=1)
    h = h.merge(comp, on="hhid", how="left")
    h["anio"] = anio
    p["anio"] = anio

    cols_h = ["hhid", "anio", "peso", "mieperho", "dpto", "dominio", "urbano", "gasto_pc", "ing_pc", "linea",
              "linpe", "pobre", "pobre_ext", "lab_500", "lab_sumaria", "tr_juntos", "tr_p65", "tr_pub_otros",
              "tr_privadas", "remesas", "rentas", "alq_imputado", "extraord", "otros_nolab",
              "ajuste_contable", "n_menores", "n_adultos", "n_ocupados"]
    cols_p = ["hhid", "anio", "codperso", "peso", "peso_pob", "edad", "gedad", "mujer", "jefe", "conyuge",
              "educ", "estudia", "estado", "sector", "ing_lab", "afp", "independiente", "urbano", "dominio",
              "dpto", "n_menores", "n_adultos", "otros_ocupados"]
    return p[cols_p].reset_index(drop=True), h[cols_h].reset_index(drop=True)


def guardar(anio: int) -> None:
    C.CLEAN.mkdir(parents=True, exist_ok=True)
    p, h = construir(anio)
    p.to_parquet(C.CLEAN / f"personas_{anio}.parquet", index=False)
    h.to_parquet(C.CLEAN / f"hogares_{anio}.parquet", index=False)
    w = h.peso * h.mieperho
    print(f"{anio}: {len(h):,} hogares, {len(p):,} personas | pobreza {np.average(h.pobre, weights=w):.3%} "
          f"| extrema {np.average(h.pobre_ext, weights=w):.3%}")


def cargar(anio: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (pd.read_parquet(C.CLEAN / f"personas_{anio}.parquet"),
            pd.read_parquet(C.CLEAN / f"hogares_{anio}.parquet"))
