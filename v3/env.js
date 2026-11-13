// The life around the field: cheerleaders working both sidelines, the coaches, the chain crew and its sticks on the line
// to gain, photographers along the end lines, camera crews, pylons, the benches and coolers, a blimp overhead, and the
// weather the game is being played in. Built once per stadium from the figure kit; update() runs it every frame.
const cl = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v)), lerp = (a, b, t) => a + (b - a) * t;

export function makeEnv(st, F, o) {
  const THREE = st.THREE, scene = st.scene, V = st.V, top = V.top || 46, open = !(V.dome || V.roof), hc = o.home, alt = o.alt, ac = o.away;
  const C = (c, k = 1) => new THREE.Color().setRGB(Math.min(1, c[0] * k), Math.min(1, c[1] * k), Math.min(1, c[2] * k), THREE.LinearSRGBColorSpace);
  const flat = (c, x) => new THREE.MeshBasicMaterial(Object.assign({ color: C(c) }, x || {})), lit = (c, x) => new THREE.MeshLambertMaterial(Object.assign({ color: C(c) }, x || {}));
  const add = (m) => { scene.add(m); return m; }, SZ = 26.67, ORANGE = [1, 0.42, 0.05], tex = (cv) => { const t = new THREE.CanvasTexture(cv); t.anisotropy = 8; st.tex.push(t); return t; };
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(), s3 = new THREE.Vector3();
  const inst = (mesh, list) => { list.forEach(([x, y, z, ry, sc], i) => { e.set(0, ry || 0, 0); q.setFromEuler(e); s3.setScalar(sc || 1); m4.compose(p3.set(x, y, z), q, s3); mesh.setMatrixAt(i, m4); }); mesh.count = list.length; mesh.instanceMatrix.needsUpdate = true; scene.add(mesh); return mesh; };

  // pylons at the goal lines and end lines
  { const g = new THREE.BoxGeometry(0.34, 1.5, 0.34), m = new THREE.InstancedMesh(g, flat(ORANGE), 8), L = []; for (const x of [-60, -50, 50, 60]) for (const z of [-SZ, SZ]) L.push([x, 0.75, z, 0, 1]); inst(m, L); }
  // the benches behind each team, and the coolers
  for (const sd of [-1, 1]) { const b = add(new THREE.Mesh(new THREE.BoxGeometry(34, 0.5, 0.9), lit([0.62, 0.64, 0.7]))); b.position.set(0, 0.5, sd * (SZ + 6.9)); const bk = add(new THREE.Mesh(new THREE.BoxGeometry(34, 0.9, 0.12), lit(sd < 0 ? hc : ac))); bk.position.set(0, 1.1, sd * (SZ + 7.4));
    for (const x of [-19.5, 19.5]) { const tb = add(new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.9, 1.1), lit([0.8, 0.8, 0.82]))); tb.position.set(x, 0.45, sd * (SZ + 6.6)); for (const dx of [-0.6, 0.6]) { const c = add(new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.38, 0.9, 12), lit(ORANGE))); c.position.set(x + dx, 1.35, sd * (SZ + 6.6)); const l = add(new THREE.Mesh(new THREE.CylinderGeometry(0.44, 0.44, 0.12, 12), lit([0.95, 0.95, 0.95]))); l.position.set(x + dx, 1.85, sd * (SZ + 6.6)); } } }

  // the chain crew, on the home sideline: two sticks ten yards apart, the down box on the ball
  const mkStick = (sign) => { const g = new THREE.Group(), pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 3.1, 8), flat(ORANGE)); pole.position.y = 1.55; g.add(pole); for (const y of [0.9, 1.9]) { const b = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.3, 8), flat([0.05, 0.05, 0.06])); b.position.y = y; g.add(b); }
    const hd = new THREE.Mesh(sign ? new THREE.BoxGeometry(0.9, 0.9, 0.12) : new THREE.CylinderGeometry(0.42, 0.42, 0.12, 4), flat(ORANGE)); hd.position.y = 3.3; if (!sign) hd.rotation.x = Math.PI / 2; g.add(hd); scene.add(g); return g; };
  const CZ = -(SZ + 1.15), stA = mkStick(false), stB = mkStick(false), box = mkStick(true), chain = add(new THREE.Mesh(new THREE.BoxGeometry(1, 0.05, 0.05), flat([0.75, 0.76, 0.8]))); chain.position.set(0, 0.12, CZ);
  const dcv = document.createElement("canvas"); dcv.width = dcv.height = 64; const dtx = tex(dcv), dface = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.8), new THREE.MeshBasicMaterial({ map: dtx })); dface.position.set(0, 3.3, 0.07); box.add(dface); let dShown = -1;
  const setDown = (n) => { if (n === dShown) return; dShown = n; const x = dcv.getContext("2d"); x.fillStyle = "#ff6b0d"; x.fillRect(0, 0, 64, 64); x.fillStyle = "#0a0a0c"; x.font = "900 56px Arial, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText(String(n || ""), 32, 35); dtx.needsUpdate = true; };
  const crew = [0, 1, 2].map((i) => { const f = F.person({ kind: "crew", top: [0.95, 0.4, 0.06], bottom: [0.08, 0.08, 0.1], skin: [[0.62, 0.42, 0.28], [0.36, 0.22, 0.14], [0.78, 0.58, 0.44]][i], seed: i * 2.1 }); scene.add(f.g); f.g.position.z = CZ - 0.75; return f; });
  const chains = { a: 0, b: 10, x: 0 };

  // the coaches, a step onto the field from each bench, following the ball
  const coaches = [-1, 1].map((sd) => { const f = F.person({ kind: "coach", top: sd < 0 ? hc : ac, bottom: [0.14, 0.14, 0.17], skin: sd < 0 ? [0.78, 0.58, 0.44] : [0.45, 0.29, 0.19], hair: [0.3, 0.3, 0.32], seed: sd * 3 }); scene.add(f.g); f.g.position.set(0, 0, sd * (SZ + 2.1)); f.g.rotation.y = sd < 0 ? 0 : Math.PI; f.sd = sd; return f; });

  // the cheerleaders: a line on each sideline past the benches, in the home colours, facing the stands
  const cheer = []; for (const sd of [-1, 1]) for (let i = 0; i < 5; i++) { const f = F.person({ kind: "cheer", top: sd < 0 ? hc : alt, bottom: sd < 0 ? hc : alt, alt: sd < 0 ? alt : hc, skin: [[0.78, 0.58, 0.44], [0.62, 0.42, 0.28], [0.36, 0.22, 0.14], [0.86, 0.68, 0.54], [0.5, 0.33, 0.22]][i], hair: [[0.5, 0.36, 0.14], [0.08, 0.06, 0.05], [0.25, 0.13, 0.07], [0.62, 0.48, 0.2], [0.05, 0.04, 0.04]][(i + (sd > 0 ? 2 : 0)) % 5], seed: i * 0.9 + sd, scale: 1.22 });
    scene.add(f.g); f.g.position.set((sd < 0 ? 25 : -41) + i * 3.2, 0, sd * (SZ + 3.4)); f.g.rotation.y = sd < 0 ? Math.PI : 0; f.lag = i * 0.12; cheer.push(f); }

  // photographers kneeling along both end lines, camera crews at the corners
  { const k = F.person({ kind: "cam", top: [0.16, 0.17, 0.2], bottom: [0.1, 0.1, 0.12], skin: [0.72, 0.52, 0.4] }); F.posePerson(k, "kneel", 0); const m = F.freeze(k, 22), L = [];
    for (const sd of [-1, 1]) for (let i = 0; i < 11; i++) { if (i === 5) continue; L.push([sd * (62.6 + (i % 2) * 0.9), 0, -19 + i * 3.8, sd < 0 ? Math.PI / 2 : -Math.PI / 2, 1.25]); } inst(m, L); k.dispose(); }
  { const k = F.person({ kind: "cam", top: [0.85, 0.2, 0.15], bottom: [0.1, 0.1, 0.12], skin: [0.55, 0.38, 0.26] }); F.posePerson(k, "cam", 0); const m = F.freeze(k, 6), L = [], cart = new THREE.InstancedMesh(new THREE.BoxGeometry(2.2, 1.3, 2.2), lit([0.14, 0.15, 0.18]), 6), CL = [];
    for (const [x, z, ry] of [[-34, SZ + 3.2, Math.PI], [34, SZ + 3.2, Math.PI], [-56, -(SZ + 3), Math.PI / 4], [56, -(SZ + 3), -Math.PI / 4], [-66, 9, Math.PI / 2], [66, -9, -Math.PI / 2]]) { L.push([x, 1.3, z, ry, 1.28]); CL.push([x, 0.65, z, ry, 1]); } inst(cart, CL); inst(m, L); k.dispose(); }

  // the blimp, on a slow lap over an open building
  let blimp = null; if (open) { const g = new THREE.Group(), hull = new THREE.Mesh(new THREE.SphereGeometry(1, 28, 18), lit([0.86, 0.88, 0.93])); hull.scale.set(21, 6.4, 6.4); g.add(hull);
    const band = new THREE.Mesh(new THREE.SphereGeometry(1.004, 28, 6, 0, Math.PI * 2, Math.PI * 0.42, Math.PI * 0.16), lit(hc)); band.scale.copy(hull.scale); g.add(band);
    for (const [ry, rz] of [[0, 0], [0, Math.PI / 2], [0, Math.PI], [0, -Math.PI / 2]]) { const f = new THREE.Mesh(new THREE.BoxGeometry(6, 5.4, 0.3), lit(hc)); f.position.set(-17.5, 0, 0); const h = new THREE.Group(); h.rotation.x = rz; f.position.y = 3.6; h.add(f); g.add(h); }
    const gon = new THREE.Mesh(new THREE.BoxGeometry(5.4, 1.6, 2), lit([0.2, 0.21, 0.25])); gon.position.y = -6.8; g.add(gon);
    const cv = document.createElement("canvas"); cv.width = 1024; cv.height = 256; const x = cv.getContext("2d"); x.fillStyle = "#05070c"; x.fillRect(0, 0, 1024, 256); x.font = "900 150px 'Big Shoulders Display', 'Barlow Condensed', Arial, sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillStyle = "#ffffff"; x.fillText("SWEAT", 330, 134); x.fillStyle = "#ffc94d"; x.fillText("BOARD", 720, 134);
    const lt = tex(cv); for (const sd of [-1, 1]) { const p = new THREE.Mesh(new THREE.PlaneGeometry(22, 5.5), new THREE.MeshBasicMaterial({ map: lt })); p.position.set(0.5, -0.4, sd * 6.2); p.rotation.y = sd < 0 ? Math.PI : 0; p.rotation.x = sd * -0.12; g.add(p); }
    const bl = new THREE.Mesh(new THREE.SphereGeometry(0.5, 8, 6), flat([1, 0.1, 0.1])); bl.position.set(0, -7.8, 0); g.add(bl); scene.add(g); blimp = { g, bl, r: Math.max(V.A || 90, V.B || 70) + 55 }; }

  // the weather: snow or rain over an open field, from the game's own report
  let wx = null; const wxKind = () => { try { const d = window.__demoWx; if (d) return d; const g = window.__sbFeat && window.__sbFeat(), s = g && g.wx ? String(g.wx.txt || "") : ""; return /snow|flurr|sleet|wintry/i.test(s) ? "snow" : /rain|shower|drizzle|storm/i.test(s) ? "rain" : ""; } catch (err) { return ""; } };
  const wxSet = (k) => { if (wx && wx.k === k) return; if (wx) { scene.remove(wx.pts); wx.pts.geometry.dispose(); wx.pts.material.dispose(); wx = null; } if (!k || !open) return;
    const N = k === "snow" ? 7000 : 6500, pos = new Float32Array(N * 3), sp = new Float32Array(N); for (let i = 0; i < N; i++) { pos[i * 3] = (Math.random() - 0.5) * 190; pos[i * 3 + 1] = Math.random() * (top + 40); pos[i * 3 + 2] = (Math.random() - 0.5) * 130; sp[i] = 0.6 + Math.random() * 0.8; }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); const cv = document.createElement("canvas"); cv.width = cv.height = 32; const x = cv.getContext("2d"), gr = x.createRadialGradient(16, 16, 0, 16, 16, 16); gr.addColorStop(0, "#fff"); gr.addColorStop(0.4, "rgba(255,255,255,.7)"); gr.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = gr; x.fillRect(0, 0, 32, 32);
    const pts = new THREE.Points(g, new THREE.PointsMaterial({ size: k === "snow" ? 1.05 : 0.45, map: tex(cv), color: C(k === "snow" ? [1, 1, 1] : [0.62, 0.72, 0.9]), transparent: true, opacity: k === "snow" ? 0.95 : 0.6, depthWrite: false })); pts.frustumCulled = false; scene.add(pts); wx = { k, pts, pos, sp, N, H: top + 40 }; };
  let wxAt = -99, last = null, hype = 0;

  return {
    // S: { x, dir, has, togo, dn } from the field; play: is a play on; cheerK: how loud the home side is (0..1)
    update(t, S, play, cheerK) {
      const dt = last == null ? 0.016 : Math.min(0.1, t - last); last = t; hype = lerp(hype, cheerK > 0.2 ? 1 : 0, 0.06);
      // chains: the box on the ball, the sticks from the series' start to the line to gain
      if (S.has) { const ltg = S.togo != null ? cl(S.x + S.dir * S.togo, -50, 50) : S.x + S.dir * 10; chains.b = lerp(chains.b, ltg, 0.08); chains.a = lerp(chains.a, cl(ltg - S.dir * 10, -50, 50), 0.08); chains.x = lerp(chains.x, S.x, 0.1); setDown(S.dn || 1); }
      stA.position.set(chains.a, 0, CZ); stB.position.set(chains.b, 0, CZ); box.position.set(chains.x, 0, CZ - 0.25); chain.position.x = (chains.a + chains.b) / 2; chain.scale.x = Math.max(0.1, Math.abs(chains.b - chains.a));
      for (const g of [stA, stB, box, chain]) g.visible = !!S.has; [chains.a, chains.b, chains.x].forEach((x, i) => { const f = crew[i]; f.g.visible = !!S.has; f.g.position.x = x + (i === 2 ? 0.6 : 0); F.posePerson(f, "stand", t); });
      // coaches drift with the ball; arms up when their side has something to shout about
      for (const f of coaches) { const tx = cl((S.has ? S.x : 0) + f.sd * 2, -22, 22); f.g.position.x = lerp(f.g.position.x, tx, 0.02); F.posePerson(f, f.sd < 0 && cheerK > 0.4 ? "hype" : "coach", t); }
      // cheerleaders: the routine, or all up on a score
      for (const f of cheer) F.posePerson(f, hype > 0.5 ? "hype" : "cheer", t - f.lag);
      if (blimp) { const a = t * 0.035; blimp.g.position.set(Math.cos(a) * blimp.r, top + 62 + Math.sin(t * 0.3) * 1.5, Math.sin(a) * blimp.r * 0.8); blimp.g.rotation.y = -a - Math.PI / 2; blimp.bl.visible = (t * 1.2) % 1 < 0.35; }
      if (t - wxAt > 20) { wxAt = t; wxSet(wxKind()); }
      if (wx) { const a = wx.pos, snow = wx.k === "snow", vy = snow ? 5.5 : 46; for (let i = 0; i < wx.N; i++) { const j = i * 3; a[j + 1] -= vy * wx.sp[i] * dt; a[j] += (snow ? Math.sin(t * 0.8 + i) * 0.9 + 1.2 : 5) * dt; if (a[j + 1] < 0) { a[j + 1] = wx.H; a[j] = (Math.random() - 0.5) * 190; } } wx.pts.geometry.attributes.position.needsUpdate = true; }
    },
  };
}
