// The stories a cashed bet can have, the team behind it, and the finale for the biggest ones: scenes for the composed
// show (celebrate.js). Each runs on the act's kit K (the scene, sparks, rings, signs) and the composer's H (timing, the
// camera, figures, the bet's own seeded dice). The board already names these stories (betTypes): a whale or a nuke by
// stake, a medal, a parlay long enough to need a receipt, a lotto ticket, a same-game script, a world tour, chalk, a dawg,
// a division rivalry, a night game; and how it was won: a cardiac comeback, by the hook, no sweat.
const cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v)), lerp = (a, b, t) => a + (b - a) * t, ease = (t) => (t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t)), back = (t) => { t = cl(t); const c = 1.9; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const css = (c) => `rgb(${c.map((v) => Math.round(cl(v) * 255)).join(",")})`, lum = (c) => 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
const lift = (c, to = 0.4) => { const l = lum(c), k = l < to ? (to - l) / Math.max(0.05, 1 - l) : 0; return c.map((v) => cl(v + (1 - v) * k)); };

// the chant every NFL fan base knows its team by
export const CHANTS = { ARI: "BIRD GANG", ATL: "RISE UP", BAL: "CAW CAW", BUF: "BILLS MAFIA", CAR: "KEEP POUNDING", CHI: "BEAR DOWN", CIN: "WHO DEY", CLE: "DAWG POUND", DAL: "HOW 'BOUT THEM COWBOYS", DEN: "BRONCOS COUNTRY", DET: "ONE PRIDE", GB: "GO PACK GO", HOU: "H-TOWN", IND: "FOR THE SHOE", JAX: "DUUUVAL", KC: "CHIEFS KINGDOM", LV: "RAIDER NATION", LAC: "BOLT UP", LAR: "WHOSE HOUSE? RAMS HOUSE", MIA: "FINS UP", MIN: "SKOL", NE: "PATS NATION", NO: "WHO DAT", NYG: "BIG BLUE", NYJ: "J-E-T-S JETS JETS JETS", PHI: "FLY EAGLES FLY", PIT: "HERE WE GO STEELERS", SF: "FAITHFUL", SEA: "GO HAWKS", TB: "FIRE THE CANNONS", TEN: "TITAN UP", WSH: "HAIL TO THE COMMANDERS" };
// and the thing each one does when it scores
export const TEAMFX = { ARI: "birds", ATL: "birds", BAL: "birds", PHI: "birds", SEA: "birds", DAL: "fall:star", GB: "fall:cheese", IND: "fall:shoe", LAC: "fall:bolt", SF: "fall:nugget", PIT: "fall:towel", CLE: "fall:bone", KC: "fall:arrow", NO: "fall:fleur", MIA: "dolphins", TB: "cannons", NE: "cannons", MIN: "horn", NYJ: "jets", DET: "roar", CHI: "roar", CAR: "roar", JAX: "roar", CIN: "claws", HOU: "fall:star", TEN: "fall:star" };

// what story a bet tells, from the board's names for it; the first that fits wins
const ORDER = [["cardiac", "cardiac"], ["hook", "hook"], ["nosweat", "nosweat"], ["nuke", "nuke"], ["whale", "whale"], ["botd", "whale"], ["receipt", "receipt"], ["lotto", "lotto"], ["script", "script"], ["tour", "tour"], ["rivalry", "rivalry"], ["dawg", "dawg"], ["chalk", "money"], ["afterdark", "night"], ["degen", "night"], ["prime", "night"], ["gold", "medal"], ["silver", "medal"], ["bronze", "medal"]];
export const STORIES = [...new Set(ORDER.map((x) => x[1]))];
export function storyOf(keys, o) { if (o.force && o.force.story) return STORIES.includes(o.force.story) ? o.force.story : ""; for (const [k, s] of ORDER) if (keys.includes(k)) { if (s === "rivalry" && !(o.game && o.team)) continue; return s; } return ""; }

// ---- small makers ----
function kit3(K) {
  const { THREE } = K, V3 = (x, y, z) => new THREE.Vector3(x, y, z);
  const mx = (p = [0, 0, 0], r = [0, 0, 0], s = [1, 1, 1]) => new THREE.Matrix4().compose(V3(...p), new THREE.Quaternion().setFromEuler(new THREE.Euler(...r)), V3(...s));
  // several geometries as one (positions and normals), each placed by its matrix
  const merge = (list) => { let n = 0; const gs = list.map(([g0, m]) => { const g = g0.index ? g0.toNonIndexed() : g0.clone(); g0.dispose(); if (m) g.applyMatrix4(m); g.computeVertexNormals(); n += g.attributes.position.count; return g; });
    const P = new Float32Array(n * 3), N = new Float32Array(n * 3); let o = 0; for (const g of gs) { P.set(g.attributes.position.array, o); N.set(g.attributes.normal.array, o); o += g.attributes.position.array.length; g.dispose(); }
    const out = new THREE.BufferGeometry(); out.setAttribute("position", new THREE.BufferAttribute(P, 3)); out.setAttribute("normal", new THREE.BufferAttribute(N, 3)); return out; };
  const shape = (pts) => { const s = new THREE.Shape(); pts.forEach(([x, y], i) => (i ? s.lineTo(x, y) : s.moveTo(x, y))); return s; };
  const extrude = (s, d = 0.3, bev = 0.06) => { const g = new THREE.ExtrudeGeometry(s, { depth: d, bevelEnabled: bev > 0, bevelThickness: bev, bevelSize: bev, bevelSegments: 1, curveSegments: 10 }); g.center(); return g; };
  const canvasTex = (w, h, draw) => { const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h); const t = new THREE.CanvasTexture(c); t.anisotropy = 8; t.userData.c = c; return t; };
  const texMesh = (geo, tex, x) => { const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial(Object.assign({ map: tex, transparent: true, side: THREE.DoubleSide }, x || {}))); m.userData.tx = tex; return m; };
  const glow = (c, s) => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: K.gt, color: K.C(c), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false })); sp.scale.set(s, s, 1); return sp; };
  return { V3, mx, merge, shape, extrude, canvasTex, texMesh, glow };
}
// the falling things a team is known by
function fallGeo(K, U, kind) {
  const { THREE } = K;
  if (kind === "star") { const p = []; for (let i = 0; i < 10; i++) { const a = Math.PI / 2 + (i * Math.PI) / 5, r = i % 2 ? 0.45 : 1.1; p.push([Math.cos(a) * r, Math.sin(a) * r]); } return U.extrude(U.shape(p), 0.32, 0.05); }
  if (kind === "bolt") return U.extrude(U.shape([[-0.3, 1.3], [0.55, 1.3], [0.08, 0.25], [0.6, 0.25], [-0.5, -1.35], [-0.08, -0.12], [-0.6, -0.12]]), 0.26, 0.04);
  if (kind === "arrow") return U.extrude(U.shape([[0, 1.4], [0.9, -0.9], [0, -0.45], [-0.9, -0.9]]), 0.26, 0.04);
  if (kind === "cheese") return U.extrude(U.shape([[0, 0], [1.7, 0], [0, 1.05]]), 0.9, 0.04);
  if (kind === "shoe") { const g = new THREE.TorusGeometry(0.85, 0.24, 8, 18, Math.PI * 1.45); g.rotateZ(-Math.PI * 0.225 + Math.PI / 2); g.center(); return g; }
  if (kind === "nugget") return new THREE.DodecahedronGeometry(0.85, 0);
  if (kind === "towel") return new THREE.PlaneGeometry(2.2, 1.15, 4, 2);
  if (kind === "bone") return U.merge([[new THREE.CylinderGeometry(0.22, 0.22, 2.2, 10), U.mx([0, 0, 0], [0, 0, Math.PI / 2])], ...[[-1.1, 0.24], [-1.1, -0.24], [1.1, 0.24], [1.1, -0.24]].map(([x, y]) => [new THREE.SphereGeometry(0.34, 10, 8), U.mx([x, y, 0])])]);
  if (kind === "fleur") return U.merge([[new THREE.SphereGeometry(1, 12, 10), U.mx([0, 0.55, 0], [0, 0, 0], [0.32, 0.85, 0.22])], [new THREE.SphereGeometry(1, 12, 10), U.mx([-0.55, 0.2, 0], [0, 0, 0.75], [0.25, 0.65, 0.2])], [new THREE.SphereGeometry(1, 12, 10), U.mx([0.55, 0.2, 0], [0, 0, -0.75], [0.25, 0.65, 0.2])], [new THREE.BoxGeometry(1.3, 0.2, 0.3), U.mx([0, -0.08, 0])], [new THREE.SphereGeometry(1, 10, 8), U.mx([0, -0.55, 0], [0, 0, 0], [0.22, 0.4, 0.18])]]);
  return new THREE.BoxGeometry(1, 1, 1);
}
// a bird for the birds' teams: body, head, beak, two wings that flap
function birdOf(K, H, c1, c2) {
  const { THREE } = K, g = new THREE.Group(), lit = H.lit, body = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 9), lit(c1, 40)); body.scale.set(1.7, 0.55, 0.62); g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.46, 10, 8), lit(c2, 40)); head.position.set(1.6, 0.28, 0); g.add(head); const beak = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.7, 6), lit([1, 0.74, 0.12])); beak.rotation.z = -Math.PI / 2; beak.position.set(2.2, 0.2, 0); g.add(beak);
  const tail = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.08, 1.1), lit(c1)); tail.position.set(-1.9, 0.05, 0); g.add(tail);
  const wings = [-1, 1].map((s) => { const w = new THREE.Group(), a = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.08, 3.3), lit(c1)), b = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.06, 1.8), lit(c2)); a.position.z = s * 1.65; b.position.set(-0.25, 0, s * 4.1); w.add(a, b); w.position.set(0.15, 0.18, s * 0.3); w.userData.s = s; g.add(w); return w; });
  return { g, wings };
}
// a whale (or, smaller and quicker, a dolphin): head toward +x
function whaleOf(K, H, back, belly, dolphin) {
  const { THREE } = K, g = new THREE.Group(), lit = H.lit, L = dolphin ? 3.6 : 15, R = dolphin ? 1 : 4.3;
  const body = new THREE.Mesh(new THREE.SphereGeometry(1, 30, 18), lit(back, 70)); body.scale.set(L, R, R * 1.08); g.add(body);
  const bel = new THREE.Mesh(new THREE.SphereGeometry(1.01, 30, 12, 0, Math.PI * 2, Math.PI * 0.56, Math.PI * 0.44), lit(belly, 40)); bel.scale.copy(body.scale); g.add(bel);
  if (dolphin) { const sn = new THREE.Mesh(new THREE.ConeGeometry(0.42, 1.6, 10), lit(back, 70)); sn.rotation.z = -Math.PI / 2; sn.position.set(L + 0.5, -0.15, 0); g.add(sn); const dor = new THREE.Mesh(new THREE.ConeGeometry(0.5, 1.6, 6), lit(back, 70)); dor.position.set(-0.3, R + 0.4, 0); dor.rotation.z = 0.5; dor.scale.z = 0.25; g.add(dor); }
  else { for (const z of [-1, 1]) { const eye = new THREE.Mesh(new THREE.SphereGeometry(0.32, 8, 6), lit([0.05, 0.05, 0.06])); eye.position.set(L * 0.72, 0.2, z * R * 0.86); g.add(eye); } const jaw = new THREE.Mesh(new THREE.BoxGeometry(L * 0.9, 0.12, R * 1.9), lit([0.08, 0.1, 0.14])); jaw.position.set(L * 0.42, -R * 0.32, 0); g.add(jaw); }
  for (const z of [-1, 1]) { const fin = new THREE.Mesh(new THREE.BoxGeometry(L * 0.3, 0.16, R * 0.9), lit(back, 60)); fin.position.set(L * 0.3, -R * 0.55, z * R * 0.95); fin.rotation.set(z * 0.5, z * 0.4, -0.3); g.add(fin); }
  const tail = new THREE.Group(); tail.position.x = -L * 0.92; g.add(tail);
  const stock = new THREE.Mesh(new THREE.ConeGeometry(R * 0.55, L * 0.5, 14), lit(back, 70)); stock.rotation.z = Math.PI / 2; stock.position.x = -L * 0.18; tail.add(stock);
  const fl = new THREE.Shape(); fl.moveTo(0, 0); fl.bezierCurveTo(-R * 0.5, R * 0.8, -R * 1.2, R * 1.7, -R * 0.9, R * 2.3); fl.bezierCurveTo(-R * 0.4, R * 1.5, -R * 0.1, R * 0.8, 0, 0); fl.bezierCurveTo(-R * 0.1, -R * 0.8, -R * 0.4, -R * 1.5, -R * 0.9, -R * 2.3); fl.bezierCurveTo(-R * 1.2, -R * 1.7, -R * 0.5, -R * 0.8, 0, 0);
  const flk = new THREE.Mesh(new THREE.ExtrudeGeometry(fl, { depth: R * 0.12, bevelEnabled: false }), lit(back, 60)); flk.rotation.x = Math.PI / 2; flk.position.set(-L * 0.4, 0, 0); tail.add(flk);
  return { g, tail };
}

// ================= the stories =================
export function story(name, t0, len, K, H) {
  const { THREE, st, o, top, add, basic, addv, C, spark, burst, ringOn, beamUp, ticket, sign, M, mg, mPose, mAt, GOLD } = K, { part, word, cam, R, everyone, fwk, hide, gold, lit } = H, U = kit3(K);
  const col = o.col, WHITE = [1, 1, 1], ICE = [0.55, 0.85, 1], GREEN = [0.2, 0.9, 0.55], RED = [1, 0.25, 0.3], WATER = [0.55, 0.82, 1];
  const mascot = (act, x, z, ry) => { if (!M) return; if (x != null) mAt(x, z, ry); return act; };

  if (name === "whale") {
    // a whale breaches out of the field, arcs over the fifty and crashes back in
    const W = whaleOf(K, H, [0.16, 0.22, 0.33], [0.86, 0.89, 0.92], false), wg = add(W.g); wg.visible = false;
    const pool = [-28, 28].map((x) => { const g = add(new THREE.Group()), hole = new THREE.Mesh(new THREE.CircleGeometry(9, 40), new THREE.MeshBasicMaterial({ color: C([0.02, 0.08, 0.16]), transparent: true, opacity: 0 })), rim = new THREE.Mesh(new THREE.RingGeometry(8.6, 10.2, 48), addv(WATER, 0)); hole.rotation.x = rim.rotation.x = -Math.PI / 2; rim.position.y = 0.02; g.add(hole, rim); g.position.set(x, 0.16, 4); return { g, hole, rim }; });
    const sw = (x) => { for (let i = 0; i < 260; i++) { const a = R() * 6.28, sp = 4 + R() * 12; spark([x + Math.cos(a) * 3, 1, 4 + Math.sin(a) * 3], [Math.cos(a) * sp * 0.6, 14 + R() * 26, Math.sin(a) * sp * 0.6], R() < 0.4 ? WHITE : WATER, 1.4 + R() * 0.8, 28); } ringOn(WATER, 30).position.set(x, 0.3, 4); st.flash = Math.max(st.flash, 0.9); st.fc = WATER; st.wave = 1.3; };
    let up = false, down = false;
    part(t0, len, (u) => { for (const p of pool) { p.hole.material.opacity = 0.75 * cl((u - 0.1) * 3) * cl((len - 0.3 - u) * 2); p.rim.material.opacity = 0.5 * cl((u - 0.1) * 3) * cl((len - 0.3 - u) * 2) * (0.7 + 0.3 * Math.sin(u * 8)); }
      const k = cl((u - 0.6) / 3.2); wg.visible = k > 0 && k < 1; if (wg.visible) { const x = lerp(-34, 34, k), y = -14 + 176 * k * (1 - k), vy = 176 * (1 - 2 * k), vx = 68; wg.position.set(x, y, 4); wg.rotation.set(Math.sin(k * Math.PI) * 0.35, 0, Math.atan2(vy, vx)); W.tail.rotation.z = Math.sin(u * 7) * 0.35;
        if (y > 0 && R() < 0.8) spark([x - 8, y - 2, 4 + (R() - 0.5) * 6], [(R() - 0.5) * 4, -6, (R() - 0.5) * 4], WATER, 1.1, 20); }
      if (k > 0.09 && !up) { up = true; sw(-28); } if (k > 0.91 && !down) { down = true; sw(28); st.flash = 1.4; st.burst = 0.9; } if (k > 0.1) everyone(1); }, () => { wg.visible = false; for (const p of pool) p.g.visible = false; });
    word("Whale", t0 + 2.2, len - 2.4, 21, -6, 46, "#7fd6ff"); cam(t0 - 0.2, [-6, 7, 58], [0, 12, 2], 58, 1300); cam(t0 + 2.6, [10, 5, 44], [20, 6, 4], 52, 1200); return true;
  }
  if (name === "nuke") {
    // the lights go, something comes down at the fifty, and the place goes up in gold
    const ms = add(new THREE.Group()), bodyM = lit([0.32, 0.34, 0.38], 80), m1 = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 7, 14), bodyM), m2 = new THREE.Mesh(new THREE.ConeGeometry(0.9, 2.4, 14), lit([0.9, 0.15, 0.12], 60)); m2.position.y = -4.7; m2.rotation.x = Math.PI; ms.add(m1, m2);
    for (let i = 0; i < 4; i++) { const f = new THREE.Mesh(new THREE.BoxGeometry(0.12, 2, 1.6), bodyM); f.position.set(Math.cos((i * Math.PI) / 2) * 0.9, 3.2, Math.sin((i * Math.PI) / 2) * 0.9); f.rotation.y = -(i * Math.PI) / 2; ms.add(f); }
    const fire = add(new THREE.Mesh(new THREE.SphereGeometry(1, 28, 18), addv([1, 0.62, 0.15], 0))), stem = add(new THREE.Mesh(new THREE.CylinderGeometry(1, 1.5, 1, 24, 1, true), addv([1, 0.55, 0.12], 0))), cap = add(new THREE.Mesh(new THREE.SphereGeometry(1, 28, 14), addv([1, 0.75, 0.25], 0))), ring = add(new THREE.Mesh(new THREE.TorusGeometry(1, 0.08, 6, 64), addv([1, 0.85, 0.4], 0))); ring.rotation.x = Math.PI / 2;
    let hit = false;
    part(t0, len, (u, dt) => { st.dim = Math.max(st.dim, cl(u / 0.4) * cl((1.3 - u) * 3) * 1.1); const k = cl(u / 1.3); ms.visible = k < 1; ms.position.set(0, lerp(top + 70, 2, k * k), 6); if (k < 1) for (let q = 0; q < 3; q++) spark([0, ms.position.y + 4, 6], [(R() - 0.5) * 3, 6, (R() - 0.5) * 3], [0.6, 0.6, 0.62], 1.2, -2);
      if (k >= 1 && !hit) { hit = true; st.flash = 2; st.fc = [1, 0.85, 0.5]; st.wave = 1.5; st.burst = 1; ringOn([1, 0.8, 0.3], 120); ringOn(WHITE, 70); burst([0, 3, 6], GOLD, 500, 70); try { window.SBW.burst([0, top, 6], GOLD, 300); } catch (e) {} }
      if (hit) { const v = u - 1.3, f = ease(v / 1.6); fire.scale.setScalar(4 + f * 10); fire.position.set(0, 3 + f * 26, 6); fire.material.opacity = 0.75 * cl((len - 0.4 - u) * 1.5);
        stem.scale.set(3 + f * 3, Math.max(0.01, f * 26), 3 + f * 3); stem.position.set(0, f * 13, 6); stem.material.opacity = 0.45 * cl((len - 0.4 - u) * 1.5);
        cap.scale.set(6 + f * 16, 3 + f * 6, 6 + f * 16); cap.position.set(0, 4 + f * 30, 6); cap.material.opacity = 0.55 * cl(f * 2) * cl((len - 0.4 - u) * 1.5);
        const rk = ease(v / 1.1); ring.scale.setScalar(4 + rk * 110); ring.position.set(0, 1, 6); ring.material.opacity = 0.8 * (1 - rk);
        for (let q = 0; q < 6; q++) { const a = R() * 6.28; spark([Math.cos(a) * 6, 4 + f * 24, 6 + Math.sin(a) * 6], [Math.cos(a) * 6, 10 + R() * 10, Math.sin(a) * 6], R() < 0.5 ? GOLD : [1, 0.5, 0.15], 1.4, -3); } everyone(1); } }, () => { ms.visible = fire.visible = stem.visible = cap.visible = ring.visible = false; });
    word("Nuke", t0 + 2, len - 2.2, 22, -8, 40, "#ffb84d"); cam(t0 - 0.2, [0, 9, 70], [0, 18, 6], 60, 1200); return true;
  }
  if (name === "medal") {
    // the podium comes up, the medal comes down on its ribbon, and it hangs there turning
    const k3 = (o.keys || []).includes("gold") ? 0 : (o.keys || []).includes("silver") ? 1 : 2, MC = [[1, 0.76, 0.2], [0.86, 0.88, 0.92], [0.78, 0.48, 0.26]][k3], NAME = ["Gold", "Silver", "Bronze"][k3];
    const pod = add(new THREE.Group()); [[0, 4.4, MC], [-6.2, 3, [0.86, 0.88, 0.92]], [6.2, 2.1, [0.78, 0.48, 0.26]]].forEach(([x, h, c], i) => { const b = new THREE.Mesh(new THREE.BoxGeometry(6, h, 6), lit([0.12, 0.13, 0.16], 60)); b.position.set(x, h / 2, 0); const tp = new THREE.Mesh(new THREE.BoxGeometry(6.05, 0.4, 6.05), lit(c, 100)); tp.position.set(x, h + 0.05, 0); pod.add(b, tp); const n = add(sign(String(i + 1), 3, 3, "#ffffff", true)); n.userData.p = [x, h * 0.55, 3.05]; pod.userData["n" + i] = n; });
    const med = add(new THREE.Group()), mm = new THREE.MeshPhongMaterial({ color: C(MC), shininess: 140, specular: C([1, 0.95, 0.8]), emissive: C(MC, 0.18) }), disc = new THREE.Mesh(new THREE.CylinderGeometry(4.2, 4.2, 0.7, 48), mm); disc.rotation.x = Math.PI / 2; med.add(disc);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(3.3, 0.24, 10, 48), mm); rim.position.z = 0.36; med.add(rim); const star = new THREE.Mesh(fallGeo(K, U, "star"), mm); star.scale.setScalar(2.1); star.position.z = 0.5; med.add(star);
    for (const s of [-1, 1]) { const rb = new THREE.Mesh(new THREE.BoxGeometry(1.5, 30, 0.12), lit(col, 20)); rb.position.set(s * 1.8, 18.5, -0.1); rb.rotation.z = s * -0.09; med.add(rb); }
    let land = false;
    part(t0, len, (u) => { pod.position.set(0, lerp(-6, 0, ease(u / 0.8)) - (1 - cl((len - u) * 2.5)) * 8, 8); for (let i = 0; i < 3; i++) { const n = pod.userData["n" + i]; n.position.set(n.userData.p[0], pod.position.y + n.userData.p[1], 8 + n.userData.p[2]); n.material.opacity = hide(n, u, len); }
      const k = ease((u - 0.6) / 1.5); med.position.set(0, lerp(70, 13, k) + (k >= 1 ? Math.sin(u * 2) * 0.3 : 0), 8); med.rotation.y = k < 1 ? u * 6 : Math.sin(u * 1.6) * 0.6; med.visible = u < len - 0.3;
      if (k >= 1 && !land) { land = true; ringOn(MC, 50).position.set(0, 0.2, 8); burst([0, 13, 8], MC, 300, 40); beamUp(MC, 0, 8, 1.6, 140); st.flash = 1; st.fc = MC; st.wave = 1.2; }
      if (land && R() < 0.7) { const a = R() * 6.28; spark([Math.cos(a) * 5, 13 + Math.sin(a) * 5, 8.5], [0, 1, 1], R() < 0.5 ? MC : WHITE, 0.8); }
      if (M) { mAt(0, 14.5, 0); mPose(land ? "cheer" : "idle", u); } everyone(land ? 1 : 0.3); }, () => { pod.visible = false; med.visible = false; });
    word(NAME + " medal", t0 + 2.2, len - 2.4, 26, 4, 44, css(lift(MC, 0.5))); cam(t0 - 0.2, [0, 9, 40], [0, 10, 8], 50, 1200); cam(t0 + 2.4, [14, 12, 32], [0, 12, 8], 46, 2200); return true;
  }
  if (name === "receipt") {
    // a printer at one goal line runs the slip the length of the field
    const legs = (o.legs && o.legs.length ? o.legs : ["Leg"]).slice(0, 16), pr = add(new THREE.Group()), box = new THREE.Mesh(new THREE.BoxGeometry(6, 4.5, 11), lit([0.12, 0.13, 0.16], 70)); box.position.y = 2.25; pr.add(box);
    const slot = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.35, 9.4), addv([1, 0.85, 0.4], 0.9)); slot.position.set(3.05, 1.6, 0); pr.add(slot); pr.position.set(-61, 0, 4);
    const items = [`PAID ${o.pay || ""}`, `TOTAL ${o.odds || ""}`, ...legs.slice().reverse().map((t, i) => `LEG ${legs.length - i} ✓ ${t}`), `${(o.who || "").toUpperCase()} · ${legs.length}-LEG PARLAY`, "★ SWEAT BOARD ★"];
    const tex = U.canvasTex(4096, 256, (x, w, h) => { x.fillStyle = "#f6f4ec"; x.fillRect(0, 0, w, h); x.fillStyle = "rgba(0,0,0,.05)"; for (let i = 0; i < w; i += 6) x.fillRect(i, 0, 2, h); x.fillStyle = "#1b1d22"; x.font = "700 92px 'Courier New', Courier, monospace"; x.textBaseline = "middle"; let cx = 30; for (const [i, t] of items.entries()) { x.fillStyle = i === 0 ? "#c4161c" : "#1b1d22"; x.fillText(t.toUpperCase().slice(0, 34), cx, h / 2 + 4); cx += x.measureText(t.toUpperCase().slice(0, 34)).width + 120; if (i < items.length - 1) { x.fillStyle = "#9aa0a6"; x.fillText("·", cx - 80, h / 2 + 4); } } });
    tex.repeat.set(0.001, 1); const strip = add(U.texMesh(new THREE.PlaneGeometry(1, 1), tex, { transparent: false })); strip.rotation.x = -Math.PI / 2; strip.visible = false;
    part(t0, len, (u) => { pr.visible = true; const s = cl(ease((u - 0.4) / 3.4) * 1.0, 0.001, 1), L = s * 112; strip.visible = u > 0.4; strip.scale.set(L, 8.5, 1); strip.position.set(-58 + L / 2, 0.6, 4); tex.repeat.set(s, 1); tex.offset.set(1 - s, 0);
      if (u > 0.4 && u < 3.8) { slot.material.opacity = 0.6 + 0.4 * Math.sin(u * 30); if (R() < 0.5) spark([-58, 1.6, 4 + (R() - 0.5) * 8], [2, 3, 0], [1, 0.85, 0.4], 0.4); }
      if (u > 3.8 && u < 3.9) { burst([54, 2, 4], GOLD, 220, 34); ringOn(GOLD, 40).position.set(54, 0.3, 4); st.flash = 0.9; st.fc = GOLD; st.wave = 1.2; } everyone(u > 3.8 ? 1 : 0.3); }, () => { pr.visible = strip.visible = false; });
    word(`${legs.length}-leg receipt`, t0 + 3.9, len - 4.1, 15, -6, 40, "#ffd66b"); cam(t0 - 0.2, [-40, 30, 40], [-20, 0, 4], 50, 900); cam(t0 + 1.2, [0, 70, 30], [8, 0, 4], 50, 2400); return true;
  }
  if (name === "lotto") {
    // the drum spins, the balls bounce, and the price comes out one ball at a time
    const D0 = [0, 10.5, 6], drum = add(new THREE.Group()), glass = new THREE.Mesh(new THREE.SphereGeometry(6.6, 32, 20), addv([0.6, 0.85, 1], 0.1)); drum.add(glass); for (const rx of [0, Math.PI / 2]) { const r = new THREE.Mesh(new THREE.TorusGeometry(6.7, 0.22, 8, 64), gold()); r.rotation.x = rx; drum.add(r); }
    const stand = new THREE.Mesh(new THREE.CylinderGeometry(1, 2.6, 4.4, 18), lit([0.14, 0.15, 0.18], 70)); stand.position.y = -8.6; drum.add(stand); drum.position.set(...D0);
    const pal = [[0.95, 0.25, 0.3], [0.2, 0.55, 1], [1, 0.8, 0.2], [0.25, 0.85, 0.5], [0.85, 0.4, 1], [1, 0.55, 0.15]], balls = Array.from({ length: 18 }, (_, i) => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.85, 14, 10), lit(pal[i % 6], 90)); m.userData = { p: [(R() - 0.5) * 8, (R() - 0.5) * 8, (R() - 0.5) * 8], v: [(R() - 0.5) * 20, (R() - 0.5) * 20, (R() - 0.5) * 20] }; drum.add(m); return m; });
    const digits = String(Math.abs(Number(o.oddsN) || 1000)).split("").slice(0, 5), out = digits.map((d, i) => { const tx = U.canvasTex(256, 128, (x, w, h) => { x.fillStyle = "#fbfbf6"; x.fillRect(0, 0, w, h); x.fillStyle = css(pal[i % 6]); x.fillRect(0, h * 0.38, w, h * 0.24); for (const cx of [32, 96, 160, 224]) { x.fillStyle = "#fff"; x.beginPath(); x.arc(cx, h / 2, 26, 0, 7); x.fill(); x.fillStyle = "#111"; x.font = "900 40px Arial"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText(d, cx, h / 2 + 2); } });
      const m = add(new THREE.Mesh(new THREE.SphereGeometry(1.7, 24, 16), new THREE.MeshPhongMaterial({ map: tx, shininess: 90 }))); m.userData.tx = tx; m.visible = false; m.userData.to = [(i - (digits.length - 1) / 2) * 4.2, 1.7, 15]; return m; });
    const sg = add(sign("+", 3.4, 3.4, "#ffd66b", true)); sg.visible = false;
    part(t0, len, (u, dt) => { drum.visible = true; drum.position.y = D0[1] + (1 - ease(u / 0.6)) * -16; drum.rotation.y = u * 2.4; drum.rotation.z = Math.sin(u * 1.7) * 0.25;
      for (const b of balls) { const d = b.userData; for (let a = 0; a < 3; a++) d.p[a] += d.v[a] * dt; const r = Math.hypot(...d.p); if (r > 5.6) { const n = d.p.map((v) => v / r), dot = d.v[0] * n[0] + d.v[1] * n[1] + d.v[2] * n[2]; for (let a = 0; a < 3; a++) { d.v[a] -= 2 * dot * n[a]; d.p[a] = n[a] * 5.5; } } b.position.set(...d.p); }
      out.forEach((m, i) => { const k = (u - 1.3 - i * 0.55) / 0.7; if (k <= 0) return; m.visible = u < len - 0.3; const kk = cl(k), to = m.userData.to; m.position.set(lerp(0, to[0], ease(kk)), lerp(D0[1] - 6, to[1], kk) + Math.sin(kk * Math.PI) * 5 + (kk >= 1 ? Math.abs(Math.sin((k - 1) * 9)) * Math.exp(-(k - 1) * 4) * 1.2 : 0), lerp(D0[2], to[2], ease(kk))); m.rotation.y = (1 - kk) * 8; if (k > 1 && !m.userData.hit) { m.userData.hit = true; ringOn(pal[i % 6], 10).position.set(to[0], 0.2, to[2]); burst(m.position.toArray(), pal[i % 6], 60, 16); } });
      if (u > 1.3 + digits.length * 0.55 + 0.6) { sg.visible = u < len - 0.3; sg.position.set(out[0].userData.to[0] - 3.6, 1.8, 15); if (st.cam) sg.lookAt(st.cam.position.x, 1.8, st.cam.position.z); if (!sg.userData.hit) { sg.userData.hit = true; st.flash = 1; st.fc = GOLD; st.wave = 1.3; burst([0, 3, 15], GOLD, 300, 40); } everyone(1); } }, () => { drum.visible = false; for (const m of out) m.visible = false; sg.visible = false; });
    word("Lotto", t0 + 0.4, len - 0.6, 22, 0, 32, "#ffd66b"); cam(t0 - 0.2, [0, 9, 38], [0, 7, 8], 48, 1200); return true;
  }
  if (name === "script") {
    // a clapperboard the size of the end zone: the scene, the take, the legs; it snaps shut and the frames go round
    const g = add(new THREE.Group()), slate = U.canvasTex(1024, 640, (x, w, h) => { x.fillStyle = "#16181d"; x.fillRect(0, 0, w, h); x.strokeStyle = "#e9edf3"; x.lineWidth = 6; x.strokeRect(20, 20, w - 40, h - 40); x.beginPath(); x.moveTo(20, 250); x.lineTo(w - 20, 250); x.moveTo(20, 430); x.lineTo(w - 20, 430); x.moveTo(w / 2, 250); x.lineTo(w / 2, h - 20); x.stroke(); x.fillStyle = "#fff"; x.font = "900 130px 'Big Shoulders Display', 'Barlow Condensed', Arial"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("SCRIPTED", w / 2, 140); x.font = "700 54px 'Barlow Condensed', Arial"; x.fillText("SCENE", w / 4, 300); x.fillText("TAKE", (3 * w) / 4, 300); x.font = "900 80px 'Barlow Condensed', Arial"; x.fillText(o.game ? `${o.game.a.ab}@${o.game.h.ab}` : "THE GAME", w / 4, 375); x.fillText("1", (3 * w) / 4, 375); x.font = "800 60px 'Barlow Condensed', Arial"; x.fillText(`${(o.legs || []).length || 2} LEGS · ONE GAME`, w / 4, 535); x.fillText((o.who || "").toUpperCase(), (3 * w) / 4, 535); });
    const dark = lit([0.08, 0.09, 0.11], 60), board = new THREE.Mesh(new THREE.BoxGeometry(15, 9.4, 0.6), [dark, dark, dark, dark, new THREE.MeshBasicMaterial({ map: slate }), dark]); board.userData.tx = slate; g.add(board);
    const stripes = U.canvasTex(1024, 128, (x, w, h) => { x.fillStyle = "#f2f2f2"; x.fillRect(0, 0, w, h); x.fillStyle = "#111"; for (let i = -2; i < 12; i++) { x.beginPath(); x.moveTo(i * 110, 0); x.lineTo(i * 110 + 55, 0); x.lineTo(i * 110 + 15, h); x.lineTo(i * 110 - 40, h); x.fill(); } });
    const hinge = new THREE.Group(); hinge.position.set(-7.5, 4.7, 0); g.add(hinge); const arm = new THREE.Mesh(new THREE.BoxGeometry(15, 1.9, 0.6), [dark, dark, dark, dark, new THREE.MeshBasicMaterial({ map: stripes }), dark]); arm.userData.tx = stripes; arm.position.set(7.5, 0.95, 0); hinge.add(arm);
    const top2 = new THREE.Mesh(new THREE.BoxGeometry(15, 1.2, 0.6), [dark, dark, dark, dark, new THREE.MeshBasicMaterial({ map: stripes }), dark]); top2.position.set(0, 5.3, 0); g.add(top2);
    const legs = (o.legs || []).slice(0, 8), frames = legs.map((t, i) => { const m = add(ticket(9, 3.4, false, { who: "Leg " + (i + 1), big: t, sub: "✓ In", odds: "", bg: "#101215", edge: "#e9edf3", subCol: "#8ff5c0" })); m.visible = false; return m; });
    let snap = false;
    part(t0, len, (u) => { g.visible = true; g.position.set(0, lerp(-10, 9.5, back(u / 0.9)) - (1 - cl((len - u) * 2.5)) * 18, 6); g.rotation.y = Math.sin(u * 0.8) * 0.12; hinge.rotation.z = u < 1.5 ? 0.62 * cl(u / 0.4) : Math.max(0, 0.62 - (u - 1.5) * 9);
      if (u > 1.55 && !snap) { snap = true; st.flash = 1.3; st.fc = WHITE; burst([0, 14, 6.5], WHITE, 260, 36); ringOn(WHITE, 50).position.set(0, 0.2, 6); st.wave = 1.2; }
      frames.forEach((m, i) => { if (!snap) return; m.visible = u < len - 0.3; const a = u * 0.7 + (i / frames.length) * Math.PI * 2; m.position.set(Math.cos(a) * 22, 9 + Math.sin(u * 2 + i) * 0.6, 6 + Math.sin(a) * 12); if (st.cam) m.lookAt(st.cam.position.x, 9, st.cam.position.z); });
      everyone(snap ? 1 : 0.3); }, () => { g.visible = false; for (const m of frames) m.visible = false; });
    cam(t0 - 0.2, [0, 8, 34], [0, 9, 6], 50, 1000); cam(t0 + 2.4, [0, 26, 52], [0, 8, 6], 52, 2200); return true;
  }
  if (name === "tour") {
    // a passport stamp for every sport the parlay went through, slammed into the turf
    const sports = (o.sports && o.sports.length ? o.sports : ["NFL", "NBA"]).slice(0, 4), INK = [[0.85, 0.12, 0.18], [0.12, 0.35, 0.85], [0.1, 0.6, 0.3], [0.55, 0.2, 0.75]];
    const stamps = sports.map((sp, i) => { const x = (i - (sports.length - 1) / 2) * 24, g = add(new THREE.Group()), blk = new THREE.Mesh(new THREE.CylinderGeometry(5.2, 5.2, 1.6, 40), lit([0.36, 0.22, 0.12], 30)), hd = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.2, 4.5, 16), lit([0.42, 0.26, 0.14], 30)), kn = new THREE.Mesh(new THREE.SphereGeometry(1.6, 16, 12), lit([0.45, 0.28, 0.15], 40)); hd.position.y = 3; kn.position.y = 5.6; g.add(blk, hd, kn);
      const ink = add(new THREE.Group()), ringM = new THREE.Mesh(new THREE.RingGeometry(4.3, 5.1, 48), new THREE.MeshBasicMaterial({ color: C(INK[i % 4]), transparent: true, opacity: 0, side: THREE.DoubleSide })), t = sign(sp, 7, 2.6, css(INK[i % 4]), true); ringM.rotation.x = -Math.PI / 2; t.rotation.x = -Math.PI / 2; t.position.y = 0.05; ink.add(ringM, t); ink.position.set(x, 0.18, 6); ink.userData = { ringM, t };
      g.visible = false; return { x, g, ink, t0: 0.4 + i * 0.85, hit: false, c: INK[i % 4] }; });
    part(t0, len, (u) => { for (const s of stamps) { const k = (u - s.t0) / 0.5; s.g.visible = k > 0 && k < 2.2; if (k > 0) { const down = cl(k), upk = cl(k - 1.3); s.g.position.set(s.x, lerp(30, 0.8, down * down) + upk * 30, 6); s.g.rotation.y = (1 - down) * 2; }
        if (k >= 1 && !s.hit) { s.hit = true; burst([s.x, 0.8, 6], [0.75, 0.7, 0.6], 120, 18); ringOn(s.c, 16).position.set(s.x, 0.25, 6); st.flash = Math.max(st.flash, 0.6); st.fc = s.c; st.wave = 1; }
        const op = s.hit ? 0.85 * cl((len - 0.3 - u) * 2.5) : 0; s.ink.userData.ringM.material.opacity = op; s.ink.userData.t.material.opacity = op; } everyone(u > 0.9 ? 1 : 0.4); }, () => { for (const s of stamps) { s.g.visible = false; s.ink.visible = false; } });
    word("World tour", t0 + 0.6 + sports.length * 0.85, len - 0.8 - sports.length * 0.85, 17, -4, 44, "#ffd66b"); cam(t0 - 0.2, [0, 40, 44], [0, 0, 6], 50, 1300); return true;
  }
  if (name === "money") {
    // chalk is free money: the bank's printer runs and the bills come out over the field
    const pr = add(new THREE.Group()), bx = new THREE.Mesh(new THREE.BoxGeometry(9, 6.5, 6), lit([0.1, 0.32, 0.18], 70)); bx.position.y = 3.25; pr.add(bx);
    const face = U.canvasTex(512, 256, (x, w, h) => { x.fillStyle = "#0d2a17"; x.fillRect(0, 0, w, h); x.strokeStyle = "#7dffa8"; x.lineWidth = 8; x.strokeRect(10, 10, w - 20, h - 20); x.fillStyle = "#c9ffd9"; x.font = "900 84px 'Barlow Condensed', Arial"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("SWEAT BANK", w / 2, h / 2); });
    const fm = U.texMesh(new THREE.PlaneGeometry(8.4, 4.2), face, { transparent: false }); fm.position.set(0, 3.6, 3.02); pr.add(fm); const sl = new THREE.Mesh(new THREE.BoxGeometry(6, 0.3, 0.3), addv([0.5, 1, 0.6], 0.9)); sl.position.set(0, 1.1, 3.1); pr.add(sl); pr.position.set(0, 0, 2);
    const bill = U.canvasTex(256, 112, (x, w, h) => { x.fillStyle = "#cfe8c9"; x.fillRect(0, 0, w, h); x.strokeStyle = "#2f6a3a"; x.lineWidth = 6; x.strokeRect(5, 5, w - 10, h - 10); x.fillStyle = "#2f6a3a"; x.beginPath(); x.ellipse(w / 2, h / 2, 30, 38, 0, 0, 7); x.fill(); x.font = "900 40px Arial"; x.textBaseline = "middle"; x.fillText("100", 16, 32); x.textAlign = "right"; x.fillText("100", w - 16, h - 30); });
    const NB = 220, bm = add(new THREE.InstancedMesh(new THREE.PlaneGeometry(2.6, 1.14), new THREE.MeshBasicMaterial({ map: bill, side: THREE.DoubleSide }), NB)); bm.userData.tx = bill; bm.frustumCulled = false;
    const bs = Array.from({ length: NB }, () => ({ p: [0, 1.4, 5.2], v: [(R() - 0.5) * 26, 9 + R() * 16, 10 + R() * 18], r: [R() * 6, R() * 6, R() * 6], w: [(R() - 0.5) * 10, (R() - 0.5) * 10, (R() - 0.5) * 10], t0: 0.8 + R() * 3, done: false }));
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(), s3 = new THREE.Vector3();
    part(t0, len, (u, dt) => { pr.visible = true; pr.position.y = lerp(-8, 0, back(u / 0.7)) - (1 - cl((len - u) * 2.5)) * 9; sl.material.opacity = u > 0.8 ? 0.6 + 0.4 * Math.sin(u * 40) : 0.2;
      for (let i = 0; i < NB; i++) { const b = bs[i]; let sc = 0; if (u > b.t0) { if (!b.done) { if (b.p[1] > 0.25 || b.v[1] > 0) { b.v[1] -= 13 * dt; b.v[0] *= 0.995; b.v[2] *= 0.995; for (let a = 0; a < 3; a++) { b.p[a] += b.v[a] * dt * (b.v[1] < 0 ? 0.55 : 1); b.r[a] += b.w[a] * dt; } } else { b.done = true; b.p[1] = 0.25; b.r = [-Math.PI / 2, 0, R() * 6]; } } sc = cl((len - 0.3 - u) * 3); }
        e.set(...b.r); q.setFromEuler(e); m4.compose(p3.set(...b.p), q, s3.setScalar(sc)); bm.setMatrixAt(i, m4); } bm.instanceMatrix.needsUpdate = true; if (u > 1) everyone(1); }, () => { pr.visible = false; bm.visible = false; });
    word("Free money", t0 + 1.4, len - 1.6, 19, -4, 46, "#5dff95"); cam(t0 - 0.2, [0, 8, 38], [0, 5, 4], 50, 1000); cam(t0 + 2.2, [-18, 14, 40], [0, 4, 10], 52, 2400); return true;
  }
  if (name === "dawg") {
    // paw prints up the field to a bone the size of a man; the dog in the building howls
    const paw = (s) => { const g = new THREE.Group(), m = new THREE.MeshBasicMaterial({ color: C([0.12, 0.08, 0.05]), transparent: true, opacity: 0 }), pad = new THREE.Mesh(new THREE.CircleGeometry(1.2, 20), m); pad.scale.set(1, 0.85, 1); g.add(pad); for (const [x, y] of [[-1.1, 1.25], [-0.38, 1.75], [0.38, 1.75], [1.1, 1.25]]) { const t = new THREE.Mesh(new THREE.CircleGeometry(0.46, 14), m); t.position.set(x, y, 0); g.add(t); } g.rotation.x = -Math.PI / 2; g.rotation.z = s; g.userData.m = m; return g; };
    const prints = Array.from({ length: 10 }, (_, i) => { const p = add(paw(-Math.PI / 2)); p.position.set(-48 + i * 5.4, 0.14, i % 2 ? 9.5 : 5.5); p.userData.t = 0.25 + i * 0.22; return p; });
    const bone = add(new THREE.Mesh(fallGeo(K, U, "bone"), lit([0.96, 0.94, 0.88], 60))); bone.scale.setScalar(4); bone.visible = false;
    part(t0, len, (u) => { for (const p of prints) { const k = cl((u - p.userData.t) / 0.15); p.userData.m.opacity = 0.85 * k * cl((len - 0.3 - u) * 2.5); if (k > 0 && !p.userData.hit) { p.userData.hit = true; burst([p.position.x, 0.4, p.position.z], [0.7, 0.6, 0.45], 24, 6); } }
      const k = ease((u - 2.6) / 0.8); bone.visible = u > 2.6 && u < len - 0.3; bone.position.set(10, lerp(-4, 9, back(k)), 7.5); bone.rotation.set(0.3, u * 2.4, Math.sin(u * 2) * 0.3);
      if (u > 3.3 && !bone.userData.hit) { bone.userData.hit = true; burst([10, 9, 7.5], [1, 0.9, 0.6], 240, 36); ringOn(col, 36).position.set(10, 0.2, 7.5); st.flash = 0.9; st.fc = [1, 0.9, 0.6]; st.wave = 1.2; }
      if (M) { mAt(16, 11, -0.6); mPose(u > 3.3 ? (M.f.kind === "dog" ? "cheer" : "dance") : "idle", u); } everyone(u > 3.3 ? 1 : 0.3); }, () => { for (const p of prints) p.visible = false; bone.visible = false; });
    word(`Dawg ${o.odds || ""}`.trim(), t0 + 3.4, len - 3.6, 20, -2, 40, "#ffb35c"); cam(t0 - 0.2, [-30, 18, 34], [-24, 0, 7], 50, 900); cam(t0 + 2.4, [2, 7, 32], [10, 8, 7], 48, 1200); return true;
  }
  if (name === "cardiac") {
    // a heartbeat traced across the stadium: flat, a beat, a beat, then the one that won it
    const xs = [-30, 0, 30], pts = []; for (let x = -62; x <= 62; x += 0.5) { let y = 0; xs.forEach((c, i) => { const s = i === 2 ? 1.6 : 1; y += 1.2 * Math.exp(-(((x - (c - 6)) / 1.2) ** 2)) - 1 * Math.exp(-(((x - (c - 1.4)) / 0.35) ** 2)) + 9 * s * Math.exp(-(((x - c) / 0.45) ** 2)) - 2.5 * Math.exp(-(((x - (c + 1.2)) / 0.4) ** 2)) + 2 * Math.exp(-(((x - (c + 6)) / 1.8) ** 2)); }); pts.push(new THREE.Vector3(x, 17 + y, -12)); }
    const curve = new THREE.CatmullRomCurve3(pts), tg = new THREE.TubeGeometry(curve, 900, 0.32, 6, false), line = add(new THREE.Mesh(tg, addv([0.3, 1, 0.5], 0.95))), N = tg.index.count; tg.setDrawRange(0, 0);
    const pen = add(U.glow([0.6, 1, 0.7], 9)); pen.visible = false;
    const hs = new THREE.Shape(); hs.moveTo(0, -1.6); hs.bezierCurveTo(-0.6, -1, -2.4, 0.2, -2.2, 1.2); hs.bezierCurveTo(-2, 2.2, -0.6, 2.4, 0, 1.3); hs.bezierCurveTo(0.6, 2.4, 2, 2.2, 2.2, 1.2); hs.bezierCurveTo(2.4, 0.2, 0.6, -1, 0, -1.6);
    const heart = add(new THREE.Mesh(U.extrude(hs, 1.2, 0.25), new THREE.MeshPhongMaterial({ color: C([0.92, 0.1, 0.18]), shininess: 90, emissive: C([0.35, 0, 0.05]) }))); heart.visible = false; let beat = 0, bt = -9;
    part(t0, len, (u) => { st.dim = Math.max(st.dim, 0.45 * cl(u * 2) * cl((len - 0.6 - u) * 2)); const f = cl((u - 0.3) / 3.6); tg.setDrawRange(0, Math.floor((N * f) / 3) * 3); line.material.opacity = 0.95 * cl((len - 0.3 - u) * 2.5);
      pen.visible = f > 0 && f < 1; if (pen.visible) pen.position.copy(curve.getPointAt(f));
      const nb = xs.filter((c) => f >= (c + 62) / 124).length; if (nb > beat) { beat = nb; bt = u; const big = nb === 3; st.flash = big ? 1.4 : 0.8; st.fc = RED; st.burst = big ? 1 : 0.6; st.wave = big ? 1.3 : 0.7; burst(curve.getPointAt(f).toArray(), big ? RED : [0.4, 1, 0.55], big ? 320 : 120, big ? 44 : 24); }
      heart.visible = u > 0.3 && u < len - 0.3; const pulse = Math.exp(-(u - bt) * 5) * (beat === 3 ? 0.5 : 0.28); heart.position.set(0, 7 + Math.sin(u * 1.4) * 0.3, 8); heart.scale.setScalar(2.2 * (1 + pulse) * cl((u - 0.3) * 3)); heart.rotation.y = Math.sin(u * 0.9) * 0.4; everyone(beat === 3 ? 1 : 0.4); }, () => { line.visible = false; pen.visible = false; heart.visible = false; });
    word("Cardiac", t0 + 3.6, len - 3.8, 24, -8, 40, "#ff5a6e"); cam(t0 - 0.2, [0, 12, 64], [0, 14, -10], 58, 1200); return true;
  }
  if (name === "hook") {
    // won by half a point: a hook on a line comes down out of the night and takes the ticket up with it
    const tk = add(ticket(17, 6.4, false)); tk.rotation.x = -Math.PI / 2; tk.position.set(0, 0.45, 8);
    const hk = add(new THREE.Group()), sm = new THREE.MeshPhongMaterial({ color: C([0.82, 0.84, 0.88]), shininess: 140, specular: C([1, 1, 1]) }), sh = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 9, 14), sm); sh.position.set(2.4, 4.5, 0); hk.add(sh);
    const bend = new THREE.Mesh(new THREE.TorusGeometry(2.4, 0.42, 12, 28, Math.PI), sm); bend.rotation.z = Math.PI; hk.add(bend); const barb = new THREE.Mesh(new THREE.ConeGeometry(0.62, 1.8, 10), sm); barb.position.set(-2.4, 0.8, 0); hk.add(barb); const eye = new THREE.Mesh(new THREE.TorusGeometry(0.75, 0.2, 8, 16), sm); eye.position.set(2.4, 9.6, 0); eye.rotation.y = Math.PI / 2; hk.add(eye);
    const ln = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 160, 6), basic([0.9, 0.92, 0.95])); ln.position.set(2.4, 90, 0); hk.add(ln);
    let got = false;
    part(t0, len, (u) => { const d = ease(u / 1.5), yk = ease((u - 2.1) / 1.6), x = lerp(-0.6, 0, ease((u - 1.5) / 0.4)), y = lerp(72, 3.4, d) + yk * 24, sw = u > 2.1 ? Math.sin((u - 2.1) * 4) * 0.25 * Math.exp(-(u - 2.1) * 0.8) : 0; hk.position.set(x, y, 8); hk.rotation.z = sw;
      if (u > 1.9 && !got) { got = true; st.flash = 1.2; st.fc = [0.6, 0.9, 1]; burst([x, 1.5, 8], WHITE, 220, 30); ringOn([0.6, 0.9, 1], 30).position.set(0, 0.25, 8); st.wave = 1.2; }
      if (got) { const a = ease((u - 1.9) / 0.5), hx = x + Math.sin(sw) * 2.4, hy = y - 2.4 * Math.cos(sw); tk.rotation.set(-Math.PI / 2 * (1 - a), 0, sw * a); tk.position.set(lerp(0, hx, a), lerp(0.45, hy - 3.6, a), 8); } everyone(got ? 1 : 0.3); }, () => { hk.visible = false; tk.visible = false; });
    word("By the hook", t0 + 2.2, len - 2.4, 22, -4, 46, "#8fd8ff"); cam(t0 - 0.2, [0, 6, 30], [0, 3, 8], 52, 900); cam(t0 + 2, [9, 10, 34], [0, 14, 8], 52, 1800); return true;
  }
  if (name === "nosweat") {
    // won by a mile: frost on the field, snow out of a clear night, the mascot in shades
    let shades = null; if (M && M.f && M.f.j && M.f.j.head) { shades = new THREE.Group(); const lm = new THREE.MeshPhongMaterial({ color: C([0.03, 0.03, 0.05]), shininess: 150, specular: C([0.8, 0.9, 1]) }); for (const x of [-0.17, 0.17]) { const l = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.04, 20), lm); l.rotation.x = Math.PI / 2; l.position.set(x, 0.47, 0.47); shades.add(l); } const br = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.035, 0.035), lm); br.position.set(0, 0.5, 0.48); shades.add(br); for (const x of [-0.33, 0.33]) { const arm = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.03, 0.42), lm); arm.position.set(x, 0.48, 0.28); shades.add(arm); } }
    const frost = add(new THREE.Mesh(new THREE.CircleGeometry(1, 64), addv(ICE, 0))); frost.rotation.x = -Math.PI / 2; frost.position.set(0, 0.3, 4);
    part(t0, len, (u) => { const fr = ease(u / 2.4); frost.scale.setScalar(1 + fr * 60); frost.material.opacity = 0.07 * cl(u * 2) * cl((len - u) * 2);
      for (let i = 0; i < 6; i++) spark([(R() - 0.5) * 110, 26 + R() * 30, (R() - 0.5) * 60], [1.2, -6 - R() * 4, 0], R() < 0.7 ? WHITE : ICE, 3, 0);
      if (shades && !shades.parent && u > 0.6) { M.f.j.head.add(shades); burst([mg.position.x, 7, mg.position.z], ICE, 80, 14); }
      if (M) { mAt(-4, 10, 0.4); mPose("idle", u * 0.6); } everyone(0.8); }, () => { frost.visible = false; if (shades && shades.parent) { shades.parent.remove(shades); shades.traverse((x) => { if (x.geometry) x.geometry.dispose(); if (x.material) x.material.dispose(); }); } });
    const by = o.game ? Math.abs(o.game.margin || 0) : 0; word("No sweat", t0 + 0.6, len - 0.8, 18, -4, 44, "#bfeaff"); if (by) word(`Won by ${by}`, t0 + 1.1, len - 1.3, 10.5, -3, 26, "#ffffff"); cam(t0 - 0.2, [-8, 6, 26], [-4, 6, 10], 46, 1200); cam(t0 + 2.6, [8, 12, 40], [0, 10, 0], 52, 2200); return true;
  }
  if (name === "rivalry") {
    // a division rival: both flags up; theirs comes down, yours goes up and stays
    const g = o.game, me = o.team, them = g[me.home ? "a" : "h"], flags = [[me, -1], [{ ab: them.ab, nm: them.ab, col: them.col }, 1]].map(([t, s], i) => { const tex = U.canvasTex(512, 320, (x, w, h) => { x.fillStyle = css(t.col); x.fillRect(0, 0, w, h); x.fillStyle = "rgba(0,0,0,.25)"; x.fillRect(0, h - 40, w, 40); x.fillStyle = "#fff"; x.font = "900 170px 'Big Shoulders Display', 'Barlow Condensed', Arial"; x.textAlign = "center"; x.textBaseline = "middle"; x.lineWidth = 12; x.strokeStyle = "rgba(0,0,0,.45)"; x.strokeText(t.ab, w / 2, h / 2); x.fillText(t.ab, w / 2, h / 2); });
      const fg = add(new THREE.Group()), pole = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 26, 10), lit([0.85, 0.86, 0.9], 90)); pole.position.y = 13; fg.add(pole); const cg = new THREE.PlaneGeometry(13, 8, 16, 6); cg.translate(6.5, 0, 0); const cloth = new THREE.Mesh(cg, new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide })); cloth.userData.tx = tex; cloth.position.y = 22; fg.add(cloth); fg.position.set(s * 24, 0, 2); return { fg, cloth, cg, p0: cg.attributes.position.array.slice(), win: i === 0 }; });
    part(t0, len, (u) => { for (const f of flags) { const a = f.cg.attributes.position.array; for (let i = 0; i < a.length; i += 3) { const x = f.p0[i]; a[i + 2] = Math.sin(x * 0.55 - u * 7) * 0.5 * (x / 13) * (f.win || u < 1.4 ? 1 : 0.2); } f.cg.attributes.position.needsUpdate = true;
        if (f.win) { f.fg.position.x = lerp(-24, 0, ease((u - 2) / 1.4)); f.cloth.position.y = 22 + ease((u - 2) / 1.4) * 2; } else { const k = ease((u - 1.4) / 0.8); f.cloth.position.y = lerp(22, 2, k); f.fg.rotation.z = -k * 1.45; f.fg.visible = k < 1; } }
      if (u > 3.4 && !flags[0].hit) { flags[0].hit = true; const c = me.col; ringOn(c, 50).position.set(0, 0.2, 2); burst([0, 20, 2], c, 320, 40); beamUp(c, 0, 2, 1.4, 140); st.flash = 1; st.fc = c; st.wave = 1.4; }
      if (u > 3.4 && R() < 0.12) fwk([(R() - 0.5) * 150, top + 15 + R() * 30, (R() - 0.5) * 90], [me.col, me.alt || WHITE, GOLD][Math.floor(R() * 3)], 120); everyone(u > 3.4 ? 1 : 0.5); }, () => { for (const f of flags) f.fg.visible = false; });
    word("Rivalry win", t0 + 3.4, len - 3.6, 30, -2, 44, css(lift(me.col, 0.5))); cam(t0 - 0.2, [0, 12, 50], [0, 14, 2], 56, 1000); return true;
  }
  if (name === "night") {
    // prime time: the lights go down, a moon comes up over the rim, and the neon comes on
    const after = (o.keys || []).some((k) => k === "afterdark" || k === "degen"), moon = add(new THREE.Group()), ball = new THREE.Mesh(new THREE.SphereGeometry(13, 32, 20), basic([1, 0.96, 0.84])), halo = U.glow([0.9, 0.9, 1], 80); moon.add(ball, halo);
    const n1 = add(sign(after ? "After dark" : "Primetime", 62, 15.5, "#ff4fd8", true)), n2 = add(sign(after ? "After dark" : "Primetime", 62.5, 15.6, "#3ff0ff", true)); n2.position.z = -0.3;
    const lights = [0, 1, 2, 3].map((i) => { const gg = new THREE.ConeGeometry(10, 170, 18, 1, true); gg.translate(0, 85, 0); const m = add(new THREE.Mesh(gg, addv(i % 2 ? [1, 0.3, 0.85] : [0.25, 0.95, 1], 0))); m.position.set(i < 2 ? -50 : 50, 0, i % 2 ? -24 : 24); m.userData.i = i; return m; });
    part(t0, len, (u) => { st.dim = Math.max(st.dim, 0.85 * cl(u / 0.6) * cl((len - 0.5 - u) * 2)); moon.position.set(-70, lerp(-20, 70, ease(u / 2.2)), -170); halo.material.opacity = 0.6;
      const on = u > 1.2 ? (u < 1.6 ? (Math.sin(u * 60) > 0 ? 1 : 0.15) : 1) * cl((len - 0.3 - u) * 2.5) : 0; for (const n of [n1, n2]) { n.material.opacity = on * (n === n2 ? 0.55 : 1); n.position.set(0, 18 + Math.sin(u * 1.4) * 0.3, -6 + (n === n2 ? -0.3 : 0)); if (st.cam) n.lookAt(st.cam.position.x, 18, st.cam.position.z); }
      for (const m of lights) { const i = m.userData.i; m.material.opacity = 0.07 * cl((u - 1.2) * 2) * cl((len - 0.5 - u) * 2); m.rotation.z = Math.sin(u * 1.1 + i * 1.7) * 0.5; m.rotation.x = Math.cos(u * 0.8 + i) * 0.4; }
      if (u > 1.6 && !n1.userData.hit) { n1.userData.hit = true; st.flash = 0.8; st.fc = [1, 0.3, 0.85]; st.wave = 1.2; } everyone(u > 1.6 ? 1 : 0.2); }, () => { moon.visible = false; n1.visible = n2.visible = false; for (const m of lights) m.visible = false; });
    cam(t0 - 0.2, [10, 6, 52], [-14, 24, -40], 60, 1400); return true;
  }
  return false;
}

// ================= the team behind it =================
export function teamScene(t0, len, K, H) {
  const { THREE, st, o, top, add, addv, C, spark, burst, ringOn, beamUp, sign } = K, { part, word, cam, R, everyone, fwk, lit } = H, U = kit3(K), T = o.team; if (!T) return false;
  const c1 = T.col, c2 = T.alt && lum(T.alt) > 0.05 ? T.alt : [1, 1, 1], WHITE = [1, 1, 1], chant = CHANTS[T.ab] || `Let's go ${T.nm || T.ab}`.toUpperCase(), fx = (o.force && o.force.teamfx) || TEAMFX[T.ab] || "confetti";
  // the banner comes down over the far sideline: the logo, the name, the chant
  const tex = U.canvasTex(2048, 512, (x, w, h) => { const gr = x.createLinearGradient(0, 0, w, 0); gr.addColorStop(0, css(c1)); gr.addColorStop(1, css(c1.map((v) => v * 0.55))); x.fillStyle = gr; x.fillRect(0, 0, w, h); x.fillStyle = css(c2); x.fillRect(0, 0, w, 18); x.fillRect(0, h - 18, w, 18);
    x.fillStyle = "#fff"; x.textBaseline = "middle"; x.font = "900 70px 'Barlow Condensed', Arial"; x.fillText(String(T.nm || T.ab).toUpperCase(), 470, 120); let fs = 190; x.font = `900 ${fs}px 'Big Shoulders Display', 'Barlow Condensed', Arial`; while (x.measureText(chant).width > w - 520 && fs > 60) { fs -= 8; x.font = `900 ${fs}px 'Big Shoulders Display', 'Barlow Condensed', Arial`; }
    x.lineWidth = 10; x.strokeStyle = "rgba(0,0,0,.35)"; x.strokeText(chant, 470, 300); x.fillText(chant, 470, 300); x.font = "900 260px 'Big Shoulders Display', Arial"; x.textAlign = "center"; x.fillText(T.ab, 230, h / 2); });
  const ban = add(U.texMesh(new THREE.PlaneGeometry(64, 16), tex, { transparent: false })); ban.position.set(0, 60, -18);
  if (T.lg) { const im = new Image(); im.crossOrigin = "anonymous"; im.referrerPolicy = "no-referrer"; im.onload = () => { try { const x = tex.userData.c.getContext("2d"); x.fillStyle = css(c1); x.fillRect(30, 40, 400, 432); x.drawImage(im, 40, 56, 400, 400); tex.needsUpdate = true; } catch (e) {} }; im.src = T.lg; }
  part(t0, len, (u) => { ban.visible = u < len - 0.2; ban.position.y = lerp(60, 21, back(u / 0.9)) + Math.sin(u * 1.3) * 0.25 - (1 - cl((len - u) * 2.5)) * 40; ban.rotation.x = Math.sin(u * 1.1) * 0.03; if (st.cam) ban.lookAt(st.cam.position.x * 0.3, 21, st.cam.position.z);
    if (u > 0.9 && !ban.userData.hit) { ban.userData.hit = true; st.flash = 0.9; st.fc = c1; st.wave = 1.3; burst([0, 21, -17], c1, 260, 40); burst([0, 21, -17], c2, 160, 34); }
    if (u > 0.9 && R() < 0.1) fwk([(R() - 0.5) * 150, top + 12 + R() * 30, (R() - 0.5) * 90], R() < 0.5 ? c1 : c2, 140); if (u > 0.9) { everyone(1); st.burst = Math.max(st.burst, 0.55 + 0.45 * Math.max(0, Math.sin(u * 5))); } }, () => { ban.visible = false; });
  cam(t0 - 0.2, [0, 9, 46], [0, 17, -16], 52, 1200);
  // and what the team does when it scores
  const P0 = t0 + 1.1, PL = len - 1.2;
  if (fx.startsWith("fall:")) { const kind = fx.slice(5), geo = fallGeo(K, U, kind), NC = kind === "towel" ? 260 : 200, mat = kind === "towel" ? new THREE.MeshBasicMaterial({ color: C([1, 0.78, 0.1]), side: THREE.DoubleSide }) : new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: kind === "nugget" || kind === "star" ? 120 : 40, specular: C([0.9, 0.9, 0.9]), side: THREE.DoubleSide });
    const fm = add(new THREE.InstancedMesh(geo, mat, NC)); fm.frustumCulled = false; const pal = kind === "nugget" ? [[1, 0.76, 0.2], [0.95, 0.66, 0.12]] : kind === "cheese" ? [[1, 0.8, 0.18], [1, 0.72, 0.1]] : kind === "bone" ? [[0.96, 0.94, 0.88], [0.9, 0.88, 0.82]] : kind === "towel" ? [[1, 1, 1]] : [lift(c1, 0.3), lift(c2, 0.3)];
    for (let i = 0; i < NC; i++) fm.setColorAt(i, C(pal[i % pal.length])); if (fm.instanceColor) fm.instanceColor.needsUpdate = true;
    const cs = Array.from({ length: NC }, () => ({ p: [(R() - 0.5) * 112, top * 0.6 + R() * 60, (R() - 0.5) * 56], v: [(R() - 0.5) * 4, -6 - R() * 8, (R() - 0.5) * 4], r: [R() * 6, R() * 6, R() * 6], w: [(R() - 0.5) * 6, (R() - 0.5) * 6, (R() - 0.5) * 6], s: 0.8 + R() * 0.7, t0: R() * 1.8, b: 0 }));
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(), s3 = new THREE.Vector3(), soft = kind === "towel";
    part(P0, PL, (u, dt) => { for (let i = 0; i < NC; i++) { const c = cs[i]; let sc = 0; if (u > c.t0) { if (soft) { c.p[1] -= (4 + Math.sin(u * 3 + i) * 1.5) * dt; c.p[0] += Math.sin(u * 2.3 + i) * 3 * dt; } else c.v[1] -= 18 * dt; if (!soft) for (let a = 0; a < 3; a++) c.p[a] += c.v[a] * dt; for (let a = 0; a < 3; a++) c.r[a] += c.w[a] * dt;
          if (c.p[1] < 0.4) { if (!soft && c.v[1] < 0 && c.b < 2) { c.v[1] *= -0.3; c.b++; c.p[1] = 0.4; } else { c.p[1] = 0.4; c.v = [0, 0, 0]; c.w = [0, 0, 0]; c.r[0] = -Math.PI / 2; } } sc = c.s * cl((PL - 0.3 - u) * 2.5) * (kind === "nugget" ? 1 : 1.25); }
        e.set(...c.r); q.setFromEuler(e); m4.compose(p3.set(...c.p), q, s3.setScalar(sc)); fm.setMatrixAt(i, m4); } fm.instanceMatrix.needsUpdate = true; }, () => { fm.visible = false; }); }
  else if (fx === "birds") { const birds = Array.from({ length: 7 }, (_, i) => { const b = birdOf(K, H, i % 3 ? c1 : lift(c1, 0.3), c2); add(b.g); b.g.scale.setScalar(1.4 + (i % 3) * 0.35); b.g.visible = false; b.i = i; return b; });
    part(P0, PL, (u) => { for (const b of birds) { const a = u * 0.75 + b.i * 0.9, rx = 54 + (b.i % 3) * 14, rz = 34 + (b.i % 2) * 10, x = Math.cos(a) * rx, z = Math.sin(a) * rz, y = top * 0.55 + 8 + Math.sin(u * 1.3 + b.i) * 5 + (b.i % 3) * 4; b.g.visible = u < PL - 0.2; b.g.position.set(x, y, z); b.g.rotation.y = Math.atan2(-(Math.cos(a) * rz), -Math.sin(a) * rx); b.g.rotation.z = Math.sin(u * 1.3 + b.i) * 0.15;
        for (const w of b.wings) w.rotation.x = w.userData.s * Math.sin(u * 9 + b.i) * 0.65; if (R() < 0.15) spark([x, y, z], [0, -2, 0], c1, 0.8); } }, () => { for (const b of birds) b.g.visible = false; }); cam(P0 + 0.6, [0, 6, 30], [0, 32, -10], 64, 2000); }
  else if (fx === "dolphins") { const ds = Array.from({ length: 6 }, (_, i) => { const d = whaleOf(K, H, [0, 0.56, 0.59], [0.9, 0.95, 0.95], true); add(d.g); d.g.scale.setScalar(1.6); d.g.visible = false; d.i = i; return d; });
    part(P0, PL, (u) => { for (const d of ds) { const k = ((u - d.i * 0.45) / 1.6) % 1, on = u > d.i * 0.45; d.g.visible = on && u < PL - 0.2; if (!on) continue; const x = -40 + d.i * 16, z = lerp(-24, 24, k), y = -3 + 64 * k * (1 - k); d.g.position.set(x, y, z); d.g.rotation.set(0, -Math.PI / 2, Math.atan2(64 * (1 - 2 * k), 48)); d.tail.rotation.z = Math.sin(u * 9) * 0.4; if (Math.abs(y) < 0.6) for (let q = 0; q < 12; q++) spark([x, 0.5, z], [(R() - 0.5) * 6, 8 + R() * 10, (R() - 0.5) * 6], R() < 0.5 ? [0.6, 0.85, 1] : WHITE, 1, 24); } }, () => { for (const d of ds) d.g.visible = false; }); cam(P0 + 0.6, [-60, 10, 44], [-10, 6, 0], 54, 2000); }
  else if (fx === "cannons") { const cn = [-1, 1].map((s) => { const g = add(new THREE.Group()), b = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.8, 8, 16), lit([0.12, 0.12, 0.14], 90)); b.rotation.z = s * 0.95; b.position.set(-s * 2, 3.4, 0); g.add(b); for (const z of [-2, 2]) { const w = new THREE.Mesh(new THREE.CylinderGeometry(2.1, 2.1, 0.6, 18), lit([0.35, 0.2, 0.1], 30)); w.rotation.x = Math.PI / 2; w.position.set(0, 2.1, z); g.add(w); } g.position.set(s * 58, 0, 6); g.visible = false; return { g, s }; });
    let last = -1; part(P0, PL, (u) => { for (const c of cn) c.g.visible = u < PL - 0.2; const n = Math.floor(u / 0.7); if (n !== last && u < PL - 0.6) { last = n; const c = cn[n % 2], mx = c.s * 54, my = 6.5; for (let i = 0; i < 90; i++) spark([mx, my, 6], [-c.s * (8 + R() * 18), 4 + R() * 12, (R() - 0.5) * 10], R() < 0.5 ? [0.7, 0.7, 0.72] : [1, 0.75, 0.3], 1 + R(), -1); st.flash = Math.max(st.flash, 0.7); st.fc = [1, 0.8, 0.5]; burst([-c.s * 40, top + 10 + R() * 20, (R() - 0.5) * 60], R() < 0.5 ? c1 : c2, 140, 30); st.burst = 0.8; }
      for (const c of cn) c.g.position.x = c.s * 58 + (u % 0.7 < 0.1 ? c.s * 0.8 : 0); }, () => { for (const c of cn) c.g.visible = false; }); cam(P0 + 0.6, [40, 6, 34], [58, 4, 6], 54, 1600); }
  else if (fx === "horn" || fx === "roar") { const rings = []; let last = -1; part(P0, PL, (u) => { const n = Math.floor(u / (fx === "horn" ? 1.1 : 0.8)); if (n !== last && u < PL - 0.5) { last = n; const m = add(new THREE.Mesh(new THREE.TorusGeometry(1, 0.18, 6, 64), addv(n % 2 ? c2 : lift(c1, 0.4), 0.9))); m.position.set(0, 12, -10); m.userData.t = u; rings.push(m); st.burst = 1; st.wave = 1.2; st.flash = Math.max(st.flash, 0.5); st.fc = c1; }
      for (const m of rings) { const k = (u - m.userData.t) / 1.6; m.scale.setScalar(2 + k * 70); m.material.opacity = 0.8 * Math.max(0, 1 - k); m.visible = k < 1; if (st.cam) m.lookAt(st.cam.position); } everyone(1); }, () => { for (const m of rings) m.visible = false; }); }
  else if (fx === "claws") { const cls = [0, 1, 2].map((i) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(1, 3.2), addv(i % 2 ? [0.05, 0.05, 0.05] : lift(c1, 0.3), 0))); m.rotation.x = -Math.PI / 2; m.rotation.z = 0.55; m.position.set((i - 1) * 9, 0.3, 4); return m; });
    part(P0, PL, (u) => { cls.forEach((m, i) => { const k = ease((u - 0.3 - i * 0.18) / 0.35); m.scale.set(Math.max(0.01, k * 90), 1, 1); m.material.opacity = 0.75 * cl(k * 3) * cl((PL - 0.3 - u) * 2); if (k > 0.98 && !m.userData.hit) { m.userData.hit = true; st.flash = 0.7; st.fc = c1; burst([m.position.x, 1, 4], c1, 120, 30); } }); everyone(1); }, () => { for (const m of cls) m.visible = false; }); cam(P0 + 0.2, [0, 70, 30], [0, 0, 2], 50, 1400); }
  else if (fx === "jets") { const jets = [-1.5, -0.5, 0.5, 1.5].map((k) => { const j = add(new THREE.Group()), f = new THREE.Mesh(new THREE.ConeGeometry(1.6, 13, 8), lit([0.85, 0.86, 0.9], 90)); f.rotation.z = -Math.PI / 2; j.add(f); const w = new THREE.Mesh(new THREE.BoxGeometry(4, 0.3, 11), lit(c1, 60)); w.position.x = -2; j.add(w); j.scale.setScalar(2); j.userData.k = k; j.visible = false; return j; });
    part(P0, PL, (u) => { for (const j of jets) { const q = (u - 0.3 - Math.abs(j.userData.k) * 0.15) / 3.2, x = lerp(-300, 300, q); j.visible = q > 0 && q < 1; j.position.set(x, top + 14, j.userData.k * 22); if (j.visible) for (let i = 0; i < 4; i++) spark([x - 16 - i * 5, j.position.y, j.position.z], [0, -1.5, 0], j.userData.k > 0 ? c1 : WHITE, 2.6, 0.4); } }, () => { for (const j of jets) j.visible = false; }); }
  else { const NC = 700, conf = add(new THREE.InstancedMesh(new THREE.PlaneGeometry(0.9, 0.5), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide }), NC)); conf.frustumCulled = false; const pal = [lift(c1, 0.3), lift(c2, 0.3), WHITE];
    const cs = Array.from({ length: NC }, (_, i) => { conf.setColorAt(i, C(pal[i % 3])); return { p: [(R() - 0.5) * 120, 10 + R() * (top + 30), (R() - 0.5) * 60], r: [R() * 6, R() * 6, R() * 6], w: [(R() - 0.5) * 9, (R() - 0.5) * 9, (R() - 0.5) * 9], f: 3 + R() * 4, ph: R() * 6 }; }); if (conf.instanceColor) conf.instanceColor.needsUpdate = true;
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(), s3 = new THREE.Vector3();
    part(P0, PL, (u, dt) => { const sc = cl(u * 3) * cl((PL - 0.3 - u) * 2) * 1.5; for (let i = 0; i < NC; i++) { const c = cs[i]; c.p[1] -= c.f * dt; c.p[0] += Math.sin(u * 2 + c.ph) * 2 * dt; if (c.p[1] < 0.3) c.p[1] = top + 20; for (let a = 0; a < 3; a++) c.r[a] += c.w[a] * dt; e.set(...c.r); q.setFromEuler(e); m4.compose(p3.set(...c.p), q, s3.setScalar(sc)); conf.setMatrixAt(i, m4); } conf.instanceMatrix.needsUpdate = true; }, () => { conf.visible = false; }); }
  return true;
}

// ================= the biggest: the whole building goes =================
export function finale(t0, len, K, H) {
  const { THREE, st, o, top, add, addv, C, spark, burst, ringOn, beamUp } = K, { part, word, cam, R, everyone, fwk } = H, U = kit3(K), col = o.col, GOLD = K.GOLD, WHITE = [1, 1, 1], tc = o.team ? o.team.col : col;
  // a money tornado at the fifty, fireworks walking the rim, searchlights, the crowd twice round
  const bill = U.canvasTex(256, 112, (x, w, h) => { x.fillStyle = "#cfe8c9"; x.fillRect(0, 0, w, h); x.strokeStyle = "#2f6a3a"; x.lineWidth = 6; x.strokeRect(5, 5, w - 10, h - 10); x.fillStyle = "#2f6a3a"; x.beginPath(); x.ellipse(w / 2, h / 2, 30, 38, 0, 0, 7); x.fill(); x.font = "900 40px Arial"; x.textBaseline = "middle"; x.fillText("100", 16, 32); x.textAlign = "right"; x.fillText("100", w - 16, h - 30); });
  const NB = 320, bm = add(new THREE.InstancedMesh(new THREE.PlaneGeometry(2.6, 1.14), new THREE.MeshBasicMaterial({ map: bill, side: THREE.DoubleSide }), NB)); bm.userData.tx = bill; bm.frustumCulled = false;
  const bs = Array.from({ length: NB }, () => ({ a: R() * 6.28, h: R() * 46, sp: 2 + R() * 2.5, r0: 3 + R() * 4, ph: R() * 6 }));
  const lights = [0, 1, 2, 3, 4, 5].map((i) => { const g = new THREE.ConeGeometry(11, 180, 18, 1, true); g.translate(0, 90, 0); const m = add(new THREE.Mesh(g, addv(i % 2 ? GOLD : tc, 0))); m.position.set([-55, 55, -55, 55, 0, 0][i], 0, [-24, -24, 24, 24, -30, 30][i]); m.userData.i = i; return m; });
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(), s3 = new THREE.Vector3(); let fwAt = -1, rimA = 0;
  part(t0, len, (u, dt) => { const out = cl((len - 0.4 - u) * 2), spin = ease(u / 1.2);
    for (let i = 0; i < NB; i++) { const b = bs[i], h = (b.h + u * b.sp * 6) % 48, r = (b.r0 + h * 0.42) * spin, a = b.a + u * (2.2 + 18 / (4 + h)); e.set(u * 3 + b.ph, a, u * 2 + b.ph); q.setFromEuler(e); m4.compose(p3.set(Math.cos(a) * r, h + 0.5, 6 + Math.sin(a) * r), q, s3.setScalar(out * spin)); bm.setMatrixAt(i, m4); } bm.instanceMatrix.needsUpdate = true;
    for (const m of lights) { const i = m.userData.i; m.material.opacity = 0.075 * cl(u * 2) * out; m.rotation.z = Math.sin(u * 1.3 + i * 1.3) * 0.5; m.rotation.x = Math.cos(u * 1.1 + i * 2.1) * 0.45; }
    if (u - fwAt > 0.16 && u < len - 0.8) { fwAt = u; rimA += 0.55; const p = [Math.cos(rimA) * 92, top + 6 + R() * 22, Math.sin(rimA) * 64]; fwk(p, [GOLD, tc, WHITE, col][Math.floor(R() * 4)], 110); }
    if (Math.floor(u / 2.2) !== Math.floor((u - dt) / 2.2)) { st.wave = 1.6; st.burst = 1; } st.cheer = 1; everyone(1); }, () => { bm.visible = false; for (const m of lights) m.visible = false; });
  ringOn(GOLD, 120); st.flash = 1.4; st.fc = GOLD; beamUp(GOLD, 0, 6, 2.4, 200);
  const big = (o.keys || []).some((k) => k === "nuke" || k === "whale" || k === "botd");
  word(big ? "Whale hit" : "Monster hit", t0 + 0.4, len - 0.6, 34, 6, 52, "#ffd66b"); cam(t0 - 0.2, [0, 4, 34], [0, 22, 6], 64, 1400); cam(t0 + 2.6, [0, 60, 90], [0, 14, 0], 52, 2600); return true;
}

// ================= a spread or a total, with the arithmetic =================
export function scoreboard(t0, len, K, H) {
  const { THREE, st, o, add, C, burst, ringOn, beamUp } = K, { part, cam, R, everyone, lit } = H, U = kit3(K), g = o.game; if (!g) return false;
  const A = g.a, Hm = g.h, tot = (A.sc || 0) + (Hm.sc || 0), side = g.s === "a" ? A : g.s === "h" ? Hm : null, line = Number(g.l) || 0;
  const mineBy = side ? side.sc - (side === A ? Hm.sc : A.sc) : 0, math = g.m === "tot" ? `TOTAL ${tot} · ${g.s === "u" ? "UNDER" : "OVER"} ${line} · BY ${Math.round(Math.abs(tot - line) * 10) / 10}` : side ? `${side.ab} ${line > 0 ? "+" : ""}${line} · ${mineBy >= 0 ? "WON BY " + mineBy : "LOST BY " + -mineBy} · COVERED BY ${Math.round(Math.abs(mineBy + line) * 10) / 10}` : "";
  let shown = [-1, -1]; const tex = U.canvasTex(2048, 900, () => {});
  const draw = (sa, sh) => { if (sa === shown[0] && sh === shown[1]) return; shown = [sa, sh]; const x = tex.userData.c.getContext("2d"), w = 2048, h = 900; x.fillStyle = "#07090e"; x.fillRect(0, 0, w, h); x.fillStyle = css(A.col); x.fillRect(0, 0, w / 2 - 6, 520); x.fillStyle = css(Hm.col); x.fillRect(w / 2 + 6, 0, w / 2, 520);
    x.fillStyle = "rgba(0,0,0,.28)"; x.fillRect(0, 380, w, 140); x.fillStyle = "#fff"; x.textBaseline = "middle"; x.textAlign = "center"; x.font = "900 150px 'Big Shoulders Display', 'Barlow Condensed', Arial"; x.fillText(A.ab, w / 4, 120); x.fillText(Hm.ab, (3 * w) / 4, 120);
    x.font = "900 300px 'Big Shoulders Display', 'Barlow Condensed', Arial"; x.fillText(String(sa), w / 4, 300); x.fillText(String(sh), (3 * w) / 4, 300); x.font = "800 74px 'Barlow Condensed', Arial"; x.fillText("FINAL", w / 2, 450);
    x.fillStyle = "#36e08a"; x.font = "900 120px 'Big Shoulders Display', 'Barlow Condensed', Arial"; let fs = 120; while (x.measureText(math).width > w - 80 && fs > 50) { fs -= 6; x.font = `900 ${fs}px 'Big Shoulders Display', 'Barlow Condensed', Arial`; } x.fillText(math, w / 2, 700); tex.needsUpdate = true; };
  const sbG = add(new THREE.Group()), frame = new THREE.Mesh(new THREE.BoxGeometry(36, 16.6, 1.4), lit([0.1, 0.11, 0.14], 60)), face = U.texMesh(new THREE.PlaneGeometry(34.6, 15.2), tex, { transparent: false }); face.position.z = 0.72; sbG.add(frame, face);
  for (const x of [-12, 12]) { const leg = new THREE.Mesh(new THREE.BoxGeometry(1.2, 12, 1.2), lit([0.2, 0.21, 0.25], 60)); leg.position.set(x, -14, 0); sbG.add(leg); }
  part(t0, len, (u) => { sbG.visible = u < len - 0.2; sbG.position.set(0, lerp(-14, 14, back(u / 0.8)) - (1 - cl((len - u) * 2.5)) * 30, -4); const k = ease((u - 0.8) / 1.6); draw(Math.round((A.sc || 0) * k), Math.round((Hm.sc || 0) * k));
    if (k >= 1 && !sbG.userData.hit) { sbG.userData.hit = true; st.flash = 1; st.fc = [0.2, 0.9, 0.55]; st.wave = 1.3; burst([0, 10, -2], [0.2, 0.9, 0.55], 320, 44); ringOn([0.2, 0.9, 0.55], 60).position.set(0, 0.2, 2); for (const x of [-18, 18]) beamUp([0.2, 0.9, 0.55], x, -4, 0.8, 120); } everyone(k >= 1 ? 1 : 0.4); }, () => { sbG.visible = false; });
  cam(t0 - 0.2, [0, 12, 36], [0, 13, -4], 50, 1100); cam(t0 + 2.8, [-14, 9, 30], [0, 13, -4], 50, 2000); return true;
}
