"""Indicadores de pobreza, desigualdad y distribución (ponderados)."""
from __future__ import annotations

import numpy as np


def gini(x: np.ndarray, w: np.ndarray) -> float:
    o = np.argsort(x)
    x, w = np.asarray(x, float)[o], np.asarray(w, float)[o]
    cw = np.cumsum(w)
    cx = np.cumsum(x * w)
    W, X = cw[-1], cx[-1]
    if X <= 0:
        return float("nan")
    # área bajo la curva de Lorenz (trapecios)
    lx = cx / X
    lw = cw / W
    area = np.sum((lw - np.concatenate([[0], lw[:-1]])) * (lx + np.concatenate([[0], lx[:-1]])) / 2)
    return float(1 - 2 * area)


def cuantiles_pond(x: np.ndarray, w: np.ndarray, q: np.ndarray) -> np.ndarray:
    o = np.argsort(x)
    x, w = np.asarray(x, float)[o], np.asarray(w, float)[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(q, cw, x)


def medias_por_decil(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    cortes = cuantiles_pond(x, w, np.arange(1, 10) / 10)
    dec = np.searchsorted(cortes, x, side="right")
    return np.array([np.average(x[dec == d], weights=w[dec == d]) for d in range(10)])


def resumen(gasto_pc, ing_pc, linea, linpe, w, urbano=None, dominio=None, dpto=None, gasto_pc_base=None) -> dict:
    gasto_pc, ing_pc, linea, linpe, w = map(lambda a: np.asarray(a, float), (gasto_pc, ing_pc, linea, linpe, w))
    pobre = gasto_pc < linea
    ext = gasto_pc < linpe
    brecha = np.where(pobre, 1 - gasto_pc / linea, 0.0)
    out = {
        "pobreza": float(np.average(pobre, weights=w)),
        "pobreza_extrema": float(np.average(ext, weights=w)),
        "brecha": float(np.average(brecha, weights=w)),
        "severidad": float(np.average(brecha ** 2, weights=w)),
        "n_pobres": float((w * pobre).sum()),
        "n_pobres_ext": float((w * ext).sum()),
        "poblacion": float(w.sum()),
        "gini_gasto": gini(gasto_pc, w),
        "gini_ingreso": gini(np.clip(ing_pc, 0, None), w),
        "gasto_pc_medio": float(np.average(gasto_pc, weights=w)),
        "ing_pc_medio": float(np.average(ing_pc, weights=w)),
        "deciles_gasto": medias_por_decil(gasto_pc, w).tolist(),
    }
    if gasto_pc_base is not None:
        d0 = medias_por_decil(np.asarray(gasto_pc_base, float), w)
        out["gic"] = (out["deciles_gasto"] / d0 - 1).tolist()
    if urbano is not None:
        urbano = np.asarray(urbano)
        out["por_area"] = {("urbano" if u == 1 else "rural"): {
            "pobreza": float(np.average(pobre[urbano == u], weights=w[urbano == u])),
            "pobreza_extrema": float(np.average(ext[urbano == u], weights=w[urbano == u]))} for u in (1, 0)}
    if dominio is not None:
        dominio = np.asarray(dominio)
        out["por_dominio"] = {int(d): float(np.average(pobre[dominio == d], weights=w[dominio == d])) for d in np.unique(dominio)}
    if dpto is not None:
        dpto = np.asarray(dpto)
        out["por_dpto"] = {int(d): float(np.average(pobre[dpto == d], weights=w[dpto == d])) for d in np.unique(dpto)}
    return out
