// V3's set pieces, played inside the stadium itself (the engine's 3D scene, in yards, the field centred on the origin):
// a bet placed is flown in by a drone and dropped on midfield; a bet that cashes gets a flyover, coins raining into the
// bowl, the ticket unrolled across the field and searchlights; a loss puts the lights out and a bolt through the ticket.
const SBW = () => window.SBW;
function ticketTex(THREE, o, big) {
  const c = document.createElement("canvas"); c.width = 2048; c.height = 768; const x = c.getContext("2d"); x.scale(2, 2);
  const g = x.createLinearGradient(0, 0, 0, 384); g.addColorStop(0, o.bg || "#141b2b"); g.addColorStop(1, "#070a12"); x.fillStyle = g; x.fillRect(0, 0, 1024, 384);
  x.fillStyle = o.col; x.fillRect(0, 0, 26, 384); x.strokeStyle = o.edge || o.col; x.lineWidth = 10; x.strokeRect(5, 5, 1014, 374);
  x.textBaseline = "middle"; x.fillStyle = o.col; x.font = "900 64px 'Barlow Condensed', Arial, sans-serif"; x.fillText(String(o.who || "").toUpperCase(), 60, 70);
  x.textAlign = "right"; x.fillStyle = "#fff"; x.fillText(o.odds || "", 980, 70); x.textAlign = "left";
  x.font = `900 ${big ? 150 : 124}px 'Big Shoulders Display', 'Barlow Condensed', Arial, sans-serif`; x.fillStyle = "#fff"; let t = String(o.big || ""); while (x.measureText(t).width > 920 && t.length > 4) t = t.slice(0, -2); x.fillText(t, 60, 200);
  x.font = "800 58px 'Barlow Condensed', Arial, sans-serif"; x.fillStyle = o.subCol || "#aeb9cc"; x.fillText(String(o.sub || "").toUpperCase().slice(0, 34), 60, 322);
  const tx = new THREE.CanvasTexture(c); tx.anisotropy = 16; return tx;
}
function glowTex(THREE) { const c = document.createElement("canvas"); c.width = c.height = 64; const x = c.getContext("2d"), g = x.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, "#fff"); g.addColorStop(0.3, "rgba(255,255,255,.55)"); g.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = g; x.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c); }
const ease = (t) => (t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t)), lerp = (a, b, t) => a + (b - a) * t, cl = (v) => Math.max(0, Math.min(1, v));

// run one: kind "place" | "win" | "loss"; o: { col: [r,g,b], who, big, sub, odds, tier }. Resolves when it's over
export function runAct(kind, o) {
  const st = SBW() && SBW().st && SBW().st(); if (!st || st.room || !st.scene || SBW().kind() !== "nfl") return Promise.resolve(false);
  const THREE = st.THREE, scene = st.scene, top = (st.V && st.V.top) || 46, own = [], C = (c, k = 1) => new THREE.Color().setRGB(Math.min(1, c[0] * k), Math.min(1, c[1] * k), Math.min(1, c[2] * k), THREE.LinearSRGBColorSpace);
  const add = (m, parent) => { (parent || scene).add(m); if (!parent) own.push(m); return m; }, basic = (c, o2) => new THREE.MeshBasicMaterial(Object.assign({ color: C(c) }, o2 || {})), addv = (c, op) => basic(c, { transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  const gt = glowTex(THREE), cssCol = `rgb(${o.col.map((v) => Math.round(v * 255)).join(",")})`, GOLD = [1, 0.8, 0.25];
  // sparks: one pool for trails, bursts, embers
  const NP = 1600, pos = new Float32Array(NP * 3).fill(9999), colr = new Float32Array(NP * 3), vel = new Float32Array(NP * 3), life = new Float32Array(NP), mx = new Float32Array(NP), base = new Float32Array(NP * 3), grav = new Float32Array(NP); let pi = 0;
  const pg = new THREE.BufferGeometry(); pg.setAttribute("position", new THREE.BufferAttribute(pos, 3)); pg.setAttribute("color", new THREE.BufferAttribute(colr, 3));
  const pts = add(new THREE.Points(pg, new THREE.PointsMaterial({ size: 2.6, map: gt, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }))); pts.frustumCulled = false;
  const spark = (p, v, c, l, g = 0) => { const i = (pi = (pi + 1) % NP); pos[i * 3] = p[0]; pos[i * 3 + 1] = p[1]; pos[i * 3 + 2] = p[2]; vel[i * 3] = v[0]; vel[i * 3 + 1] = v[1]; vel[i * 3 + 2] = v[2]; life[i] = mx[i] = l; grav[i] = g; base[i * 3] = c[0]; base[i * 3 + 1] = c[1]; base[i * 3 + 2] = c[2]; };
  const burst = (p, c, n, sp) => { for (let k = 0; k < n; k++) { const a = Math.random() * 6.283, e = Math.acos(2 * Math.random() - 1), v = sp * (0.5 + 0.5 * Math.random()); spark(p, [Math.cos(a) * Math.sin(e) * v, Math.cos(e) * v, Math.sin(a) * Math.sin(e) * v], Math.random() < 0.25 ? [1, 1, 1] : c, 1.2 + Math.random() * 0.8, 9); } };
  const ringOn = (c, r1) => { const m = add(new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 64), addv(c, 1))); m.rotation.x = -Math.PI / 2; m.position.y = 0.2; m.userData = { t: 0, r1 }; rings.push(m); return m; }, rings = [];
  const beamUp = (c, x, z, r, h) => { const m = add(new THREE.Mesh(new THREE.CylinderGeometry(r, r * 1.6, h, 20, 1, true), addv(c, 0.2))); m.position.set(x, h / 2, z); m.userData.t = 0; beams.push(m); return m; }, beams = [];
  const ticket = (w, h, big, extra) => { const tx = ticketTex(THREE, Object.assign({}, o, { col: cssCol }, extra || {}), big), m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tx, side: THREE.DoubleSide, transparent: true })); m.userData.tx = tx; return m; };
  const sign = (txt, w, h, colr2, heavy) => { const cv = document.createElement("canvas"); cv.width = 2048; cv.height = Math.round(2048 * h / w); const x = cv.getContext("2d"), H = cv.height; x.textAlign = "center"; x.textBaseline = "middle"; let fs = H * (heavy ? 0.86 : 0.7); const s2 = String(txt || "").toUpperCase();
    do { x.font = `900 ${fs}px 'Big Shoulders Display', 'Barlow Condensed', Arial, sans-serif`; fs *= 0.95; } while (x.measureText(s2).width > 1960 && fs > 20);
    if (heavy) { x.shadowColor = colr2; x.shadowBlur = 50; x.lineWidth = H * 0.11; x.strokeStyle = colr2; x.strokeText(s2, 1024, H * 0.54); x.shadowBlur = 0; x.lineWidth = H * 0.035; x.strokeStyle = "#0a0d14"; x.strokeText(s2, 1024, H * 0.54); } else { x.lineWidth = H * 0.16; x.strokeStyle = "rgba(6,8,14,.92)"; x.strokeText(s2, 1024, H * 0.54); }
    x.fillStyle = "#fff"; x.fillText(s2, 1024, H * 0.54); const tx = new THREE.CanvasTexture(cv); tx.anisotropy = 16; const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tx, transparent: true, depthWrite: false, side: THREE.DoubleSide })); m.userData.tx = tx; m.renderOrder = 6; return m; };
  const steps = []; let T = 0, dur = 4000; const KT = window.__actK || 1;   // (a test can run the clock slow)
  const M = st.mascot || null, mg = M && M.f.g, mPose = (act, t, k) => M && M.F.poseMascot(M.f, act, t, k), mAt = (x, z, ry) => { if (!M) return; mg.position.x = x; mg.position.z = z; if (ry != null) mg.rotation.y = ry; }; if (M) M.busy = true;
  // a flag for it to carry: the bettor's name, flying
  const flagOn = (txt, c) => { if (!M) return null; const cv = document.createElement("canvas"); cv.width = 1024; cv.height = 512; const x = cv.getContext("2d"); x.fillStyle = cssCol; x.fillRect(0, 0, 1024, 512); x.fillStyle = "rgba(0,0,0,.28)"; x.fillRect(0, 0, 1024, 70); x.fillRect(0, 442, 1024, 70); x.lineWidth = 14; x.strokeStyle = "#fff"; x.strokeRect(7, 7, 1010, 498);
    x.font = "900 250px 'Big Shoulders Display', 'Barlow Condensed', Arial, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; let s2 = String(txt || "").toUpperCase(); while (x.measureText(s2).width > 900 && s2.length > 3) s2 = s2.slice(0, -1); x.lineWidth = 18; x.strokeStyle = "#0a0d14"; x.strokeText(s2, 512, 270); x.fillStyle = "#fff"; x.fillText(s2, 512, 270);
    const tx = new THREE.CanvasTexture(cv); tx.anisotropy = 8; const g = new THREE.Group(), pole = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 2.6, 8), basic([0.85, 0.86, 0.9])); pole.position.y = -1.3; g.add(pole);
    const cg = new THREE.PlaneGeometry(1.9, 1.0, 14, 4); cg.rotateY(-Math.PI / 2); cg.translate(0, -2.06, 0.98); const cloth = new THREE.Mesh(cg, new THREE.MeshBasicMaterial({ map: tx })), back = new THREE.Mesh(cg, new THREE.MeshBasicMaterial({ map: tx, side: THREE.BackSide })); back.scale.z = -1; back.position.z = 1.96; g.add(cloth, back); const p0 = cg.attributes.position.array.slice();
    M.f.hand.add(g); return { g, wave(t) { const a = cg.attributes.position.array; for (let i = 0; i < a.length; i += 3) { const z = p0[i + 2]; a[i] = Math.sin(z * 3.2 - t * 9) * 0.1 * z; a[i + 1] = p0[i + 1] + Math.sin(z * 2.1 - t * 7) * 0.04 * z; } cg.attributes.position.needsUpdate = true; }, off() { M.f.hand.remove(g); pole.geometry.dispose(); pole.material.dispose(); cg.dispose(); cloth.material.dispose(); back.material.dispose(); tx.dispose(); } }; };
  let flag = null; window.__actOn = true;
  const tour = (p, l, f, ms) => { let n = 0; const go = () => { try { if (st !== SBW().st()) return; if (!SBW().tour(p, l, f, ms / KT) && n++ < 14) setTimeout(go, 140); } catch (e) {} }; go(); };

  if (kind === "place") {
    dur = 7000;
    // the drone: body, four arms and rotors, a light, the ticket slung under it
    const dr = add(new THREE.Group()), body = new THREE.Mesh(new THREE.BoxGeometry(5, 1.4, 5), basic([0.1, 0.11, 0.14])); dr.add(body); const rot = [];
    for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) { const arm = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.4, 0.5), basic([0.2, 0.21, 0.25])); arm.position.set(sx * 3.2, 0.3, sz * 3.2); arm.rotation.y = sx * sz > 0 ? -Math.PI / 4 : Math.PI / 4; dr.add(arm);
      const r = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 0.12, 20), addv(o.col, 0.35)); r.position.set(sx * 4.8, 0.9, sz * 4.8); dr.add(r); rot.push(r); }
    const lamp = new THREE.Sprite(new THREE.SpriteMaterial({ map: gt, color: C(o.col), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false })); lamp.scale.set(14, 14, 1); lamp.position.y = -1; dr.add(lamp);
    const tk = add(ticket(26, 9.75, false)), cone = add(new THREE.Mesh(new THREE.ConeGeometry(9, 30, 20, 1, true), addv(o.col, 0.16))); let landed = false;
    const A = [-150, top + 46, -70], B = [-40, top + 30, -10], D = [0, 24, 4], MX = 0, MZ = 4, HY = M ? 5.3 : 0.35; let hit = false; const m0 = M ? [mg.position.x, mg.position.z] : [0, 0];
    steps.push((t, dt) => {
      const k = ease(t / 2.4), k2 = ease((t - 2.4) / 0.8), off = ease((t - 3.4) / 2.4);
      const px = lerp(lerp(A[0], B[0], k), lerp(B[0], D[0], k), k) + off * 170, py = lerp(lerp(A[1], B[1], k), lerp(B[1], D[1], k), k) - k2 * 10 + off * 70, pz = lerp(lerp(A[2], B[2], k), lerp(B[2], D[2], k), k) - off * 60;
      dr.position.set(px, py + Math.sin(t * 5) * 0.4, pz); dr.rotation.set(Math.sin(t * 2) * 0.05 - off * 0.3, t * 0.25, (1 - k) * 0.25); for (const r of rot) r.rotation.y += dt * 60;
      cone.position.set(px, py - 16, pz); cone.material.opacity = t < 3.2 ? 0.16 : Math.max(0, 0.16 - (t - 3.2) * 0.3);
      // the mascot: out from the sideline, under it, hands up, then the spike
      if (M) { if (t < 2.5) { const u = ease(t / 2.5); mAt(lerp(m0[0], MX, u), lerp(m0[1], MZ, u), Math.atan2(MX - m0[0], MZ - m0[1])); mPose("run", t); } else if (t < 4.3) { mg.rotation.y += (0.25 - mg.rotation.y) * 0.2; mPose("catch", t); } else if (t < 4.75) mPose("spike", t, (t - 4.3) / 0.3); else mPose("cheer", t); }
      if (t < 3.2) { tk.position.set(px, py - 7, pz); tk.rotation.set(0, dr.rotation.y, Math.sin(t * 3) * 0.06); if (Math.random() < 0.5) spark([px, py - 2, pz], [(Math.random() - 0.5) * 4, -6, (Math.random() - 0.5) * 4], o.col, 0.7); }
      else if (t < 4.3) { const f = cl((t - 3.2) / 0.55), y0 = D[1] - 10 - 7; tk.position.set(MX, lerp(y0, HY + 2.6, f * f) + (f >= 1 ? Math.sin(t * 9) * 0.15 : 0), MZ + 0.4); tk.rotation.set(0, tk.rotation.y * (1 - f) + 0.25 * f, 0); const sc = lerp(1, M ? 0.42 : 1, f); tk.scale.set(sc, sc, 1); }
      else if (t < 4.6) { const f = cl((t - 4.3) / 0.3); tk.position.set(MX + 1.2 * f, lerp(HY + 2.6, 0.35, f * f), MZ + 0.4 + 5 * f); tk.rotation.set(-Math.PI / 2 * f, 0.25, 0); const sc = lerp(M ? 0.42 : 1, 1, f); tk.scale.set(sc, sc, 1); }
      else { if (!hit) { hit = true; const P = [MX + 1.2, 0, MZ + 5.4]; for (const r of [ringOn(o.col, 60), ringOn([1, 1, 1], 34)]) r.position.set(P[0], 0.2, P[2]); beamUp(o.col, P[0], P[2], 2, 150); burst([P[0], 2, P[2]], o.col, 320, 46); st.flash = 1.3; st.fc = o.col; st.burst = 0.5; st.wave = 1; st.cheer = 1; try { SBW().burst && SBW().burst([0, top + 20, 0], o.col, 180); } catch (e) {} }
        tk.position.y = 0.35 + Math.max(0, Math.sin((t - 4.6) * 9)) * Math.exp(-(t - 4.6) * 4) * 2; tk.material.opacity = cl((dur / 1000 - 0.3 - t) * 2.5); st.cheer = Math.max(st.cheer || 0, cl((dur / 1000 - 0.6 - t))); }
    });
    tour(M ? [-15, 6.5, 27] : [-34, 30, 56], M ? [0, 5.5, 5] : [0, 6, 0], 46, 2400);
  } else if (kind === "win") {
    const tier = o.tier || 1; dur = tier === 3 ? 13500 : tier === 2 ? 11000 : 9200; const D = dur / 1000, J0 = 3.3; flag = flagOn(o.who, o.col); const m0 = [-44, 5];
    // the flyover: three jets, wingtip to wingtip, trailing the colours
    const jets = [-1, 0, 1].map((k) => { const j = add(new THREE.Group()), f = new THREE.Mesh(new THREE.ConeGeometry(1.6, 13, 8), basic([0.8, 0.82, 0.86])); f.rotation.z = -Math.PI / 2; j.add(f); const w = new THREE.Mesh(new THREE.BoxGeometry(4, 0.3, 11), basic([0.6, 0.62, 0.68])); w.position.x = -2; j.add(w); const tl = new THREE.Mesh(new THREE.BoxGeometry(2, 3, 0.3), basic([0.6, 0.62, 0.68])); tl.position.set(-5.5, 1.4, 0); j.add(tl); j.userData = { k, c: [o.col, [1, 1, 1], GOLD][k + 1] }; j.scale.setScalar(2.2); return j; });
    // the coins: hundreds, into the bowl, a bounce off the turf
    const NC = tier === 3 ? 620 : tier === 2 ? 420 : 260, cg = new THREE.CylinderGeometry(1.05, 1.05, 0.24, 20), coins = add(new THREE.InstancedMesh(cg, M ? new THREE.MeshPhongMaterial({ color: C([1, 0.72, 0.16]), shininess: 120, specular: C([1, 0.95, 0.7]), emissive: C([0.35, 0.22, 0.02]) }) : basic([1, 0.78, 0.2]), NC)); coins.frustumCulled = false;
    const cs = Array.from({ length: NC }, () => ({ p: [(Math.random() - 0.5) * 104, top * 0.5 + Math.random() * 70, (Math.random() - 0.5) * 50], v: [(Math.random() - 0.5) * 6, -8 - Math.random() * 10, (Math.random() - 0.5) * 6], r: [Math.random() * 6, Math.random() * 6, Math.random() * 6], w: [(Math.random() - 0.5) * 14, (Math.random() - 0.5) * 14, (Math.random() - 0.5) * 14], t0: 3.1 + Math.random() * (D - 7.2), b: 0 }));
    const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _p = new THREE.Vector3(), _s = new THREE.Vector3();
    // the ticket, unrolled across midfield
    const ban = add(ticket(78, 29.25, true, { bg: "#0f3b27", edge: "#ffd66b", subCol: "#bff5d8" })); ban.rotation.x = -Math.PI / 2; ban.position.set(0, 0.4, 0); ban.scale.set(0.001, 1, 1);
    // searchlights from the corners, and a column of light where it lies
    const lights = [[-55, -24], [55, -24], [-55, 24], [55, 24], [0, -30], [0, 30]].map(([x, z], i) => { const g = new THREE.ConeGeometry(11, 170, 18, 1, true); g.translate(0, 85, 0); const m = add(new THREE.Mesh(g, addv(i % 2 ? GOLD : o.col, 0))); m.position.set(x, 0, z); m.userData.i = i; return m; });
    let lastFw = 0, lit = false;
    steps.push((t, dt) => {
      for (const j of jets) { const k = j.userData.k, u = (t - J0 - Math.abs(k) * 0.12) / 3.6, x = lerp(-300, 300, u); j.visible = u > 0 && u < 1; j.position.set(x, top + 12 + Math.sin(u * Math.PI) * 8, k * 30 + 4); j.rotation.z = Math.cos(u * Math.PI) * 0.15;
        if (j.visible) for (let q = 0; q < 5; q++) spark([x - 16 - q * 5, j.position.y + (Math.random() - 0.5), j.position.z + (Math.random() - 0.5) * 2], [0, -1.5, 0], j.userData.c, 2.6, 0.4); }
      for (let i = 0; i < NC; i++) { const c = cs[i]; let sc = 0; if (t > c.t0) { c.v[1] -= 22 * dt; for (let a = 0; a < 3; a++) { c.p[a] += c.v[a] * dt; c.r[a] += c.w[a] * dt; } if (c.p[1] < 0.6 && c.v[1] < 0) { if (c.b < 2) { c.v[1] *= -0.35; c.b++; c.p[1] = 0.6; for (let a = 0; a < 3; a++) c.w[a] *= 0.5; } else { c.p[1] = 0.3; c.v = [0, 0, 0]; c.w = [0, 0, 0]; c.r[0] = Math.PI / 2; c.r[2] = 0; } } sc = cl((D - 0.6 - t) * 2); }
        _e.set(c.r[0], c.r[1], c.r[2]); _q.setFromEuler(_e); _p.set(c.p[0], c.p[1], c.p[2]); _s.set(sc, sc, sc); _m.compose(_p, _q, _s); coins.setMatrixAt(i, _m); } coins.instanceMatrix.needsUpdate = true;
      const un = ease((t - 2.5) / 1.0);
      if (M) { if (t < 2.4) { mAt(lerp(m0[0], 0, t / 2.4), m0[1], Math.PI / 2); mPose("carry", t); } else if (t < 3.3) { mg.rotation.y += (0.3 - mg.rotation.y) * 0.25; mPose("flip", t, (t - 2.4) / 0.9); } else mPose(t % 5 < 3.2 ? "dance" : "cheer", t); if (flag) flag.wave(t); }
      if (t > 2.4 && t < D - 0.8) st.cheer = 1; ban.scale.set(Math.max(0.001, un), 1, 1); ban.material.opacity = cl((D - 0.7 - t) * 2); ban.position.y = 0.4 + Math.sin(t * 2.2) * 0.12;
      if (un >= 1 && !lit) { lit = true; ringOn(GOLD, 90); ringOn(o.col, 60); beamUp(GOLD, 0, 0, 3.2, 190); burst([0, 3, 0], GOLD, 300, 60); st.flash = 0.9; st.fc = GOLD; st.wave = 1.3; st.burst = 0.6; }
      for (const m of lights) { const i = m.userData.i, on = cl((t - 3) / 0.8) * cl((D - 1 - t) * 1.5); m.material.opacity = 0.05 * on; m.rotation.z = Math.sin(t * 0.9 + i * 1.3) * 0.45; m.rotation.x = Math.cos(t * 0.7 + i * 2.1) * 0.4; }
      if (t > 3.2 && t < D - 1.2 && t - lastFw > (tier === 3 ? 0.4 : 0.75)) { lastFw = t; const a = Math.random() * 6.283, c = [GOLD, o.col, [1, 1, 1], [0.3, 0.9, 0.55]][Math.floor(Math.random() * 4)], p = [Math.cos(a) * 95, top + 25 + Math.random() * 35, Math.sin(a) * 60]; burst(p, c, 150, 34); st.flash = Math.max(st.flash, 0.7); st.fc = c; try { SBW().burst && SBW().burst(p, c, 120); } catch (e) {} }
      if (t > 1 && t < D - 1.5) { st.wave = Math.max(st.wave, 0.9); st.burst = Math.max(st.burst, 0.35); }
    });
    const cams = M ? [[0, [-9, 3.2, 26], [-7, 4, 5], 46, 1100], [2500, [0, 104, 34], [0, 0, 0], 44, 2300], [Math.max(5300, dur * 0.56), [10, 3.6, 19], [0, 5, 4], 40, 1900]] : [[0, [0, 104, 34], [0, 0, 0], 44, 2600], [Math.min(5200, dur * 0.5), [-46, 16, 54], [6, 6, -6], 50, 3600]];
    for (const [at, p, l, f, ms] of cams) setTimeout(() => tour(p, l, f, ms), at / KT);
  } else if (kind === "score") {
    // the game scores: the word stands up out of that end zone, pyro off the posts, the ball through the air, and every
    // bet riding on it called out on the grass, green or red
    const call = o.call || ""; dur = call ? 5400 : 6800; const D = dur / 1000, sd = o.side || 1, X0 = call ? Math.max(-30, Math.min(30, (o.x || 0) + sd * 8)) : sd * 38, home = !!o.home, camP = [X0 - sd * 46, 13, 46], nX = X0 - sd * 16;
    const word = add(sign(o.big, 70, 17.5, cssCol, true)), sub = add(sign(o.sub, 56, 7, "#ffffff", false)); for (const m of [word, sub]) { m.position.set(X0, -20, 0); m.lookAt(camP[0], 12, camP[2]); }
    const notes = (o.notes || []).slice(0, 3).map((nt, i, a) => { const m = add(ticket(15, 5.6, false, { who: nt.who, big: nt.pick, sub: (nt.good ? "▲ " : "▼ ") + nt.tx, odds: "", col: nt.col, bg: nt.good ? "#0f3b27" : "#3b1218", edge: nt.good ? "#36e08a" : "#ff5468", subCol: nt.good ? "#8ff5c0" : "#ff9aa5" })); const q = (i - (a.length - 1) / 2) * 16.5; m.userData.x = nX + q * 0.69; m.userData.z = 17 + q * sd * 0.72; m.userData.good = nt.good; m.position.set(m.userData.x, -8, m.userData.z); m.lookAt(camP[0], 9, camP[2]); return m; });
    const ball = add(new THREE.Group()), bm = M ? new THREE.MeshPhongMaterial({ color: C([0.45, 0.2, 0.08]), shininess: 40 }) : basic([0.5, 0.25, 0.1]), bb = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), bm); bb.scale.set(3.1, 1.75, 1.75); ball.add(bb);
    for (const bx of [-1.9, 1.9]) { const r = new THREE.Mesh(new THREE.TorusGeometry(1.32, 0.13, 6, 24), basic([0.95, 0.95, 0.95])); r.rotation.y = Math.PI / 2; r.position.x = bx; ball.add(r); } { const l = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.16, 0.3), basic([0.95, 0.95, 0.95])); l.position.y = 1.72; ball.add(l); }
    ball.visible = !call; const zone = call === "redzone" ? add(new THREE.Mesh(new THREE.PlaneGeometry(20, 53.3), addv([1, 0.12, 0.1], 0))) : null; if (zone) { zone.rotation.x = -Math.PI / 2; zone.position.set(sd * 40, 0.12, 0); }
    const fg = o.pts === 3, m0 = M ? [mg.position.x, mg.position.z] : [0, 0]; let lastFw = 0, popped = 0;
    steps.push((t, dt) => {
      const up = ease(t / 0.7), out = cl((D - 0.5 - t) * 2.2), bounce = 1 + Math.sin(Math.min(1, t / 0.9) * Math.PI) * 0.12;
      word.position.y = lerp(-20, 15, up) - (1 - out) * 40; word.scale.set(bounce, bounce, 1); sub.position.y = lerp(-20, 3.8, ease((t - 0.35) / 0.6)) - (1 - out) * 30; word.material.opacity = sub.material.opacity = out;
      notes.forEach((m, i) => { const k = ease((t - 1.1 - i * 0.28) / 0.45); m.position.y = lerp(-8, 4.4, k) + Math.sin(t * 2.4 + i) * 0.25 - (1 - out) * 16; if (k >= 1 && popped === i) { popped++; const c = m.userData.good ? [0.2, 0.9, 0.55] : [1, 0.33, 0.41]; burst([m.userData.x, 6, m.userData.z], c, 90, 22); const r = ringOn(c, 16); r.position.set(m.userData.x, 0.2, m.userData.z); } });
      if (zone) zone.material.opacity = (0.16 + 0.12 * Math.sin(t * 7)) * out * cl(t * 2);
      if (call) { if (M) mPose(call === "turnover" ? (home ? "cheer" : "sad") : "idle", t); if (call === "turnover" && home && t < D - 1.5) st.cheer = 1; return; }
      if (fg) { const u = cl(t / 1.7), bx = sd * lerp(18, 80, u), by = 1 + Math.sin(u * Math.PI * 0.82) * 30; ball.position.set(bx, by, 0); ball.rotation.z = -t * 14 * sd; ball.visible = u < 1; if (u < 1) spark([bx, by, 0], [0, 0, 0], o.col, 0.8); }
      else { const dr = cl(t / 0.9); ball.position.set(X0, lerp(70, 31, dr * dr) + Math.abs(Math.sin(Math.max(0, t - 0.9) * 5)) * 3 * Math.exp(-(t - 0.9) * 1.2), 0); ball.rotation.set(Math.sin(t * 2) * 0.2, t * 2.4, 0.35); ball.scale.setScalar(out * 1.25); }
      // pyro off both posts and along the back of the end zone
      if (t > 0.3 && t < D - 1.6) for (const z of [-11, 11, -24, 24]) for (let q = 0; q < 3; q++) spark([sd * 61, 1, z], [(Math.random() - 0.5) * 7, 30 + Math.random() * 26, (Math.random() - 0.5) * 7], Math.random() < 0.5 ? o.col : GOLD, 1.3 + Math.random() * 0.6, 30);
      if (t > 0.5 && t < D - 1.4 && t - lastFw > 0.55) { lastFw = t; const c = [GOLD, o.col, [1, 1, 1]][Math.floor(Math.random() * 3)], p = [sd * (30 + Math.random() * 45), top * 0.6 + Math.random() * 30, (Math.random() - 0.5) * 70]; burst(p, c, 150, 32); st.flash = Math.max(st.flash, 0.5); st.fc = c; try { SBW().burst && SBW().burst(p, c, 100); } catch (e) {} }
      if (t < D - 1.5) { st.wave = Math.max(st.wave, home ? 1.1 : 0.4); if (home) st.cheer = 1; }
      if (M) { if (!home) { mPose("sad", t); } else if (t < 1.3) { const u = ease(t / 1.3), tx = sd * 30, tz = 13; mAt(lerp(m0[0], tx, u), lerp(m0[1], tz, u), Math.atan2(tx - m0[0], tz - m0[1])); mPose("run", t); } else { mg.rotation.y += (-sd * 0.5 - mg.rotation.y) * 0.2; mPose(t % 3 < 1 && t < 2.4 ? "flip" : "dance", t, ((t - 1.3) % 3) / 0.9); } }
    });
    tour(camP, [X0, 10, 0], 48, 1500);
  } else if (kind === "swing") {
    // a bet changes sides: its ticket stands up out of the turf under an arrow, green and rising or red and falling
    dur = 4400; const D = dur / 1000, good = !!o.good, c = good ? [0.2, 0.9, 0.55] : [1, 0.33, 0.41], cam = st.cam && st.cam.position, bx = o.x || 0;
    const card = add(ticket(30, 11.25, false, { bg: good ? "#0f3b27" : "#3b1218", edge: good ? "#36e08a" : "#ff5468", subCol: good ? "#8ff5c0" : "#ff9aa5" })), arrow = add(new THREE.Group());
    const am = M ? new THREE.MeshPhongMaterial({ color: C(c), emissive: C(c, 0.45), shininess: 80 }) : basic(c), head = new THREE.Mesh(new THREE.ConeGeometry(3.8, 4.8, 4), am), shaft = new THREE.Mesh(new THREE.BoxGeometry(2.5, 4.4, 2.5), am); head.position.y = 2.2; shaft.position.y = -2.2; arrow.add(head, shaft); if (!good) arrow.rotation.x = Math.PI;
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: gt, color: C(c), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false })); glow.scale.set(34, 34, 1); arrow.add(glow); let lit = false;
    steps.push((t, dt) => {
      const up = ease(t / 0.6), out = cl((D - 0.45 - t) * 2.4), y = lerp(-9, 8.5, up) - (1 - out) * 22;
      card.position.set(bx, y + Math.sin(t * 2.2) * 0.3, 4); if (cam) { card.lookAt(cam.x, cam.y * 0.55, cam.z); } card.material.opacity = out;
      arrow.position.set(bx, y + 14 + (good ? 1 : -1) * ((t * 5) % 4 - 2), 4); arrow.rotation.y = t * 2.6; arrow.scale.setScalar(out * (0.8 + up * 0.2));
      if (up >= 1 && !lit) { lit = true; const r = ringOn(c, 40); r.position.x = bx; r.position.z = 4; beamUp(c, bx, 4, 1.6, 120); burst([bx, 4, 4], c, 200, 36); st.flash = 0.6; st.fc = c; if (good) st.wave = Math.max(st.wave, 0.8); else st.dim = Math.max(st.dim, 0.5); }
      if (t > 0.5 && t < D - 0.8) for (let q = 0; q < 3; q++) spark([bx + (Math.random() - 0.5) * 40, good ? 1 : 26, 4 + (Math.random() - 0.5) * 6], [0, good ? 16 + Math.random() * 10 : -14 - Math.random() * 8, 0], c, 1.1, 0);
      if (M) mPose(good ? "cheer" : "sad", t);
    });
  } else {
    dur = 5000; const m0 = M ? [-26, 9] : [0, 0];
    const tk = add(ticket(40, 15, false, { bg: "#3b1218", edge: "#ff5468", subCol: "#ff9aa5" })); tk.rotation.x = -Math.PI / 2; tk.position.set(0, 0.4, 0);
    const zig = () => { const p = [], n = 9; for (let i = 0; i <= n; i++) { const f = i / n; p.push(new THREE.Vector3((1 - f) * 34 + (i && i < n ? (Math.random() - 0.5) * 16 : 0), (1 - f) * (top + 80) + 0.5, (1 - f) * -22 + (i && i < n ? (Math.random() - 0.5) * 16 : 0))); } return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(p, false, "catmullrom", 0), 40, 0.9, 5, false); };
    const bolt = add(new THREE.Mesh(zig(), addv([1, 0.9, 0.95], 0))), halo = add(new THREE.Mesh(zig(), addv([1, 0.3, 0.4], 0))); halo.scale.set(1.02, 1, 1.02); let struck = false;
    const sh = Array.from({ length: 90 }, () => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(0.7 + Math.random() * 1.3, 0.5 + Math.random() * 1), basic(Math.random() < 0.5 ? [0.9, 0.16, 0.22] : [0.15, 0.17, 0.24], { side: THREE.DoubleSide }))); m.visible = false; m.userData = { v: [(Math.random() - 0.5) * 22, 10 + Math.random() * 16, (Math.random() - 0.5) * 16], w: [Math.random() * 8, Math.random() * 8, Math.random() * 8], p: [(Math.random() - 0.5) * 38, 0.6, (Math.random() - 0.5) * 14] }; return m; });
    steps.push((t, dt) => {
      if (M) { if (t < 1.0) { mAt(lerp(m0[0], -7, t), lerp(m0[1], 6, t), Math.PI / 2); mPose("run", t); } else { mg.rotation.y += (0.5 - mg.rotation.y) * 0.2; mPose("sad", t); } }
      st.dim = Math.max(st.dim, cl(t / 0.5) * cl((dur / 1000 - 0.8 - t) * 2) * 1.1);
      const fl = (a) => Math.max(0, 1 - Math.abs(t - a) * 9), b = Math.max(fl(1.0), fl(1.14) * 0.7, fl(1.42)); bolt.material.opacity = b; halo.material.opacity = b * 0.5;
      if (t > 1.0 && !struck) { struck = true; st.flash = 1.5; st.fc = [1, 0.35, 0.42]; ringOn([1, 0.3, 0.4], 70); burst([0, 2, 0], [1, 0.35, 0.4], 260, 50); tk.visible = false; for (const m of sh) { m.visible = true; m.position.set(...m.userData.p); } }
      if (struck) for (const m of sh) { const u = m.userData; u.v[1] -= 42 * dt; for (let a = 0; a < 3; a++) u.p[a] += u.v[a] * dt; if (u.p[1] < 0.3) { u.p[1] = 0.3; u.v = [u.v[0] * 0.3, 0, u.v[2] * 0.3]; u.w = [0, 0, 0]; } m.position.set(...u.p); m.rotation.x += u.w[0] * dt; m.rotation.y += u.w[1] * dt; m.rotation.z += u.w[2] * dt; m.material.opacity = 1; m.scale.setScalar(cl((dur / 1000 - 0.4 - t) * 2)); }
      else tk.position.y = 0.4 + Math.sin(t * 30) * 0.15 * cl(t - 0.4);
    });
    tour(M ? [-10, 9, 30] : [-30, 34, 52], [0, 2, 0], 44, 1300);
  }
  return new Promise((done) => {
    let last = null, T0 = 0; const f = (now) => {
      if (st !== (SBW().st && SBW().st())) return;   // the building changed under it: it goes with the building
      const dt = last == null ? 0.016 : Math.min(0.1, now - last) * KT; if (last == null) T0 = now; last = now; T = (now - T0) * KT;
      for (const s of steps) try { s(T, dt); } catch (e) {}
      for (let i = 0; i < NP; i++) { if (life[i] <= 0) continue; life[i] -= dt; const k = Math.max(0, life[i] / mx[i]); vel[i * 3 + 1] -= grav[i] * dt; for (let a = 0; a < 3; a++) { pos[i * 3 + a] += vel[i * 3 + a] * dt; colr[i * 3 + a] = base[i * 3 + a] * k; } if (life[i] <= 0) pos[i * 3] = 9999; }
      pg.attributes.position.needsUpdate = true; pg.attributes.color.needsUpdate = true;
      for (const m of rings) { m.userData.t += dt; const k = m.userData.t / 1.4, s = 1 + ease(k) * m.userData.r1; m.scale.set(s, s, 1); m.material.opacity = Math.max(0, 1 - k); }
      for (const m of beams) { m.userData.t += dt; m.material.opacity = Math.max(0, 0.2 - m.userData.t * 0.16); m.scale.x = m.scale.z = 1 + m.userData.t * 0.4; }
    };
    (st.spin = st.spin || []).push(f);
    setTimeout(() => { const i = st.spin.indexOf(f); if (i >= 0) st.spin.splice(i, 1); for (const m of own) { scene.remove(m); m.traverse && m.traverse((x) => { if (x.geometry) x.geometry.dispose(); if (x.material) { if (x.userData && x.userData.tx) x.userData.tx.dispose(); x.material.dispose(); } }); } gt.dispose(); if (flag) flag.off(); window.__actOn = false; if (M) { M.busy = false; mg.rotation.x = 0; } try { SBW().home && SBW().home(2600); } catch (e) {} done(true); }, dur / KT);
  });
}
