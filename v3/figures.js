// The people in the building: football players with helmets, facemasks, pads, numbers and real stances, and the home
// side's mascot. Every figure is the same jointed skeleton (hips, chest, head, shoulders, elbows, thighs, knees), each
// bone one merged, vertex-coloured mesh, lit by the two lights this adds to the scene.
const cl = (v) => Math.max(0, Math.min(1, v)), lerp = (a, b, t) => a + (b - a) * t;

export function makeFigures(THREE) {
  const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), V1 = new THREE.Vector3(), V2 = new THREE.Vector3();
  // one part of a bone: a shape, a colour, where it sits
  const part = (g, c, p = [0, 0, 0], r = [0, 0, 0], s = [1, 1, 1]) => ({ g, c, p, r, s });
  const merge = (parts) => {
    const P = [], N = [], C = [];
    for (const q of parts) { const g = q.g.index ? q.g.toNonIndexed() : q.g.clone(); E.set(q.r[0], q.r[1], q.r[2]); Q.setFromEuler(E); M4.compose(V1.set(q.p[0], q.p[1], q.p[2]), Q, V2.set(q.s[0], q.s[1], q.s[2])); g.applyMatrix4(M4); g.computeVertexNormals();
      const a = g.attributes.position.array, n = g.attributes.normal.array; for (let i = 0; i < a.length; i++) { P.push(a[i]); N.push(n[i]); } for (let i = 0; i < a.length; i += 3) C.push(q.c[0], q.c[1], q.c[2]); g.dispose(); q.g.dispose(); }
    const o = new THREE.BufferGeometry(); o.setAttribute("position", new THREE.Float32BufferAttribute(P, 3)); o.setAttribute("normal", new THREE.Float32BufferAttribute(N, 3)); o.setAttribute("color", new THREE.Float32BufferAttribute(C, 3)); return o;
  };
  const sph = (r, w = 14, h = 10) => new THREE.SphereGeometry(r, w, h), cap = (r, l, n = 10) => new THREE.CapsuleGeometry(r, l, 4, n), cyl = (a, b, h, n = 12) => new THREE.CylinderGeometry(a, b, h, n), box = (x, y, z) => new THREE.BoxGeometry(x, y, z), cone = (r, h, n = 10) => new THREE.ConeGeometry(r, h, n), tor = (R, r, arc, n = 14) => new THREE.TorusGeometry(R, r, 5, n, arc);
  const matBody = new THREE.MeshLambertMaterial({ vertexColors: true }), matShine = new THREE.MeshPhongMaterial({ vertexColors: true, shininess: 70, specular: new THREE.Color(0.35, 0.35, 0.35) });
  const SKINS = [[0.36, 0.22, 0.14], [0.62, 0.42, 0.28], [0.25, 0.15, 0.1], [0.78, 0.58, 0.44], [0.45, 0.29, 0.19]];
  const WHITE = [0.93, 0.93, 0.95], DARK = [0.05, 0.05, 0.06], GREY = [0.55, 0.57, 0.62];

  // the skeleton: D holds the lengths; geo the six bone meshes (arms and legs are mirrored)
  function rig(geo, D, mats) {
    const g = new THREE.Group(), hips = new THREE.Group(), chest = new THREE.Group(), head = new THREE.Group(); g.add(hips); hips.add(chest); chest.add(head); head.position.y = D.neck;
    const mk = (ge, m) => { const o = new THREE.Mesh(ge, m || mats[0]); o.frustumCulled = false; return o; };
    hips.add(mk(geo.pelvis)); chest.add(mk(geo.chest)); head.add(mk(geo.head, mats[1]));
    const j = { hips, chest, head };
    for (const [k, sx] of [["L", -1], ["R", 1]]) {
      const sh = new THREE.Group(), el = new THREE.Group(), th = new THREE.Group(), kn = new THREE.Group();
      sh.position.set(sx * D.shW, D.shY, 0); el.position.y = -D.uarm; chest.add(sh); sh.add(el); sh.add(mk(geo.uarm)); el.add(mk(geo.farm));
      th.position.set(sx * D.hipW, 0, 0); kn.position.y = -D.thigh; hips.add(th); th.add(kn); th.add(mk(geo.thigh)); kn.add(mk(geo.shin, geo.shoe ? mats[1] : mats[0]));
      j["s" + k] = sh; j["e" + k] = el; j["t" + k] = th; j["k" + k] = kn;
    }
    return { g, j, D };
  }
  // stand it: every angle in one go. a = { lean, twist, head, th:[l,r], kn:[l,r], sh:[l,r], shz:[l,r], el:[l,r], drop }
  function apply(f, a) {
    const j = f.j, D = f.D, reach = (i) => D.thigh * Math.cos(a.th[i]) + D.shin * Math.cos(a.th[i] + a.kn[i]) + D.foot;
    j.hips.position.y = Math.max(reach(0), reach(1)) - (a.drop || 0); j.hips.rotation.set(0, a.twist || 0, a.roll || 0); j.chest.rotation.set(a.lean || 0, (a.twist || 0) * -0.6, 0); j.head.rotation.set(a.head || 0, a.look || 0, 0);
    j.tL.rotation.x = a.th[0]; j.tR.rotation.x = a.th[1]; j.kL.rotation.x = a.kn[0]; j.kR.rotation.x = a.kn[1];
    j.sL.rotation.set(a.sh[0], 0, -(a.shz ? a.shz[0] : 0.1)); j.sR.rotation.set(a.sh[1], 0, a.shz ? a.shz[1] : 0.1); j.eL.rotation.x = a.el[0]; j.eR.rotation.x = a.el[1];
  }
  const STANCE = {
    line: { lean: 1.02, head: -0.75, th: [-1.2, -0.95], kn: [1.55, 1.35], sh: [-1.05, -0.45], el: [-0.05, -1.25] },      // a hand in the dirt
    dline: { lean: 0.95, head: -0.7, th: [-1.05, -1.25], kn: [1.4, 1.6], sh: [-0.5, -1.0], el: [-1.2, -0.05] },
    qb: { lean: 0.42, head: -0.3, th: [-0.62, -0.62], kn: [0.95, 0.95], sh: [-0.75, -0.75], el: [-0.75, -0.75], shz: [-0.25, -0.25] },   // under centre
    rb: { lean: 0.5, head: -0.38, th: [-0.7, -0.7], kn: [1.05, 1.05], sh: [-0.35, -0.35], el: [-1.15, -1.15] },          // hands on the knees
    wr: { lean: 0.3, head: -0.2, th: [-0.55, 0.1], kn: [0.75, 0.3], sh: [0.25, -0.4], el: [-1.0, -1.1] },                 // staggered
    lb: { lean: 0.45, head: -0.32, th: [-0.6, -0.6], kn: [0.9, 0.9], sh: [-0.3, -0.3], el: [-1.3, -1.3], shz: [0.3, 0.3] },
    db: { lean: 0.32, head: -0.22, th: [-0.45, -0.3], kn: [0.7, 0.55], sh: [-0.15, -0.15], el: [-1.2, -1.2], shz: [0.25, 0.25] },
    stand: { lean: 0.03, head: 0, th: [0.03, -0.03], kn: [0.04, 0.04], sh: [0.05, -0.05], el: [-0.2, -0.2] },
    hips: { lean: 0.02, head: 0, th: [0.02, -0.02], kn: [0.03, 0.03], sh: [0.15, 0.15], el: [-1.5, -1.5], shz: [0.75, 0.75] },   // hands on the hips
    down: { lean: 1.42, head: -0.35, th: [-1.45, -1.2], kn: [1.6, 1.25], sh: [-2.3, -1.9], el: [-0.5, -0.7], drop: 0.34 },                                // on the turf, under the pile
    ref: { lean: 0.04, head: 0, th: [0.03, -0.03], kn: [0.04, 0.04], sh: [0.2, 0.2], el: [-0.5, -0.5], shz: [0.05, 0.05] },
  };
  const A = {}, mixA = (o, a, b, k) => { o.lean = lerp(a.lean || 0, b.lean || 0, k); o.head = lerp(a.head || 0, b.head || 0, k); o.twist = lerp(a.twist || 0, b.twist || 0, k); o.roll = lerp(a.roll || 0, b.roll || 0, k); o.look = lerp(a.look || 0, b.look || 0, k); o.drop = lerp(a.drop || 0, b.drop || 0, k);
    for (const key of ["th", "kn", "sh", "el"]) o[key] = [lerp(a[key][0], b[key][0], k), lerp(a[key][1], b[key][1], k)]; const za = a.shz || [0.1, 0.1], zb = b.shz || [0.1, 0.1]; o.shz = [lerp(za[0], zb[0], k), lerp(za[1], zb[1], k)]; return o; };
  // moving: a run (ph is the stride), a jump with the arms up, a dance
  const runA = (ph, hard = 1) => { const s = Math.sin(ph), c = Math.cos(ph); return { lean: 0.3 * hard, head: -0.2 * hard, twist: s * 0.18, th: [-0.3 - s * 0.95, -0.3 + s * 0.95], kn: [0.45 + Math.max(0, c) * 1.25, 0.45 + Math.max(0, -c) * 1.25], sh: [s * 1.0, -s * 1.0], el: [-1.4, -1.4], shz: [0.12, 0.12] }; };
  const cheerA = (t, seed = 0) => { const b = Math.abs(Math.sin(t * 5.2 + seed)); return { lean: -0.08, head: -0.25, th: [-0.25 * (1 - b), -0.25 * (1 - b)], kn: [0.5 * (1 - b), 0.5 * (1 - b)], sh: [-2.75 + Math.sin(t * 10 + seed) * 0.2, -2.75 - Math.sin(t * 10 + seed) * 0.2], el: [-0.25, -0.25], shz: [0.35, 0.35], hop: b * 0.38 }; };
  const danceA = (t) => { const s = Math.sin(t * 6.4), b = Math.abs(Math.sin(t * 6.4)); return { lean: 0.05, head: s * 0.12, look: s * 0.3, twist: s * 0.5, roll: s * 0.1, th: [-0.3 - s * 0.3, -0.3 + s * 0.3], kn: [0.6, 0.6], sh: [-2.5 * (s > 0 ? 1 : 0.25), -2.5 * (s > 0 ? 0.25 : 1)], el: [-0.9, -0.9], shz: [0.3, 0.3], hop: b * 0.22 }; };

  // a figure as it stands now, as one mesh drawn n times (the benches, the photographers)
  function freeze(f, n) { const sc = f.g.scale.x; f.g.scale.setScalar(1); f.g.position.set(0, 0, 0); f.g.rotation.set(0, 0, 0); f.g.updateMatrixWorld(true); const P = [], N = [], C = [];
    f.g.traverse((o) => { if (!o.isMesh || !o.geometry.attributes.color) return; const g = o.geometry.clone(); g.applyMatrix4(o.matrixWorld); for (const [arr, k] of [[P, "position"], [N, "normal"], [C, "color"]]) { const a = g.attributes[k].array; for (let q = 0; q < a.length; q++) arr.push(a[q]); } g.dispose(); });
    const o = new THREE.BufferGeometry(); o.setAttribute("position", new THREE.Float32BufferAttribute(P, 3)); o.setAttribute("normal", new THREE.Float32BufferAttribute(N, 3)); o.setAttribute("color", new THREE.Float32BufferAttribute(C, 3)); o.computeVertexNormals(); f.g.scale.setScalar(sc);
    const m = new THREE.InstancedMesh(o, matBody, n); m.frustumCulled = false; return m; }
  // ---- everyone else in the building: a cheerleader, a coach, a camera operator, the chain crew ----
  // o: { top, bottom, skin, hair, alt, kind: "cheer" | "coach" | "cam" | "crew" }
  function person(o) {
    const SK = o.skin || SKINS[3], TP = o.top, BT = o.bottom || DARK, HR = o.hair || [0.12, 0.08, 0.05], AL = o.alt || WHITE, k = o.kind || "crew", cheer = k === "cheer";
    const head = [part(sph(0.15, 16, 12), SK, [0, 0.14, 0]), part(sph(0.158, 14, 10), HR, [0, 0.175, -0.03], [0, 0, 0], [1, 0.92, 0.98]), part(sph(0.02, 6, 5), DARK, [-0.055, 0.15, 0.14]), part(sph(0.02, 6, 5), DARK, [0.055, 0.15, 0.14])];
    if (cheer) head.push(part(cap(0.05, 0.22), HR, [0, 0.12, -0.19], [0.5, 0, 0]), part(sph(0.05, 8, 6), AL, [0, 0.27, -0.12]));
    if (k === "coach" || k === "cam") head.push(part(sph(0.162, 14, 8), TP, [0, 0.2, 0], [0, 0, 0], [1, 0.7, 1]), part(box(0.2, 0.025, 0.14), TP, [0, 0.21, 0.19]));
    if (k === "coach") head.push(part(tor(0.165, 0.014, Math.PI, 12), DARK, [0, 0.14, 0], [0, 0, 0]), part(box(0.05, 0.09, 0.07), DARK, [-0.165, 0.12, 0]), part(box(0.012, 0.012, 0.14), DARK, [-0.15, 0.06, 0.08]));
    const chest = [part(cyl(0.2, cheer ? 0.13 : 0.165, 0.46, 14), TP, [0, 0.33, 0], [0, 0, 0], [1, 1, 0.66]), part(sph(0.085), TP, [-0.24, 0.55, 0]), part(sph(0.085), TP, [0.24, 0.55, 0]), part(cyl(0.055, 0.065, 0.1, 8), SK, [0, 0.66, 0])];
    if (cheer) chest.push(part(box(0.34, 0.07, 0.01), AL, [0, 0.4, 0.125]));
    if (k === "crew") chest.push(part(box(0.3, 0.05, 0.01), [0.9, 0.9, 0.2], [0, 0.36, 0.13]), part(box(0.3, 0.05, 0.01), [0.9, 0.9, 0.2], [0, 0.24, 0.125]));
    if (k === "cam") chest.push(part(box(0.2, 0.22, 0.5), DARK, [0.27, 0.72, 0.12]), part(cyl(0.085, 0.1, 0.2, 12), [0.16, 0.17, 0.2], [0.27, 0.72, 0.46], [Math.PI / 2, 0, 0]), part(sph(0.07, 10, 8), [0.2, 0.5, 0.9], [0.27, 0.72, 0.55]), part(box(0.05, 0.05, 0.05), [1, 0.1, 0.1], [0.27, 0.86, 0.3]));
    const geo = {
      pelvis: merge(cheer ? [part(cyl(0.15, 0.3, 0.26, 14), BT, [0, -0.06, 0], [0, 0, 0], [1, 1, 0.8]), part(cyl(0.3, 0.31, 0.04, 14), AL, [0, -0.2, 0], [0, 0, 0], [1, 1, 0.8])] : [part(sph(0.17), BT, [0, 0, 0], [0, 0, 0], [1.05, 0.8, 0.86])]),
      chest: merge(chest), head: merge(head),
      uarm: merge([part(cap(0.055, 0.17), cheer ? SK : TP, [0, -0.13, 0])]),
      farm: merge([part(cap(0.045, 0.17), SK, [0, -0.13, 0]), part(sph(0.055, 8, 6), SK, [0, -0.3, 0]), ...(cheer ? [part(sph(0.2, 10, 8), AL, [0, -0.36, 0]), part(sph(0.15, 8, 6), TP, [0.08, -0.42, 0.06]), part(sph(0.15, 8, 6), TP, [-0.07, -0.3, -0.08])] : [])]),
      thigh: merge([part(cap(cheer ? 0.075 : 0.09, 0.27), cheer ? SK : BT, [0, -0.22, 0])]),
      shin: merge([part(cap(0.06, 0.26), cheer ? SK : BT, [0, -0.2, 0]), part(box(0.1, 0.08, 0.25), cheer ? WHITE : DARK, [0, -0.44, 0.05])]),
    };
    const f = rig(geo, PD, [matBody, matBody]); f.g.scale.setScalar(o.scale || 1.28); f.seed = o.seed || 0; f.kind = k; f.dispose = () => { for (const q in geo) geo[q].dispose(); }; return f;
  }
  // one frame of one of them. act: cheer (the routine) | hype (arms up, jumping) | coach | cam | stand | kneel
  function posePerson(f, act, t, amp = 1) {
    let a, hop = 0; const s = f.seed;
    if (act === "cheer") { const c = (t * 0.5) % 4, b = Math.abs(Math.sin(t * 6.2));
      if (c < 1.2) { a = { lean: -0.05, head: -0.15, th: [0.04, -0.04], kn: [0.05, 0.05], sh: [-2.7 + Math.sin(t * 12.4) * 0.15, -2.7 - Math.sin(t * 12.4) * 0.15], el: [-0.1, -0.1], shz: [0.45, 0.45] }; hop = b * 0.1; }
      else if (c < 2.2) { const k = Math.sin(t * 6.2) > 0; a = { lean: 0, twist: k ? 0.35 : -0.35, th: [0.04, -0.04], kn: [0.1, 0.1], sh: [k ? -1.55 : 0.2, k ? 0.2 : -1.55], el: [k ? -0.05 : -1.9, k ? -1.9 : -0.05], shz: [0.2, 0.2] }; }
      else if (c < 2.9) { const k = Math.sin(((c - 2.2) / 0.7) * Math.PI); a = { lean: -0.12 * k, th: [-1.75 * k, 0.05], kn: [0.05, 0.1 * k], sh: [-1.5, -1.5], el: [-0.1, -0.1], shz: [1.3, 1.3] }; }
      else a = { lean: 0, roll: Math.sin(t * 3.1) * 0.08, th: [0.05, -0.05], kn: [0.04, 0.04], sh: [0.15, 0.15], el: [-1.5, -1.5], shz: [0.75, 0.75] }; }
    else if (act === "hype") { const c = cheerA(t, s); a = c; hop = c.hop; }
    else if (act === "coach") { const pt = Math.sin(t * 0.37 + s) > 0.82; a = pt ? { lean: 0.12, head: -0.1, th: [-0.1, 0.12], kn: [0.15, 0.1], sh: [-1.45, 0.1], el: [-0.1, -0.3], shz: [0.1, 0.1], look: 0.3 } : { lean: 0.04, look: Math.sin(t * 0.5 + s) * 0.4, th: [0.04, -0.04], kn: [0.04, 0.04], sh: [-0.55, -0.55], el: [-1.75, -1.75], shz: [-0.35, -0.35] }; }
    else if (act === "cam") a = { lean: 0.05, twist: Math.sin(t * 0.3 + s) * 0.25, th: [0.1, -0.12], kn: [0.08, 0.1], sh: [-0.4, -1.25], el: [-1.4, -1.75], shz: [0.1, 0.35] };
    else if (act === "kneel") a = { lean: 0.25, head: -0.2, th: [-1.5, 0.1], kn: [1.55, 1.55], sh: [-1.1, -1.2], el: [-1.5, -1.5], shz: [-0.1, 0.1], drop: 0.02 };
    else a = { lean: 0.03 + Math.sin(t * 1.6 + s) * 0.02, look: Math.sin(t * 0.45 + s) * 0.3, th: [0.03, -0.03], kn: [0.04, 0.04], sh: [0.05, -0.05], el: [-0.2, -0.2] };
    apply(f, mixA(A, a, a, 0)); f.g.position.y = hop * amp * f.g.scale.y;
  }
  // ---- a football player ----
  function playerGeo(K) {
    const J = K.jersey, P = K.pants, H = K.helm, AL = K.alt, SK = K.skin, SO = K.sock || J;
    return {
      pelvis: merge([part(sph(0.17), P, [0, 0.0, 0], [0, 0, 0], [1.05, 0.8, 0.86]), part(cyl(0.17, 0.165, 0.06), AL, [0, 0.11, 0], [0, 0, 0], [1, 1, 0.8])]),
      chest: merge([part(cyl(0.215, 0.165, 0.46, 14), J, [0, 0.33, 0], [0, 0, 0], [1, 1, 0.72]),
        part(sph(0.2, 16, 10), J, [0, 0.57, 0], [0, 0, 0], [1.72, 0.52, 0.98]),                                   // the pads
        part(sph(0.1), J, [-0.3, 0.56, 0], [0, 0, 0], [1.1, 0.75, 1.15]), part(sph(0.1), J, [0.3, 0.56, 0], [0, 0, 0], [1.1, 0.75, 1.15]),
        part(tor(0.085, 0.02, Math.PI * 2, 12), AL, [0, 0.655, 0], [Math.PI / 2, 0, 0]), part(cyl(0.06, 0.07, 0.1, 8), SK, [0, 0.68, 0])]),
      head: merge([part(sph(0.168, 18, 14), H, [0, 0.13, 0]), part(sph(0.12, 12, 10), SK, [0, 0.105, 0.055]),
        part(box(0.2, 0.07, 0.1), DARK, [0, 0.135, 0.115]),                                                        // the opening, in shadow
        part(tor(0.169, 0.016, Math.PI, 14), AL, [0, 0.13, 0], [0, Math.PI / 2, 0]),                               // the stripe, front to back
        part(tor(0.132, 0.011, Math.PI, 12), GREY, [0, 0.07, 0.07], [Math.PI / 2, 0, 0]), part(tor(0.132, 0.011, Math.PI, 12), GREY, [0, 0.025, 0.06], [Math.PI / 2, 0, 0]),
        part(box(0.014, 0.1, 0.014), GREY, [0, 0.05, 0.196]), part(box(0.014, 0.09, 0.014), GREY, [-0.07, 0.05, 0.178]), part(box(0.014, 0.09, 0.014), GREY, [0.07, 0.05, 0.178]),
        part(sph(0.03, 8, 6), AL, [-0.165, 0.11, 0.02]), part(sph(0.03, 8, 6), AL, [0.165, 0.11, 0.02])]),
      uarm: merge([part(cap(0.068, 0.17), J, [0, -0.13, 0]), part(tor(0.07, 0.012, Math.PI * 2, 10), AL, [0, -0.2, 0], [Math.PI / 2, 0, 0]), part(sph(0.058, 8, 6), SK, [0, -0.3, 0])]),
      farm: merge([part(cap(0.05, 0.17), SK, [0, -0.13, 0]), part(cyl(0.054, 0.05, 0.07, 8), WHITE, [0, -0.21, 0]), part(sph(0.062, 10, 8), K.glove || WHITE, [0, -0.3, 0], [0, 0, 0], [0.9, 1.15, 1])]),
      thigh: merge([part(cap(0.1, 0.27), P, [0, -0.22, 0]), part(sph(0.085, 8, 6), P, [0, -0.44, 0.02])]),
      shin: merge([part(cap(0.068, 0.26), SO, [0, -0.2, 0]), part(cyl(0.07, 0.066, 0.05, 8), AL, [0, -0.09, 0]), part(box(0.105, 0.08, 0.27), K.shoe || DARK, [0, -0.44, 0.06]), part(box(0.1, 0.02, 0.27), WHITE, [0, -0.485, 0.06])]),
    };
  }
  const PD = { neck: 0.7, shW: 0.3, shY: 0.56, uarm: 0.3, hipW: 0.11, thigh: 0.46, shin: 0.46, foot: 0.05 };
  const numTex = (n, fg, edge) => { const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d"); x.font = "900 104px 'Barlow Condensed', 'Arial Narrow', Arial, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.lineWidth = 12; x.strokeStyle = edge; x.strokeText(String(n), 64, 70); x.fillStyle = fg; x.fillText(String(n), 64, 70); const t = new THREE.CanvasTexture(c); t.anisotropy = 4; return t; };
  const css = (c) => `rgb(${c.map((v) => Math.round(cl(Math.sqrt(v)) * 255)).join(",")})`;
  // a kit: the colours of one side; player(n) makes one man of it
  function kit(K) {
    const geos = SKINS.map((sk) => playerGeo(Object.assign({}, K, { skin: sk }))), tex = [], lum = 0.3 * K.jersey[0] + 0.59 * K.jersey[1] + 0.11 * K.jersey[2], fg = lum > 0.5 ? "#101520" : "#f4f5f8", edge = css(K.alt);
    const numMat = (n) => { const t = numTex(n, fg, edge); tex.push(t); return new THREE.MeshBasicMaterial({ map: t, transparent: true, alphaTest: 0.2 }); };
    const pg = new THREE.PlaneGeometry(0.25, 0.25);
    return { K, geos, scale: K.scale || 1.36,
      player(n, i = 0) { const f = rig(geos[i % geos.length], PD, [matBody, matShine]); if (n != null) { const m = numMat(n), a = new THREE.Mesh(pg, m), b = new THREE.Mesh(pg, m); a.position.set(0, 0.34, 0.158); b.position.set(0, 0.36, -0.16); b.rotation.y = Math.PI; b.scale.setScalar(1.15); f.j.chest.add(a, b); } f.g.scale.setScalar(this.scale); f.seed = i * 1.7; return f; },
      // the bench: one standing man, drawn many times
      standing(n) { const f = rig(geos[0], PD, [matBody, matShine]); apply(f, mixA({}, STANCE.stand, STANCE.stand, 0)); return freeze(f, n); },
      dispose() { for (const g of geos) for (const k in g) g[k].dispose(); for (const t of tex) t.dispose(); pg.dispose(); } };
  }
  // one frame of a player: where he lines up (kind), how hard the play is moving (mv 0..1), whether the place is going off
  function posePlayer(f, kind, t, mv, cheer) {
    const base = STANCE[kind] || STANCE.stand, br = Math.sin(t * 1.7 + f.seed) * 0.02; let hop = 0;
    if (cheer > 0.02) { const c = cheerA(t, f.seed); mixA(A, base, c, cl(cheer)); hop = c.hop * cl(cheer); }
    else if (mv > 0.1 && kind !== "ref") mixA(A, base, runA(t * (10 + mv * 3) + f.seed, 0.6 + mv * 0.5), cl((mv - 0.1) * 3));
    else { mixA(A, base, base, 0); A.lean += br; A.head += Math.sin(t * 0.6 + f.seed * 2) * 0.05; A.look = Math.sin(t * 0.43 + f.seed) * 0.25; }
    apply(f, A); f.g.position.y = hop * f.g.scale.y;
  }

  // ---- the mascot: a big plush head on a costume in the home colours ----
  const KIND = [[/^(PHI|ATL|SEA|BAL|ARI|ARIZ)$|eagle|falcon|hawk|raven|cardinal|duck|owl|bird|jay/i, "bird"], [/^(DET|CAR|JAX|CIN)$|lion|tiger|panther|jaguar|bengal|cougar|wildcat|bobcat|cats?$/i, "cat"], [/^(CHI)$|bear|bruin|grizzl/i, "bear"],
    [/^(DEN|IND|LAC)$|bronco|colt|mustang|charger|horse/i, "horse"], [/^(CLE|KC|JMU|UGA)$|dog|husk|wolf|wolves|terrier|duke/i, "dog"], [/^(BUF|HOU|LAR|LA|TEX)$|bill|bison|buffalo|ram|longhorn|texan|bull/i, "bull"],
    [/^(DAL|OKST|WYO)$|cowboy/i, "cowboy"], [/^(MIN)$|viking/i, "viking"]];
  const FUR = { bird: null, cat: [0.78, 0.5, 0.14], bear: [0.36, 0.22, 0.12], horse: [0.86, 0.84, 0.8], dog: [0.6, 0.47, 0.36], bull: [0.3, 0.2, 0.14], cowboy: [0.72, 0.52, 0.4], viking: [0.72, 0.52, 0.4], cap: [0.72, 0.52, 0.4] };
  const MD = { neck: 0.78, shW: 0.36, shY: 0.6, uarm: 0.27, hipW: 0.15, thigh: 0.3, shin: 0.3, foot: 0.09 };
  function mascot(o) {
    const kindOf = (KIND.find(([re]) => re.test(o.ab || "") || re.test(o.name || "")) || [0, "cap"])[1], J = o.col, AL = o.alt || WHITE, F = FUR[kindOf] || (kindOf === "bird" ? J.map((v) => Math.min(1, v * 1.15 + 0.03)) : FUR.cap);
    const YEL = [0.95, 0.68, 0.08], PINK = [0.9, 0.4, 0.45], EYE = [0.96, 0.96, 0.96], HEADC = kindOf === "bird" ? WHITE : F;
    const hp = [part(sph(0.44, 22, 16), HEADC, [0, 0.36, 0], [0, 0, 0], [1, 0.95, 0.96]),
      part(sph(0.115, 12, 10), EYE, [-0.17, 0.46, 0.36], [0, 0, 0], [1, 1.2, 0.6]), part(sph(0.115, 12, 10), EYE, [0.17, 0.46, 0.36], [0, 0, 0], [1, 1.2, 0.6]),
      part(sph(0.055, 10, 8), DARK, [-0.16, 0.45, 0.42]), part(sph(0.055, 10, 8), DARK, [0.16, 0.45, 0.42]),
      part(box(0.2, 0.05, 0.06), DARK, [-0.17, 0.61, 0.37], [0, 0, -0.38]), part(box(0.2, 0.05, 0.06), DARK, [0.17, 0.61, 0.37], [0, 0, 0.38])];   // the game face
    if (kindOf === "bird") hp.push(part(cone(0.15, 0.42, 10), YEL, [0, 0.3, 0.55], [Math.PI / 2 + 0.25, 0, 0], [1, 1, 0.8]), part(cone(0.1, 0.3, 6), HEADC, [0, 0.82, -0.05], [-0.4, 0, 0]), part(cone(0.09, 0.26, 6), HEADC, [-0.12, 0.78, -0.12], [-0.5, 0, 0.3]), part(cone(0.09, 0.26, 6), HEADC, [0.12, 0.78, -0.12], [-0.5, 0, -0.3]));
    else if (kindOf === "cat") hp.push(part(cone(0.14, 0.26, 4), F, [-0.27, 0.76, 0]), part(cone(0.14, 0.26, 4), F, [0.27, 0.76, 0]), part(sph(0.2, 12, 10), WHITE, [0, 0.25, 0.33], [0, 0, 0], [1.25, 0.8, 0.9]), part(sph(0.06, 8, 6), DARK, [0, 0.33, 0.51]), part(box(0.2, 0.03, 0.04), DARK, [0, 0.2, 0.49]),
      part(sph(0.5, 16, 10), F.map((v) => v * 0.6), [0, 0.34, -0.12], [0, 0, 0], [1.08, 1.02, 0.8]));
    else if (kindOf === "bear") hp.push(part(sph(0.14), F, [-0.32, 0.72, 0]), part(sph(0.14), F, [0.32, 0.72, 0]), part(sph(0.2, 12, 10), [0.8, 0.66, 0.48], [0, 0.26, 0.34], [0, 0, 0], [1.1, 0.85, 0.9]), part(sph(0.07, 8, 6), DARK, [0, 0.33, 0.52]));
    else if (kindOf === "dog") hp.push(part(box(0.16, 0.42, 0.26), F.map((v) => v * 0.6), [-0.44, 0.34, 0], [0, 0, -0.25]), part(box(0.16, 0.42, 0.26), F.map((v) => v * 0.6), [0.44, 0.34, 0], [0, 0, 0.25]), part(sph(0.22, 12, 10), WHITE, [0, 0.24, 0.36], [0, 0, 0], [1.3, 0.9, 1.05]), part(sph(0.075, 8, 6), DARK, [0, 0.34, 0.58]), part(box(0.12, 0.2, 0.03), PINK, [0, 0.06, 0.5], [0.3, 0, 0]),
      part(tor(0.3, 0.05, Math.PI * 2, 14), J, [0, -0.02, 0], [Math.PI / 2, 0, 0]), part(cone(0.05, 0.12, 4), GREY, [0, -0.02, 0.33], [Math.PI / 2, 0, 0]));
    else if (kindOf === "horse") hp.push(part(cap(0.2, 0.3), F, [0, 0.2, 0.42], [1.15, 0, 0]), part(sph(0.04, 6, 6), DARK, [-0.08, 0.1, 0.72]), part(sph(0.04, 6, 6), DARK, [0.08, 0.1, 0.72]), part(cone(0.08, 0.26, 5), F, [-0.2, 0.84, 0]), part(cone(0.08, 0.26, 5), F, [0.2, 0.84, 0]),
      part(box(0.1, 0.6, 0.3), J, [0, 0.5, -0.36], [0.25, 0, 0]), part(box(0.1, 0.2, 0.24), J, [0, 0.84, 0.1], [-0.5, 0, 0]));
    else if (kindOf === "bull") hp.push(part(cone(0.08, 0.42, 8), WHITE, [-0.5, 0.66, 0], [0, 0, 0.9]), part(cone(0.08, 0.42, 8), WHITE, [0.5, 0.66, 0], [0, 0, -0.9]), part(sph(0.22, 12, 10), [0.72, 0.56, 0.44], [0, 0.22, 0.36], [0, 0, 0], [1.25, 0.85, 0.95]), part(sph(0.04, 6, 6), DARK, [-0.09, 0.24, 0.56]), part(sph(0.04, 6, 6), DARK, [0.09, 0.24, 0.56]), part(tor(0.07, 0.018, Math.PI * 2, 12), YEL, [0, 0.13, 0.55]));
    else { hp.push(part(sph(0.1, 8, 6), F.map((v) => v * 0.92), [0, 0.32, 0.43]), part(box(0.26, 0.05, 0.05), DARK, [0, 0.16, 0.4]), part(sph(0.26, 12, 8), F, [0, 0.1, 0.16], [0, 0, 0], [1.2, 0.7, 1]));                // a nose, a grin, a jaw
      if (kindOf === "cowboy") hp.push(part(cyl(0.72, 0.72, 0.04, 22), WHITE, [0, 0.7, 0], [0, 0, 0], [1, 1, 0.82]), part(cyl(0.3, 0.38, 0.34, 16), WHITE, [0, 0.88, 0]), part(cyl(0.385, 0.385, 0.07, 16), J, [0, 0.75, 0]), part(cone(0.07, 0.07, 5), AL, [0, 0.75, 0.39], [Math.PI / 2, 0, 0]));
      else if (kindOf === "viking") hp.push(part(sph(0.46, 16, 8), J, [0, 0.46, -0.02], [0, 0, 0], [1, 0.8, 1]), part(cone(0.09, 0.5, 8), WHITE, [-0.5, 0.8, 0], [0, 0, 0.7]), part(cone(0.09, 0.5, 8), WHITE, [0.5, 0.8, 0], [0, 0, -0.7]), part(box(0.5, 0.5, 0.06), YEL, [0, 0.0, 0.3], [0.2, 0, 0], [1, 1, 1]));
      else hp.push(part(sph(0.46, 16, 8), J, [0, 0.5, -0.02], [0, 0, 0], [1, 0.72, 1]), part(box(0.6, 0.04, 0.4), J, [0, 0.62, 0.42], [0.12, 0, 0]), part(sph(0.05, 6, 6), AL, [0, 0.84, 0])); }
    const geo = {
      pelvis: merge([part(sph(0.3, 14, 10), AL, [0, 0.04, 0], [0, 0, 0], [1.05, 0.72, 0.95]), ...(["cat", "dog", "horse", "bull", "bear"].includes(kindOf) ? [part(cap(0.05, kindOf === "bear" ? 0.02 : 0.36), F, [0, 0.1, -0.36], [-0.9, 0, 0])] : [])]),
      chest: merge([part(sph(0.36, 18, 14), J, [0, 0.34, 0], [0, 0, 0], [1.08, 1.02, 0.96]), part(tor(0.2, 0.05, Math.PI * 2, 14), AL, [0, 0.66, 0], [Math.PI / 2, 0, 0]), part(box(0.74, 0.07, 0.02), AL, [0, 0.2, 0.33]), part(sph(0.13), J, [-0.36, 0.6, 0]), part(sph(0.13), J, [0.36, 0.6, 0])]),
      head: merge(hp),
      uarm: merge([part(cap(0.1, 0.16), J, [0, -0.12, 0]), part(sph(0.095, 8, 6), F, [0, -0.27, 0])]),
      farm: merge([part(cap(0.09, 0.14), F, [0, -0.11, 0]), part(sph(0.15, 12, 10), WHITE, [0, -0.3, 0], [0, 0, 0], [1, 1.05, 0.8]), part(sph(0.06, 8, 6), WHITE, [0.13, -0.24, 0.02])]),
      thigh: merge([part(cap(0.14, 0.12), AL, [0, -0.13, 0])]),
      shin: merge([part(cap(0.115, 0.1), F, [0, -0.12, 0]), part(sph(0.17, 12, 8), J, [0, -0.3, 0.1], [0, 0, 0], [1, 0.62, 1.7]), part(box(0.3, 0.035, 0.52), WHITE, [0, -0.375, 0.1])]),
    };
    const f = rig(geo, MD, [matBody, matBody]); f.g.scale.setScalar(o.scale || 2.5); f.kind = kindOf; f.seed = 0;
    // the name on its back, the letters on its chest
    const c = document.createElement("canvas"); c.width = 256; c.height = 128; const x = c.getContext("2d"); x.font = "900 96px 'Barlow Condensed', 'Arial Narrow', Arial, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.lineWidth = 10; x.strokeStyle = "#0a0d14"; x.strokeText(o.ab || "", 128, 68); x.fillStyle = css(AL); x.fillText(o.ab || "", 128, 68);
    const tx = new THREE.CanvasTexture(c), pm = new THREE.MeshBasicMaterial({ map: tx, transparent: true, alphaTest: 0.2 }), pl = new THREE.Mesh(new THREE.PlaneGeometry(0.46, 0.23), pm); pl.position.set(0, 0.42, 0.365); f.j.chest.add(pl);
    f.hand = f.j.eR; f.dispose = () => { for (const k in geo) geo[k].dispose(); tx.dispose(); pm.dispose(); pl.geometry.dispose(); };
    return f;
  }
  // one frame of the mascot. act: idle | run | dance | cheer | catch | spike | sad | flip (k 0..1) | carry (a run with one arm up)
  function poseMascot(f, act, t, k = 0) {
    let hop = 0, a; f.g.rotation.x = 0;
    if (act === "run" || act === "carry") { a = runA(t * 11, 0.7); hop = Math.abs(Math.sin(t * 11)) * 0.1; if (act === "carry") { a.sh[1] = -2.9; a.el[1] = -0.15; a.shz = [0.12, 0.1]; } }
    else if (act === "dance") { a = danceA(t); hop = a.hop; }
    else if (act === "cheer") { a = cheerA(t, 0); hop = a.hop; }
    else if (act === "catch") a = { lean: -0.2, head: -0.6, th: [-0.2, 0.15], kn: [0.3, 0.2], sh: [-2.95, -2.95], el: [-0.2, -0.2], shz: [0.2, 0.2] };
    else if (act === "spike") a = mixA({}, { lean: -0.25, head: -0.3, th: [-0.1, 0.1], kn: [0.2, 0.2], sh: [-3.0, -3.0], el: [-0.5, -0.5], shz: [0.1, 0.1] }, { lean: 0.75, head: 0.2, th: [-0.7, -0.5], kn: [0.9, 0.8], sh: [-0.5, -0.5], el: [-0.1, -0.1], shz: [0.1, 0.1] }, cl(k));
    else if (act === "sad") a = { lean: 0.5, head: 0.55, th: [-0.1, 0.05], kn: [0.2, 0.15], sh: [-2.5, -2.5], el: [-2.0, -2.0], shz: [-0.35, -0.35], look: Math.sin(t * 3) * 0.35 };
    else if (act === "flip") { const u = cl(k), tuck = Math.sin(u * Math.PI); a = { lean: 0.3 * tuck, head: 0, th: [-1.5 * tuck, -1.5 * tuck], kn: [1.9 * tuck, 1.9 * tuck], sh: [-2.8 + 2.0 * tuck, -2.8 + 2.0 * tuck], el: [-0.6, -0.6], shz: [0.2, 0.2] }; hop = Math.sin(u * Math.PI) * 1.25; f.g.rotation.x = -u * Math.PI * 2; }
    else { const w = Math.max(0, Math.sin(t * 0.5)) > 0.8; a = mixA({}, STANCE.hips, STANCE.hips, 0); a.lean += Math.sin(t * 2) * 0.03; a.look = Math.sin(t * 0.7) * 0.4; hop = Math.abs(Math.sin(t * 2.6)) * 0.05; if (w) { a.sh = [a.sh[0], -2.7 + Math.sin(t * 9) * 0.3]; a.el = [a.el[0], -0.4]; a.shz = [a.shz[0], 0.4]; } }
    apply(f, mixA(A, a, a, 0)); const s = f.g.scale.y, D = f.D;
    // a flip turns about the middle of the body, not the feet
    if (act === "flip") { const mid = (D.thigh + D.shin + 0.35) * s, an = f.g.rotation.x; f.g.position.y = hop * s + mid - Math.cos(an) * mid; f.off = Math.sin(an) * mid; } else { f.g.position.y = hop * s; f.off = 0; }
  }
  // any figure, any move: the mascot's own (run, carry, dance, cheer, catch, spike, flip, sad, idle) and the dance floor's
  function poseMove(f, style, t, k = 0) { const s = Math.sin; let a = null, hop = 0;
    if (style === "skip") { const u = s(t * 7); a = { lean: 0.12, twist: u * 0.25, th: [u > 0 ? -1.3 * u : 0.1, u < 0 ? 1.3 * u : 0.1], kn: [u > 0 ? 1.4 * u : 0.1, u < 0 ? -1.4 * u : 0.1], sh: [u * 1.1, -u * 1.1], el: [-1.2, -1.2], shz: [0.25, 0.25] }; hop = Math.abs(u) * 0.16; }
    else if (style === "robot") { const q = Math.floor(t * 2.6) % 4; a = { lean: 0, twist: [0.4, 0, -0.4, 0][q], look: [-0.6, 0, 0.6, 0][q], th: [0.03, -0.03], kn: [0.05, 0.05], sh: [[-1.57, 0, -1.57, -3][q], [0, -1.57, -1.57, -3][q]], el: [[-1.57, 0, -1.57, 0][q], [0, -1.57, -1.57, 0][q]], shz: [0.1, 0.1] }; }
    else if (style === "wave") { const u = s(t * 3.2); a = { lean: 0, roll: u * 0.2, th: [0.05, -0.05], kn: [0.06, 0.06], sh: [-2.9, -2.9], el: [-0.2, -0.2], shz: [0.5 + u * 0.4, 0.5 - u * 0.4] }; }
    else if (style === "pump") { const u = Math.abs(s(t * 8)); a = { lean: 0.1, th: [-0.2, 0.1], kn: [0.3, 0.2], sh: [-2.2 - u * 0.7, 0.2], el: [-1.6 + u * 1.4, -0.4], shz: [0.2, 0.1] }; hop = u * 0.08; }
    else if (style === "point") a = { lean: 0.05, th: [0.03, -0.03], kn: [0.04, 0.04], sh: [0.1, -1.55], el: [-0.2, -0.05], shz: [0.1, 0.15], look: -0.2 };
    else if (style === "throw") { const u = cl(k); a = { lean: -0.1 + u * 0.3, twist: 0.6 - u * 1.2, th: [-0.35, 0.3], kn: [0.3, 0.25], sh: [-0.9, 0.6 - u * 3.4], el: [-0.3, -1.9 + u * 1.6], shz: [0.2, 0.5] }; }
    if (!a) return poseMascot(f, style, t, k);
    f.g.rotation.x = 0; apply(f, mixA(A, a, a, 0)); f.g.position.y = hop * f.g.scale.y; }
  // what stands a figure up in the light: sky and ground, and the floodlights from the camera side
  function lights(scene) { const h = new THREE.HemisphereLight(new THREE.Color(1, 1, 1), new THREE.Color(0.16, 0.24, 0.14), 1.25), d = new THREE.DirectionalLight(new THREE.Color(1, 0.97, 0.9), 1.5), d2 = new THREE.DirectionalLight(new THREE.Color(0.75, 0.85, 1), 0.55); d.position.set(-30, 90, 70); d2.position.set(40, 60, -80); scene.add(h, d, d2); return [h, d, d2]; }
  return { kit, posePlayer, mascot, poseMascot, poseMove, person, posePerson, freeze, lights, STANCE, part, merge };
}
