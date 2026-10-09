/* Motor de microsimulación (réplica en JavaScript de pipeline/micropec/simular.py).
 * Se usa en la interfaz (index.html) y en la prueba de equivalencia (pipeline/07_verificar_gui.py).
 * Funciona en el navegador y en cualquier intérprete JS (sin dependencias). */
(function (global) {
  "use strict";
  const NOLAB = ["tr_juntos", "tr_p65", "tr_pub_otros", "tr_privadas", "remesas", "rentas", "alq_imputado", "extraord", "otros_nolab"];
  const FACT = { tr_juntos: "tr_juntos_factor", tr_p65: "tr_p65_factor", tr_pub_otros: "tr_pub_otros_factor",
    tr_privadas: "tr_privadas_factor", remesas: "remesas_factor", rentas: "rentas_factor", alq_imputado: "alq_factor",
    extraord: "otros_factor", otros_nolab: "otros_factor" };

  function gini(x, w) {
    const n = x.length, o = new Array(n);
    for (let i = 0; i < n; i++) o[i] = i;
    o.sort((a, b) => x[a] - x[b] || a - b);
    let W = 0, X = 0;
    for (let i = 0; i < n; i++) { W += w[i]; X += x[i] * w[i]; }
    if (X <= 0) return NaN;
    let cw = 0, cx = 0, area = 0, lwPrev = 0, lxPrev = 0;
    for (const i of o) {
      cw += w[i]; cx += x[i] * w[i];
      const lw = cw / W, lx = cx / X;
      area += (lw - lwPrev) * (lx + lxPrev) / 2;
      lwPrev = lw; lxPrev = lx;
    }
    return 1 - 2 * area;
  }
  function cuantiles(x, w, qs) {
    const n = x.length, o = new Array(n);
    for (let i = 0; i < n; i++) o[i] = i;
    o.sort((a, b) => x[a] - x[b] || a - b);
    let W = 0; for (let i = 0; i < n; i++) W += w[i];
    const cw = new Float64Array(n), xs = new Float64Array(n);
    let c = 0;
    for (let k = 0; k < n; k++) { const i = o[k]; c += w[i]; cw[k] = (c - 0.5 * w[i]) / W; xs[k] = x[i]; }
    return qs.map(q => {
      if (q <= cw[0]) return xs[0];
      if (q >= cw[n - 1]) return xs[n - 1];
      let lo = 0, hi = n - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (cw[mid] <= q) lo = mid; else hi = mid; }
      return xs[lo] + (xs[hi] - xs[lo]) * (q - cw[lo]) / (cw[hi] - cw[lo]);
    });
  }
  function mediasDecil(x, w) {
    const cortes = cuantiles(x, w, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]);
    const s = new Float64Array(10), sw = new Float64Array(10);
    for (let i = 0; i < x.length; i++) {
      let d = 0; while (d < 9 && x[i] >= cortes[d]) d++;   // searchsorted side=right
      s[d] += x[i] * w[i]; sw[d] += w[i];
    }
    return Array.from(s, (v, d) => v / sw[d]);
  }
  function wmean(mask, w, n, val) {
    let a = 0, b = 0;
    for (let i = 0; i < n; i++) if (mask(i)) { a += w[i] * (val ? val(i) : 1); b += w[i]; }
    return b > 0 ? a / b : NaN;
  }

  class Modelo {
    constructor(D) {
      this.D = D; const P = D.personas, H = D.hogares;
      this.nP = P.ih.length; this.nH = H.w.length;
      this.coef = { 3: D.params.coef_sector.informal, 4: D.params.coef_sector.formal };
      this.L0 = D.params.L0; this.omega = D.params.omega;
      this.w0 = H.w; this.ocup0 = P.e.map(e => e === 3 || e === 4);
      this.nolab0 = NOLAB.map(k => H.nolab[k]);
      this.Y0 = new Float64Array(this.nH);
      for (let h = 0; h < this.nH; h++) { let s = H.lab0[h]; for (const col of this.nolab0) s += col[h]; this.Y0[h] = s; }
      this.decilesBase = null;
    }
    static mover(idx, score, wp, cantidad, desc, total) {
      if (cantidad <= 1e-6 * total || idx.length === 0) return [];
      const o = idx.slice().sort(desc ? ((a, b) => score[b] - score[a] || a - b) : ((a, b) => score[a] - score[b] || a - b));
      const out = []; let cum = 0;
      for (const i of o) { out.push(i); cum += wp[i]; if (cum >= cantidad) break; }
      return out;
    }
    simular(esc) {
      const D = this.D, P = D.personas, H = D.hogares, nP = this.nP, nH = this.nH;
      const w = this.w0.map(v => v * (esc.poblacion_factor || 1));
      const wp = new Float64Array(nP); let pop14 = 0;
      for (let i = 0; i < nP; i++) { wp[i] = w[P.ih[i]]; pop14 += wp[i]; }
      // 2. ocupación
      const ocup = this.ocup0.slice();
      let E0 = 0; for (let i = 0; i < nP; i++) if (ocup[i]) E0 += wp[i];
      const E_t = esc.tasa_ocupacion * pop14;
      const idxAll = Array.from({ length: nP }, (_, i) => i);
      if (E_t > E0) for (const i of Modelo.mover(idxAll.filter(i => !ocup[i]), P.po, wp, E_t - E0, true, pop14)) ocup[i] = true;
      else if (E_t < E0) for (const i of Modelo.mover(idxAll.filter(i => ocup[i]), P.po, wp, E0 - E_t, false, pop14)) ocup[i] = false;
      let Eocup = 0; for (let i = 0; i < nP; i++) if (ocup[i]) Eocup += wp[i];
      const u = esc.tasa_desempleo, U_t = u / (1 - u) * Eocup;
      const des = new Array(nP).fill(false);
      for (const i of Modelo.mover(idxAll.filter(i => !ocup[i]), P.pd, wp, U_t, true, pop14)) des[i] = true;
      // formalidad
      const formal = P.e.map((e, i) => e === 4 && ocup[i]);
      let F0 = 0; for (let i = 0; i < nP; i++) if (formal[i]) F0 += wp[i];
      const F_t = (1 - esc.informalidad) * Eocup;
      if (F_t > F0) for (const i of Modelo.mover(idxAll.filter(i => ocup[i] && !formal[i]), P.pf, wp, F_t - F0, true, pop14)) formal[i] = true;
      else if (F_t < F0) for (const i of Modelo.mover(idxAll.filter(i => formal[i]), P.pf, wp, F0 - F_t, false, pop14)) formal[i] = false;
      // 3. sectores
      const sector = new Int32Array(nP);
      for (let i = 0; i < nP; i++) sector[i] = ocup[i] ? (P.s[i] > 0 ? P.s[i] : P.sp[i]) : 0;
      let sh = esc.sector_shares.slice(); const shs = sh.reduce((a, b) => a + b, 0); sh = sh.map(v => v / shs);
      const T = sh.map(v => v * Eocup);
      const contar = () => { const L = new Float64Array(6); for (let i = 0; i < nP; i++) if (ocup[i]) L[sector[i] - 1] += wp[i]; return L; };
      for (let pass = 0; pass < 2; pass++) {
        let L = contar(); let surplus = L.map((v, s) => v - T[s]);
        const orden = [0, 1, 2, 3, 4, 5].sort((a, b) => (T[b] - L[b]) - (T[a] - L[a]) || a - b);
        for (const d of orden) {
          const deficit = T[d] - L[d];
          if (deficit <= 0) break;
          const ps = P.ps[d];
          const cand = idxAll.filter(i => ocup[i] && surplus[sector[i] - 1] > 0 && sector[i] !== d + 1)
            .sort((a, b) => ps[b] - ps[a] || a - b);
          let llenado = 0;
          for (const c of cand) {
            const sOld = sector[c] - 1;
            if (surplus[sOld] <= 0) continue;
            sector[c] = d + 1; surplus[sOld] -= wp[c]; llenado += wp[c];
            if (llenado >= deficit) break;
          }
          L = contar(); surplus = L.map((v, s) => v - T[s]);
        }
      }
      // 4. ingresos laborales
      const L_t = contar();
      const rel = L_t.map((l, s) => Math.pow(esc.va_factor[s] / Math.max(l / this.L0[s], 1e-9), esc.passthrough == null ? 1 : esc.passthrough));
      let f_sector;
      if (esc.ing_lab_real_factor_sector) f_sector = esc.ing_lab_real_factor_sector.map(v => v * esc.ipc);
      else if (esc.ing_lab_real_factor == null) f_sector = rel.map(v => v * esc.ipc);
      else { let norm = 0; for (let s = 0; s < 6; s++) norm += this.omega[s] * rel[s]; f_sector = rel.map(v => v / norm * esc.ing_lab_real_factor * esc.ipc); }
      const y = new Float64Array(nP);
      for (let i = 0; i < nP; i++) {
        if (!ocup[i]) continue;
        const seg = formal[i] ? 4 : 3;
        let v = (this.ocup0[i] && seg === P.e[i]) ? P.y[i] : (formal[i] ? P.yf[i] : P.yi[i]);
        const cf = this.coef[seg];
        v *= Math.exp(cf[sector[i] - 1] - cf[P.sp[i] - 1]);
        y[i] = v * f_sector[sector[i] - 1];
      }
      // 5. hogares
      const lab_t = new Float64Array(nH);
      for (let i = 0; i < nP; i++) lab_t[P.ih[i]] += y[i];
      const fac = NOLAB.map(k => esc[FACT[k]] == null ? 1 : esc[FACT[k]]);
      const extra = new Float64Array(nH);
      const b = esc.bono || {};
      if (b.monto_anual > 0 && b.deciles > 0) {
        if (!this.decilesBase) {
          const wpers = this.w0.map((v, h) => v * H.n[h]);
          const cortes = cuantiles(H.g, wpers, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]);
          this.decilesBase = H.g.map(g => { let d = 0; while (d < 9 && g >= cortes[d]) d++; return d + 1; });
        }
        for (let h = 0; h < nH; h++) if (this.decilesBase[h] <= b.deciles) extra[h] += b.monto_anual / 12 * (b.mpc == null ? 1 : b.mpc);
      }
      const a = esc.afp || {};
      if (a.cobertura > 0 && a.monto > 0) {
        for (let i = 0; i < nP; i++) if (P.afp[i] === 1 && P.u[i] < a.cobertura) extra[P.ih[i]] += a.monto / 12 * (a.mpc == null ? 1 : a.mpc);
      }
      const el = esc.elasticidad_gasto == null ? 1 : esc.elasticidad_gasto;
      const gasto = new Float64Array(nH), ing = new Float64Array(nH), Y_t = new Float64Array(nH), wpers = new Float64Array(nH);
      const linea = new Float64Array(nH), linpe = new Float64Array(nH);
      const lf = esc.linea_factor_nacional == null ? 1 : esc.linea_factor_nacional, lfe = esc.linpe_factor_nacional == null ? 1 : esc.linpe_factor_nacional;
      let Ytot = 0;
      for (let h = 0; h < nH; h++) {
        let nol = 0; for (let k = 0; k < 9; k++) nol += this.nolab0[k][h] * fac[k];
        Y_t[h] = lab_t[h] + nol + extra[h];
        const piso = 0.1 * H.g[h] * H.n[h];
        const ratio = Math.max(Y_t[h], piso) / Math.max(this.Y0[h], piso);
        gasto[h] = H.g[h] * Math.pow(ratio, el);
        ing[h] = Y_t[h] / H.n[h];
        wpers[h] = w[h] * H.n[h];
        linea[h] = H.lin[h] * lf; linpe[h] = H.linpe[h] * lfe;
        Ytot += Y_t[h] * w[h];
      }
      // 6. indicadores
      const pobre = i => gasto[i] < linea[i], ext = i => gasto[i] < linpe[i];
      const brecha = i => pobre(i) ? 1 - gasto[i] / linea[i] : 0;
      const todos = () => true;
      let Wt = 0, nPob = 0, nExt = 0; for (let h = 0; h < nH; h++) { Wt += wpers[h]; if (pobre(h)) nPob += wpers[h]; if (ext(h)) nExt += wpers[h]; }
      const dec = mediasDecil(Array.from(gasto), wpers), dec0 = mediasDecil(H.g, wpers);
      const decReal = mediasDecil(Array.from(gasto, v => v / esc.ipc), wpers);   // GIC en términos reales
      const res = {
        pobreza: nPob / Wt, pobreza_extrema: nExt / Wt,
        brecha: wmean(todos, wpers, nH, brecha), severidad: wmean(todos, wpers, nH, i => brecha(i) ** 2),
        n_pobres: nPob, n_pobres_ext: nExt, poblacion: Wt,
        gini_gasto: gini(Array.from(gasto), wpers), gini_ingreso: gini(Array.from(ing, v => Math.max(v, 0)), wpers),
        gasto_pc_medio: wmean(todos, wpers, nH, i => gasto[i]), ing_pc_medio: wmean(todos, wpers, nH, i => ing[i]),
        deciles_gasto: dec, gic: decReal.map((v, d) => v / dec0[d] - 1),
        por_area: { urbano: { pobreza: wmean(i => H.urb[i] === 1, wpers, nH, i => pobre(i) ? 1 : 0), pobreza_extrema: wmean(i => H.urb[i] === 1, wpers, nH, i => ext(i) ? 1 : 0) },
                    rural: { pobreza: wmean(i => H.urb[i] === 0, wpers, nH, i => pobre(i) ? 1 : 0), pobreza_extrema: wmean(i => H.urb[i] === 0, wpers, nH, i => ext(i) ? 1 : 0) } },
        por_dominio: {}, por_dpto: {},
        ingreso_hogar_total: Ytot,
      };
      for (const d of [...new Set(H.dom)].sort((a, b) => a - b)) res.por_dominio[d] = wmean(i => H.dom[i] === d, wpers, nH, i => pobre(i) ? 1 : 0);
      for (const d of [...new Set(H.dpto)].sort((a, b) => a - b)) res.por_dpto[d] = wmean(i => H.dpto[i] === d, wpers, nH, i => pobre(i) ? 1 : 0);
      let Eo = 0, Ed = 0, Ef = 0, Ey = 0; const Ls = L_t.reduce((p, c) => p + c, 0);
      for (let i = 0; i < nP; i++) { if (ocup[i]) { Eo += wp[i]; Ey += wp[i] * y[i]; if (formal[i]) Ef += wp[i]; } if (des[i]) Ed += wp[i]; }
      res.laboral = { tasa_ocupacion: Eo / pop14, tasa_desempleo: Ed / (Eo + Ed), informalidad: 1 - Ef / Eo,
        sector_shares: Array.from(L_t, v => v / Ls), ing_lab_medio: Ey / Eo, ing_lab_medio_real: Ey / Eo / esc.ipc, f_sector: f_sector };
      return res;
    }
  }
  global.MicroPEC = { Modelo, gini, cuantiles, mediasDecil, NOLAB };
})(typeof window !== "undefined" ? window : globalThis);
