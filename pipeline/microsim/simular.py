"""Motor de simulación: traduce un escenario macro a la distribución de los hogares.

Pasos (idénticos a los de la interfaz en JavaScript, gui/index.html):
 1. Reponderación: crecimiento poblacional (uniforme o calibrado por sexo x edad x área).
 2. Reasignación de estados laborales a las metas de ocupación, desempleo e
    informalidad, ordenando a las personas por sus probabilidades predichas.
 3. Reasignación sectorial a la estructura meta del empleo.
 4. Ingresos laborales: continuos (observado) o entrantes (potencial del segmento),
    reescalados por sector con el PBI sectorial por ocupado y la inflación.
 5. Ingresos no laborales: cada componente crece con su factor (transferencias,
    remesas, rentas, alquiler imputado); bonos y retiros extraordinarios.
 6. Gasto: elasticidad sobre ingreso real; consumo de políticas por separado.
 7. Líneas de pobreza actualizadas y cálculo de indicadores.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config as C
from . import indicadores as I

NOLAB = ["tr_juntos", "tr_p65", "tr_pub_otros", "tr_privadas", "remesas", "rentas", "alq_imputado", "extraord", "otros_nolab", "ajuste_contable"]
FACTORES_NOLAB = {"tr_juntos": "tr_juntos_factor", "tr_p65": "tr_p65_factor", "tr_pub_otros": "tr_pub_otros_factor",
                  "tr_privadas": "tr_privadas_factor", "remesas": "remesas_factor", "rentas": "rentas_factor",
                  "alq_imputado": "alq_factor", "extraord": "otros_factor", "otros_nolab": "otros_factor",
                  "ajuste_contable": "ipc"}


def escenario_base(laboral_base: dict) -> dict:
    """Escenario neutro: reproduce el año base."""
    return {
        "poblacion_factor": 1.0, "poblacion_grupos": None,
        "tasa_ocupacion": laboral_base["tasa_ocupacion"], "tasa_desempleo": laboral_base["tasa_desempleo"],
        "informalidad": laboral_base["informalidad"], "sector_shares": laboral_base["sector_shares"],
        "va_factor": [1.0] * 6, "passthrough": 1.0, "ipc": 1.0, "ing_lab_real_factor": None, "ing_lab_real_factor_sector": None, "ing_lab_real_factor_sector_area": None,
        "lineas_factor": None, "linea_factor_nacional": 1.0, "linpe_factor_nacional": 1.0,
        "tr_juntos_factor": 1.0, "tr_p65_factor": 1.0, "tr_pub_otros_factor": 1.0, "tr_privadas_factor": 1.0,
        "remesas_factor": 1.0, "rentas_factor": 1.0, "alq_factor": 1.0, "otros_factor": 1.0,
        "elasticidad_gasto": 1.0,
        "nolab_agregados": ["tr_juntos", "tr_p65", "tr_pub_otros", "remesas"],
        "bono": {"monto_anual": 0.0, "deciles": 0, "mpc": 1.0},
        "afp": {"cobertura": 0.0, "monto": 0.0, "mpc": 1.0},
    }


def validar_escenario(e, grupos_claves=None, hogares=None):
    """Rechaza escenarios no finitos o económicamente imposibles antes de simular."""
    def numero(x, lo, hi, nombre):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not np.isfinite(x) or not lo <= x <= hi:
            raise ValueError(f"Valor inválido: {nombre}")
    for k in ("ipc", "poblacion_factor", "linea_factor_nacional", "linpe_factor_nacional"):
        numero(e[k], 0.000001, 100, k)
    numero(e["tasa_ocupacion"], .000001, 1, "tasa_ocupacion")
    numero(e["tasa_desempleo"], 0, .999999, "tasa_desempleo")
    if e["tasa_ocupacion"] > 1 - e["tasa_desempleo"] + 1e-9:
        raise ValueError("Ocupación y desempleo implican una PEA mayor que la población de 14+")
    numero(e["informalidad"], 0, 1, "informalidad")
    numero(e["passthrough"], 0, 1, "passthrough")
    numero(e["elasticidad_gasto"], .01, 3, "elasticidad_gasto")
    def vector(v, nombre, lo=0):
        if not isinstance(v, (list, tuple)) or len(v) != 6:
            raise ValueError("Se necesitan seis valores: " + nombre)
        for x in v:
            numero(x, lo, 100, nombre)
    vector(e["sector_shares"], "sector_shares")
    if sum(e["sector_shares"]) <= 0:
        raise ValueError("Las participaciones sectoriales deben sumar más de cero")
    vector(e["va_factor"], "va_factor", .000001)
    for k in set(FACTORES_NOLAB.values()):
        numero(e.get(k, 1), 0, 100, k)
    if e.get("ing_lab_real_factor") is not None:
        numero(e["ing_lab_real_factor"], 0, 100, "ing_lab_real_factor")
    if e.get("ing_lab_real_factor_sector") is not None:
        vector(e["ing_lab_real_factor_sector"], "ing_lab_real_factor_sector")
    if e.get("ing_lab_real_factor_sector_area") is not None:
        for u in ("0", "1"):
            vector(e["ing_lab_real_factor_sector_area"].get(u), "ing_lab_real_factor_sector_area")
    if e.get("poblacion_grupos") is not None:
        if grupos_claves is None or set(e["poblacion_grupos"]) != set(grupos_claves):
            raise ValueError("Grupos demográficos incompletos o desconocidos")
        for x in e["poblacion_grupos"].values():
            numero(x, .000001, 100, "poblacion_grupos")
    if e.get("lineas_factor") is not None:
        claves = set(hogares.dominio.astype(str) + "_" + hogares.urbano.astype(str)) if hogares is not None else set()
        if set(e["lineas_factor"]) != claves:
            raise ValueError("Líneas regionales incompletas o desconocidas")
        for v in e["lineas_factor"].values():
            for k in ("linea", "linpe"):
                numero(v.get(k), .000001, 100, k)
    agregados = e.get("nolab_agregados", [])
    if not isinstance(agregados, list) or len(set(agregados)) != len(agregados) or any(k not in NOLAB[:-1] for k in agregados):
        raise ValueError("Componentes agregados inválidos")
    for k in ("bono", "afp"):
        if not isinstance(e.get(k, {}), dict):
            raise ValueError("Política inválida: " + k)
        numero(e.get(k, {}).get("mpc", 1), 0, 1, k + ".mpc")
    b, a = e.get("bono", {}), e.get("afp", {})
    numero(b.get("monto_anual", 0), 0, 1e7, "bono.monto_anual")
    numero(b.get("deciles", 0), 0, 10, "bono.deciles")
    if int(b.get("deciles", 0)) != b.get("deciles", 0):
        raise ValueError("El número de deciles debe ser entero")
    numero(a.get("monto", 0), 0, 1e7, "afp.monto")
    numero(a.get("cobertura", 0), 0, 1, "afp.cobertura")


class Modelo:
    def __init__(self, q: pd.DataFrame, h: pd.DataFrame, coef_sector: dict, grupos_hh: np.ndarray | None = None):
        """q: personas de 14+ con predicciones (estimar); h: hogares del año base."""
        self.h = h.reset_index(drop=True)
        hh_idx = pd.Series(np.arange(len(self.h)), index=self.h.hhid)
        self.q = q.reset_index(drop=True)
        self.ih = hh_idx.loc[self.q.hhid].values                 # persona -> índice de hogar
        self.coef = {3: np.array(coef_sector["informal"]), 4: np.array(coef_sector["formal"])}
        self.grupos_hh = grupos_hh                                # hogares x grupos (conteo de miembros)
        self.w0 = self.h.peso.values.astype(float)
        self.wp0 = self.w0[self.ih]
        self.nolab0 = self.h[NOLAB].values.astype(float)
        self.lab0 = self.h.lab_500.values.astype(float)
        self.Y0 = self.lab0 + self.nolab0.sum(axis=1)
        self.ocup0 = self.q.estado.isin([3, 4]).values
        self.sector0 = self.q.sector.values.astype(int)
        self.L0 = np.array([self.wp0[self.ocup0 & (self.sector0 == s)].sum() for s in range(1, 7)])
        masa = np.array([(self.wp0 * self.q.ing_lab.values)[self.ocup0 & (self.sector0 == s)].sum() for s in range(1, 7)])
        self.omega = masa / masa.sum()                            # participación de cada sector en la masa salarial base
        self.ps = self.q[[f"p_sector_{s}" for s in range(1, 7)]].values.astype(float)
        self.urbano_p = self.q.urbano.values.astype(int)
        self.deciles_base = None
        self._pesos_cache = {}

    # ------------------------------------------------------------------ pesos
    def _reponderar(self, esc: dict) -> np.ndarray:
        clave = json.dumps([esc.get("poblacion_factor", 1.0), esc.get("poblacion_grupos")], sort_keys=True)
        if clave in self._pesos_cache:
            w, self.demografia = self._pesos_cache[clave]
            return w.copy()
        factor = esc.get("poblacion_factor", 1.0)
        w = self.w0 * factor
        grupos = esc.get("poblacion_grupos")
        self.demografia = {"error_max_rel": 0.0, "iteraciones": 0}
        if grupos is not None:
            if self.grupos_hh is None:
                raise ValueError("Faltan los conteos demográficos de la base")
            G = self.grupos_hh
            T = np.array([grupos[k] for k in self.grupos_claves]) * (self.w0 @ G)
            # Las metas definen composición; el factor define la población total.
            T *= (self.w0 @ self.h.mieperho.values) * factor / T.sum()
            n_h = G.sum(axis=1)
            for it in range(1000):
                cur = np.einsum("i,ij->j", w, G)
                err = float(np.max(np.abs(cur / T - 1)))
                if err < 1e-8:
                    break
                log_r = np.log(T / cur)
                w *= np.exp(np.einsum("ij,j->i", G, log_r) / n_h)
            else:
                raise ValueError("La calibración demográfica no convergió")
            self.demografia = {"error_max_rel": err, "iteraciones": it}
        if len(self._pesos_cache) < 32:
            self._pesos_cache[clave] = (w.copy(), self.demografia.copy())
        return w

    # ------------------------------------------------------- selección por rango
    @staticmethod
    def _mover(mask_cand: np.ndarray, score: np.ndarray, wp: np.ndarray, cantidad: float, desc: bool) -> np.ndarray:
        """Índices de los candidatos con mayor (o menor) score hasta sumar `cantidad` de peso."""
        idx = np.flatnonzero(mask_cand)
        if cantidad <= 1e-6 * wp.sum() or len(idx) == 0:
            return idx[:0]
        o = np.argsort(-score[idx] if desc else score[idx], kind="stable")
        idx = idx[o]
        cum = np.cumsum(wp[idx])
        k = int(np.searchsorted(cum, cantidad, side="left")) + 1
        return idx[:k]

    # ---------------------------------------------------------------- motor
    def simular(self, esc: dict, detalle: bool = False) -> dict:
        validar_escenario(esc, getattr(self, "grupos_claves", None), self.h)
        q = self.q
        w = self._reponderar(esc)
        wp = w[self.ih]
        pop14 = wp.sum()

        # 2. ocupación / desempleo
        E_t = esc["tasa_ocupacion"] * pop14
        ocup = self.ocup0.copy()
        E0 = wp[ocup].sum()
        p_oc = q.p_ocupado.values
        if E_t > E0:
            ocup[self._mover(~ocup, p_oc, wp, E_t - E0, desc=True)] = True
        elif E_t < E0:
            ocup[self._mover(ocup, p_oc, wp, E0 - E_t, desc=False)] = False
        u = esc["tasa_desempleo"]
        U_t = u / (1 - u) * wp[ocup].sum()
        des = np.zeros(len(q), bool)
        des[self._mover(~ocup, q.p_desocupado_c.values, wp, U_t, desc=True)] = True

        # formalidad
        formal = (q.estado.values == 4) & ocup
        F_t = (1 - esc["informalidad"]) * wp[ocup].sum()
        F0 = wp[formal].sum()
        p_f = q.p_formal_c.values
        if F_t > F0:
            formal[self._mover(ocup & ~formal, p_f, wp, F_t - F0, desc=True)] = True
        elif F_t < F0:
            formal[self._mover(formal, p_f, wp, F0 - F_t, desc=False)] = False

        # 3. sectores
        sector = np.where(ocup, np.where(self.sector0 > 0, self.sector0, q.sector_pot.values), 0).astype(int)
        shares = np.array(esc["sector_shares"], float)
        shares = shares / shares.sum()
        T = shares * wp[ocup].sum()
        for _ in range(2):
            L = np.array([wp[ocup & (sector == s)].sum() for s in range(1, 7)])
            surplus = L - T
            for d in np.argsort(-(T - L), kind="stable"):
                deficit = T[d] - L[d]
                if deficit <= 0:
                    break
                cand = np.flatnonzero(ocup & (surplus[sector - 1] > 0) & (sector != d + 1))
                cand = cand[np.argsort(-self.ps[cand, d], kind="stable")]
                llenado = 0.0
                for c in cand:
                    s_old = sector[c] - 1
                    if surplus[s_old] <= 0:
                        continue
                    sector[c] = d + 1
                    surplus[s_old] -= wp[c]
                    llenado += wp[c]
                    if llenado >= deficit:
                        break
                L = np.array([wp[ocup & (sector == s)].sum() for s in range(1, 7)])
                surplus = L - T

        # 4. ingresos laborales
        seg = np.where(formal, 4, 3)
        seg0 = q.estado.values
        y_obs = q.ing_lab.values.astype(float)
        y_pot = np.where(formal, q.y_pot_formal.values, q.y_pot_informal.values).astype(float)
        continua = self.ocup0 & (seg == seg0)          # mismo segmento que en la base: ingreso observado
        y = np.where(continua, y_obs, y_pot)
        sp = q.sector_pot.values.astype(int)
        shift = np.exp(self.coef[3][sector - 1] - self.coef[3][sp - 1]) * (seg == 3) + \
            np.exp(self.coef[4][sector - 1] - self.coef[4][sp - 1]) * (seg == 4)
        y = y * shift
        L_t = np.array([wp[ocup & (sector == s)].sum() for s in range(1, 7)])
        va = np.array(esc["va_factor"], float)
        rel = (va / np.maximum(L_t / self.L0, 1e-9)) ** esc.get("passthrough", 1.0)   # PBI sectorial por ocupado
        g_lab = esc.get("ing_lab_real_factor")
        g_sec = esc.get("ing_lab_real_factor_sector")
        g_sa = esc.get("ing_lab_real_factor_sector_area")
        y = np.where(ocup, y, 0.0)
        f_sector = np.ones(6)
        metas_ingreso = {}
        def ajustar(mask, mask0, factor, nombre):
            if not mask.any():
                return 1.0
            objetivo = float(np.average(y_obs[mask0], weights=self.wp0[mask0])) * factor * esc["ipc"]
            previo = float(np.average(y[mask], weights=wp[mask]))
            if previo <= 0 and objetivo > 0:
                raise ValueError("No hay ingreso positivo para calibrar " + nombre)
            f = objetivo / previo if previo > 0 else 1.0
            y[mask] *= f
            metas_ingreso[nombre] = {"meta": objetivo, "resultado": float(np.average(y[mask], weights=wp[mask]))}
            return f
        if g_sa is not None:
            for u in (0, 1):
                for s in range(1, 7):
                    mask = ocup & (sector == s) & (self.urbano_p == u)
                    mask0 = self.ocup0 & (self.sector0 == s) & (self.urbano_p == u)
                    f = ajustar(mask, mask0, g_sa[str(u)][s-1], f"sector{s}_area{u}")
                    if u == 1:
                        f_sector[s-1] = f
        elif g_sec is not None:
            for s in range(1, 7):
                f_sector[s-1] = ajustar(ocup & (sector == s), self.ocup0 & (self.sector0 == s), g_sec[s-1], f"sector{s}")
        elif g_lab is None:
            f_sector = rel * esc["ipc"]
            y[ocup] *= f_sector[sector[ocup]-1]
        else:
            y[ocup] *= rel[sector[ocup]-1]
            f = ajustar(ocup, self.ocup0, g_lab, "agregado")
            f_sector = rel * f

        # 5. Ingreso corriente, consumo y retiros de activos son cuentas distintas.
        lab_t = np.bincount(self.ih, weights=y, minlength=len(self.h))
        fac = np.array([esc.get(FACTORES_NOLAB[k], 1.0) for k in NOLAB])
        metas_nolab = {}
        for k in esc.get("nolab_agregados", []):
            j = NOLAB.index(k)
            objetivo = float(self.w0 @ self.nolab0[:, j]) * fac[j]
            previo = float(w @ self.nolab0[:, j])
            if previo == 0 and objetivo != 0:
                raise ValueError("Sin receptores para la meta de " + k)
            fac[j] = objetivo / previo if previo != 0 else 1.0
            metas_nolab[k] = {"meta": objetivo, "resultado": previo * fac[j]}
        nolab_t = self.nolab0 @ fac
        bono = np.zeros(len(self.h))
        retiro = np.zeros(len(self.h))
        b = esc.get("bono", {})
        elegible = np.zeros(len(self.h), bool)
        if b.get("monto_anual", 0) > 0 and b.get("deciles", 0) > 0:
            if self.deciles_base is None:
                cortes = I.cuantiles_pond(self.h.gasto_pc.values, self.w0 * self.h.mieperho.values, np.arange(1, 10) / 10)
                self.deciles_base = np.searchsorted(cortes, self.h.gasto_pc.values, side="right") + 1
            elegible = self.deciles_base <= b["deciles"]
            bono = elegible * b["monto_anual"] / 12
        a = esc.get("afp", {})
        retira = (q.afp.values == 1) & (q.u.values < a.get("cobertura", 0)) & (a.get("monto", 0) > 0)
        retiro = np.bincount(self.ih, weights=retira * a.get("monto", 0) / 12, minlength=len(self.h))
        Y_regular = lab_t + nolab_t
        Y_t = Y_regular + bono       # retirar activos no es ingreso corriente
        piso = 0.1 * self.h.gasto_pc.values * self.h.mieperho.values
        ratio_real = np.maximum(Y_regular / esc["ipc"], piso) / np.maximum(self.Y0, piso)
        gasto_pc = self.h.gasto_pc.values * esc["ipc"] * ratio_real ** esc.get("elasticidad_gasto", 1.0)
        extra = bono * b.get("mpc", 1.0) + retiro * a.get("mpc", 1.0)
        gasto_pc += extra / self.h.mieperho.values
        ing_pc = Y_t / self.h.mieperho.values

        # 6. líneas e indicadores
        lf = esc.get("lineas_factor")
        if lf:
            clave = self.h.dominio.astype(str) + "_" + self.h.urbano.astype(str)
            linea = self.h.linea.values * clave.map(lambda k: lf[k]["linea"]).values
            linpe = self.h.linpe.values * clave.map(lambda k: lf[k]["linpe"]).values
        else:
            linea = self.h.linea.values * esc.get("linea_factor_nacional", 1.0)
            linpe = self.h.linpe.values * esc.get("linpe_factor_nacional", 1.0)
        wpers = w * self.h.mieperho.values
        res = I.resumen(gasto_pc, ing_pc, linea, linpe, wpers, self.h.urbano.values, self.h.dominio.values,
                        self.h.dpto.values)
        # curva de incidencia del crecimiento en términos reales (deflactada por el IPC del escenario)
        d0 = I.medias_por_decil(self.h.gasto_pc.values, self.w0 * self.h.mieperho.values)
        res["gic"] = (I.medias_por_decil(gasto_pc / esc["ipc"], wpers) / d0 - 1).tolist()
        res["laboral"] = {
            "tasa_ocupacion": float(wp[ocup].sum() / pop14),
            "tasa_desempleo": float(wp[des].sum() / wp[ocup | des].sum()),
            "informalidad": float(1 - wp[formal].sum() / wp[ocup].sum()),
            "sector_shares": (L_t / L_t.sum()).tolist(),
            "ing_lab_medio": float(np.average(y[ocup], weights=wp[ocup])),
            "ing_lab_medio_real": float(np.average(y[ocup], weights=wp[ocup]) / esc["ipc"]),
            "f_sector": f_sector.tolist(),
        }
        res["diagnostico"] = {"demografia": self.demografia, "ingresos": metas_ingreso, "no_laborales": metas_nolab,
            "poblacion_meta": float((self.w0 * self.h.mieperho.values).sum() * esc.get("poblacion_factor", 1.0)),
            "ocupacion_meta": esc["tasa_ocupacion"], "desempleo_meta": esc["tasa_desempleo"],
            "informalidad_meta": esc["informalidad"], "sector_shares_meta": shares.tolist()}
        res["politicas"] = {"costo_bono_anual": float(w @ bono * 12), "hogares_bono": float(w[elegible].sum()),
            "retiro_afp_anual": float(w @ retiro * 12), "personas_afp": float(wp[retira].sum()),
            "consumo_adicional_anual": float(w @ extra * 12)}
        res["ingreso_hogar_total"] = float((Y_t * w).sum())
        if detalle:
            res["_hogares"] = {"w": w, "gasto_pc": gasto_pc, "Y_t": Y_t, "lab_t": lab_t, "nolab_t": nolab_t, "extra": extra,
                               "linea": linea}
            res["_personas"] = {"wp": wp, "ocup": ocup, "formal": formal, "sector": sector, "y": y}
        return res


def cargar_modelo() -> Modelo:
    from .preparar import cargar
    q = pd.read_parquet(C.CLEAN / f"base_modelo_{C.ANIO_BASE}.parquet")
    p, h = cargar(C.ANIO_BASE)
    with open(C.OUT / "resumen_estimacion.json") as f:
        coef = json.load(f)["coef_sector"]
    # conteo de miembros por hogar en grupos sexo x edad x área (para la calibración)
    p = p.copy()
    p["clave"] = p.mujer.astype(str) + "_" + p.gedad.astype(str) + "_" + p.urbano.astype(str)
    tab = pd.crosstab(p.hhid, p.clave).reindex(h.hhid).fillna(0)
    m = Modelo(q, h, coef, tab.values.astype(float))
    m.grupos_claves = list(tab.columns)
    return m
