/* Motor de microsimulación (réplica en JavaScript de pipeline/microsim/simular.py).
 * Se usa en la interfaz (index.html) y en la prueba de equivalencia (pipeline/07_verificar_gui.py).
 * Funciona en el navegador y en cualquier intérprete JS (sin dependencias). */
(function (global) {
  "use strict";
  const NOLAB = ["tr_juntos", "tr_p65", "tr_pub_otros", "tr_privadas", "remesas", "rentas", "alq_imputado", "extraord", "otros_nolab", "ajuste_contable"];
  const FACT = { tr_juntos: "tr_juntos_factor", tr_p65: "tr_p65_factor", tr_pub_otros: "tr_pub_otros_factor",
    tr_privadas: "tr_privadas_factor", remesas: "remesas_factor", rentas: "rentas_factor", alq_imputado: "alq_factor",
    extraord: "otros_factor", otros_nolab: "otros_factor", ajuste_contable: "ipc" };

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

  function validarEscenario(e, D) {
    const num = (x,lo,hi,k) => { if (typeof x !== "number" || !Number.isFinite(x) || x < lo || x > hi) throw Error("Valor inválido: " + k); };
    for (const k of ["ipc","poblacion_factor","linea_factor_nacional","linpe_factor_nacional"]) num(e[k],.000001,100,k);
    num(e.tasa_ocupacion,.000001,1,"tasa_ocupacion"); num(e.tasa_desempleo,0,.999999,"tasa_desempleo");
    if (e.tasa_ocupacion > 1-e.tasa_desempleo+1e-9) throw Error("Ocupación y desempleo implican una PEA mayor que la población de 14+");
    num(e.informalidad,0,1,"informalidad"); num(e.passthrough,0,1,"passthrough"); num(e.elasticidad_gasto,.01,3,"elasticidad_gasto");
    const vec = (v,k,lo=0) => { if (!Array.isArray(v) || v.length !== 6) throw Error("Se necesitan seis valores: " + k); for (const x of v) num(x,lo,100,k); };
    vec(e.sector_shares,"sector_shares"); if (e.sector_shares.reduce((a,b) => a+b,0) <= 0) throw Error("Las participaciones sectoriales deben sumar más de cero");
    vec(e.va_factor,"va_factor",.000001);
    for (const k of new Set(Object.values(FACT))) num(e[k] === undefined ? 1 : e[k],0,100,k);
    if (e.ing_lab_real_factor != null) num(e.ing_lab_real_factor,0,100,"ing_lab_real_factor");
    if (e.ing_lab_real_factor_sector != null) vec(e.ing_lab_real_factor_sector,"ing_lab_real_factor_sector");
    if (e.ing_lab_real_factor_sector_area != null) for (const u of ["0","1"]) vec(e.ing_lab_real_factor_sector_area[u],"ing_lab_real_factor_sector_area");
    if (e.poblacion_grupos != null) {
      const keys = D.demografia && D.demografia.claves;
      if (!keys || keys.length !== Object.keys(e.poblacion_grupos).length || keys.some(k => !(k in e.poblacion_grupos))) throw Error("Grupos demográficos incompletos o desconocidos");
      for (const x of Object.values(e.poblacion_grupos)) num(x,.000001,100,"poblacion_grupos");
    }
    if (e.lineas_factor != null) {
      const keys = new Set(D.hogares.dom.map((d,h) => d+"_"+D.hogares.urb[h]));
      if (keys.size !== Object.keys(e.lineas_factor).length || [...keys].some(k => !(k in e.lineas_factor))) throw Error("Líneas regionales incompletas o desconocidas");
      for (const v of Object.values(e.lineas_factor)) for (const k of ["linea","linpe"]) num(v[k],.000001,100,k);
    }
    const ag = e.nolab_agregados || [];
    if (!Array.isArray(ag) || new Set(ag).size !== ag.length || ag.some(k => !NOLAB.slice(0,-1).includes(k))) throw Error("Componentes agregados inválidos");
    for (const k of ["bono", "afp"]) if (e[k] !== undefined && (e[k] === null || typeof e[k] !== "object" || Array.isArray(e[k]))) throw Error("Política inválida: " + k);
    const b = e.bono || {}, a = e.afp || {};
    num(b.mpc === undefined ? 1 : b.mpc,0,1,"bono.mpc"); num(a.mpc === undefined ? 1 : a.mpc,0,1,"afp.mpc");
    num((b.monto_anual === undefined ? 0 : b.monto_anual),0,1e7,"bono.monto_anual"); num((b.deciles === undefined ? 0 : b.deciles),0,10,"bono.deciles");
    if (!Number.isInteger((b.deciles === undefined ? 0 : b.deciles))) throw Error("El número de deciles debe ser entero");
    num((a.monto === undefined ? 0 : a.monto),0,1e7,"afp.monto"); num((a.cobertura === undefined ? 0 : a.cobertura),0,1,"afp.cobertura");
  }

  class Modelo {
    constructor(D) {
      this.D = D; const P = D.personas, H = D.hogares;
      this.nP = P.ih.length; this.nH = H.w.length;
      this.coef = { 3: D.params.coef_sector.informal, 4: D.params.coef_sector.formal };
      this.L0 = Array(6).fill(0);
      for (let i = 0; i < P.e.length; i++) if (P.e[i] === 3 || P.e[i] === 4) this.L0[P.s[i]-1] += H.w[P.ih[i]];
      this.omega = D.params.omega;
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
      validarEscenario(esc, D);
      let w = this.w0.map(v => v * esc.poblacion_factor);
      let demografia = {error_max_rel: 0, iteraciones: 0};
      if (esc.poblacion_grupos != null) {
        const G = D.demografia.conteos, claves = D.demografia.claves, K = claves.length;
        const T = Array(K).fill(0), nh = G.map(row => row.reduce((a,b) => a+b, 0));
        let poblacion0 = 0;
        for (let h = 0; h < nH; h++) {
          poblacion0 += this.w0[h] * H.n[h];
          for (let k = 0; k < K; k++) T[k] += this.w0[h] * G[h][k];
        }
        for (let k = 0; k < K; k++) T[k] *= esc.poblacion_grupos[claves[k]];
        const total = T.reduce((a,b) => a+b, 0);
        for (let k = 0; k < K; k++) T[k] *= poblacion0 * esc.poblacion_factor / total;
        let convergio = false;
        for (let it = 0; it < 1000; it++) {
          const cur = Array(K).fill(0);
          for (let h = 0; h < nH; h++) for (let k = 0; k < K; k++) cur[k] += w[h] * G[h][k];
          const err = Math.max(...cur.map((v,k) => Math.abs(v/T[k]-1)));
          if (err < 1e-8) { demografia = {error_max_rel: err, iteraciones: it}; convergio = true; break; }
          const lr = cur.map((v,k) => Math.log(T[k]/v));
          for (let h = 0; h < nH; h++) {
            let v = 0; for (let k = 0; k < K; k++) v += G[h][k] * lr[k];
            w[h] *= Math.exp(v/nh[h]);
          }
        }
        if (!convergio) throw Error("La calibración demográfica no convergió");
      }
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
      const y = new Float64Array(nP), f_sector = Array(6).fill(1), metasIngreso = {};
      for (let i = 0; i < nP; i++) {
        if (!ocup[i]) continue;
        const seg = formal[i] ? 4 : 3, cf = this.coef[seg];
        const v = this.ocup0[i] && seg === P.e[i] ? P.y[i] : (formal[i] ? P.yf[i] : P.yi[i]);
        y[i] = v * Math.exp(cf[sector[i]-1] - cf[P.sp[i]-1]);
      }
      const ajustar = (mask, mask0, factor, nombre) => {
        let sy = 0, sw = 0, sy0 = 0, sw0 = 0;
        for (let i = 0; i < nP; i++) {
          if (mask(i)) { sy += y[i]*wp[i]; sw += wp[i]; }
          if (mask0(i)) { const w0 = this.w0[P.ih[i]]; sy0 += P.y[i]*w0; sw0 += w0; }
        }
        if (sw === 0) return 1;
        const objetivo = sy0/sw0 * factor * esc.ipc, previo = sy/sw;
        if (previo <= 0 && objetivo > 0) throw Error("No hay ingreso positivo para calibrar " + nombre);
        const f = previo > 0 ? objetivo/previo : 1;
        let nuevo = 0;
        for (let i = 0; i < nP; i++) if (mask(i)) { y[i] *= f; nuevo += y[i]*wp[i]; }
        metasIngreso[nombre] = {meta: objetivo, resultado: nuevo/sw};
        return f;
      };
      const gsa = esc.ing_lab_real_factor_sector_area, gs = esc.ing_lab_real_factor_sector;
      if (gsa != null) {
        for (const u of [0,1]) for (let s = 1; s <= 6; s++) {
          const f = ajustar(i => ocup[i] && sector[i] === s && P.urb[i] === u,
            i => this.ocup0[i] && P.s[i] === s && P.urb[i] === u, gsa[String(u)][s-1], `sector${s}_area${u}`);
          if (u === 1) f_sector[s-1] = f;
        }
      } else if (gs != null) {
        for (let s = 1; s <= 6; s++) f_sector[s-1] = ajustar(i => ocup[i] && sector[i] === s,
          i => this.ocup0[i] && P.s[i] === s, gs[s-1], `sector${s}`);
      } else if (esc.ing_lab_real_factor == null) {
        for (let s = 0; s < 6; s++) f_sector[s] = rel[s] * esc.ipc;
        for (let i = 0; i < nP; i++) if (ocup[i]) y[i] *= f_sector[sector[i]-1];
      } else {
        for (let i = 0; i < nP; i++) if (ocup[i]) y[i] *= rel[sector[i]-1];
        const f = ajustar(i => ocup[i], i => this.ocup0[i], esc.ing_lab_real_factor, "agregado");
        for (let s = 0; s < 6; s++) f_sector[s] = rel[s]*f;
      }
      // 5. Ingreso corriente, consumo y retiro de activos por separado.
      const lab_t = new Float64Array(nH);
      for (let i = 0; i < nP; i++) lab_t[P.ih[i]] += y[i];
      const fac = NOLAB.map(k => esc[FACT[k]] == null ? 1 : esc[FACT[k]]), metasNolab = {};
      for (const k of esc.nolab_agregados || []) {
        const j = NOLAB.indexOf(k); let base = 0, previo = 0;
        for (let h = 0; h < nH; h++) { base += this.w0[h]*this.nolab0[j][h]; previo += w[h]*this.nolab0[j][h]; }
        const objetivo = base*fac[j];
        if (previo === 0 && objetivo !== 0) throw Error("Sin receptores para la meta de " + k);
        fac[j] = previo !== 0 ? objetivo/previo : 1;
        metasNolab[k] = {meta: objetivo, resultado: previo*fac[j]};
      }
      const bono = new Float64Array(nH), retiro = new Float64Array(nH);
      const b = esc.bono || {}, a = esc.afp || {};
      let hogaresBono = 0, personasAFP = 0;
      if (b.monto_anual > 0 && b.deciles > 0) {
        if (!this.decilesBase) {
          const cortes = cuantiles(H.g, this.w0.map((v,h) => v*H.n[h]), [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]);
          this.decilesBase = H.g.map(g => { let d = 0; while (d < 9 && g >= cortes[d]) d++; return d+1; });
        }
        for (let h = 0; h < nH; h++) if (this.decilesBase[h] <= b.deciles) { bono[h] = b.monto_anual/12; hogaresBono += w[h]; }
      }
      if (a.cobertura > 0 && a.monto > 0) for (let i = 0; i < nP; i++) if (P.afp[i] === 1 && P.u[i] < a.cobertura) {
        retiro[P.ih[i]] += a.monto/12; personasAFP += wp[i];
      }
      const el = esc.elasticidad_gasto;
      const gasto = new Float64Array(nH), ing = new Float64Array(nH), wpers = new Float64Array(nH);
      const linea = new Float64Array(nH), linpe = new Float64Array(nH);
      let Ytot = 0, costoBono = 0, retiroAFP = 0, consumoExtra = 0, poblacionMeta = 0;
      for (let h = 0; h < nH; h++) {
        let nol = 0; for (let k = 0; k < NOLAB.length; k++) nol += this.nolab0[k][h]*fac[k];
        const regular = lab_t[h] + nol, Y = regular + bono[h], piso = 0.1*H.g[h]*H.n[h];
        const ratio = Math.max(regular/esc.ipc, piso)/Math.max(this.Y0[h], piso);
        const extra = bono[h]*(b.mpc === undefined ? 1 : b.mpc) + retiro[h]*(a.mpc === undefined ? 1 : a.mpc);
        gasto[h] = H.g[h]*esc.ipc*Math.pow(ratio, el) + extra/H.n[h];
        ing[h] = Y/H.n[h]; wpers[h] = w[h]*H.n[h];
        const lf = esc.lineas_factor && esc.lineas_factor[H.dom[h]+"_"+H.urb[h]];
        linea[h] = H.lin[h]*(lf ? lf.linea : esc.linea_factor_nacional);
        linpe[h] = H.linpe[h]*(lf ? lf.linpe : esc.linpe_factor_nacional);
        Ytot += Y*w[h]; costoBono += bono[h]*w[h]*12; retiroAFP += retiro[h]*w[h]*12; consumoExtra += extra*w[h]*12;
        poblacionMeta += this.w0[h]*H.n[h]*esc.poblacion_factor;
      }
      // 6. indicadores
      const pobre = i => gasto[i] < linea[i], ext = i => gasto[i] < linpe[i];
      const brecha = i => pobre(i) ? 1 - gasto[i] / linea[i] : 0;
      const todos = () => true;
      let Wt = 0, nPob = 0, nExt = 0; for (let h = 0; h < nH; h++) { Wt += wpers[h]; if (pobre(h)) nPob += wpers[h]; if (ext(h)) nExt += wpers[h]; }
      const dec = mediasDecil(Array.from(gasto), wpers), dec0 = mediasDecil(H.g, this.w0.map((v,h) => v*H.n[h]));
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
        diagnostico: {demografia, ingresos: metasIngreso, no_laborales: metasNolab, poblacion_meta: poblacionMeta,
          ocupacion_meta: esc.tasa_ocupacion, desempleo_meta: esc.tasa_desempleo, informalidad_meta: esc.informalidad, sector_shares_meta: sh},
        politicas: {costo_bono_anual: costoBono, hogares_bono: hogaresBono, retiro_afp_anual: retiroAFP,
          personas_afp: personasAFP, consumo_adicional_anual: consumoExtra},
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
  global.MicroSim = { validarEscenario, Modelo, gini, cuantiles, mediasDecil, NOLAB };
})(typeof window !== "undefined" ? window : globalThis);
