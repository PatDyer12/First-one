// V3's stadiums: every game on the board gets its own toy stadium, floating beside its bets. The field wears the two teams'
// colours, the ball sits where the ball is (with the line to gain), it slides when the play moves it, the crowd jumps and the
// lights flash on a score. They bob and turn a little all the time, and glide to wherever their game's lane goes.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const A = 5.6, B = 3.1, NEXP = 3.2;   // the bowl's inside edge: a superellipse round the field
const sgn = (v) => (v < 0 ? -1 : 1);
const ring = (th, o) => { const c = Math.cos(th), s = Math.sin(th), e = 2 / NEXP; return [(A + o) * sgn(c) * Math.pow(Math.abs(c), e), (B + o) * sgn(s) * Math.pow(Math.abs(s), e)]; };
const C3 = (c) => new THREE.Color(c[0], c[1], c[2]);
const cnv = (w, h) => { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; };
const css = (c, k = 1) => `rgb(${c.map((v) => Math.round(Math.min(1, v * k) * 255)).join(",")})`;

// a band of the bowl between two (offset, height) edges, all the way round
function band(o0, y0, o1, y1, seg = 96) {
  const pos = [], uv = [], idx = [];
  for (let i = 0; i <= seg; i++) { const th = (i / seg) * Math.PI * 2, p0 = ring(th, o0), p1 = ring(th, o1); pos.push(p0[0], y0, p0[1], p1[0], y1, p1[1]); uv.push(i / seg, 0, i / seg, 1); }
  for (let i = 0; i < seg; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals(); return g;
}
function glowTex() { const c = cnv(128, 128), x = c.getContext("2d"), g = x.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.25, "rgba(255,255,255,.55)"); g.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = g; x.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c); }

export function makeWorld(renderer) {
  const W = { punch: 0, st: new Map() };
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(40, 16 / 9, 0.1, 400); W.scene = scene; W.cam = cam;
  const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; pm.dispose();
  scene.add(new THREE.HemisphereLight(0xcfdcff, 0x1a1030, 1.0)); const key = new THREE.DirectionalLight(0xffffff, 2.2); key.position.set(4, 10, 12); scene.add(key);
  const gloss = (col, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: col, roughness: 0.3, metalness: 0.12, envMapIntensity: 0.85, side: THREE.DoubleSide }, o));
  const glowT = glowTex();
  const glow = (parent, x, y, z, s, col, op = 1) => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowT, color: col, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: op })); sp.position.set(x, y, z); sp.scale.set(s, s, 1); parent.add(sp); return sp; };
  // shared shapes: every stadium is the same mould in different colours
  const GEO = { apron: band(0.25, 0.04, 0.3, 0.42, 64), lo: band(0.3, 0.42, 1.9, 1.5, 64), mid: band(1.9, 1.5, 1.95, 1.95, 64), up: band(1.95, 1.95, 3.5, 3.25, 64), rim: band(3.5, 3.25, 3.9, 3.25, 64), out: band(3.9, 3.25, 4.05, 0, 64), roof: band(2.9, 3.95, 4.3, 3.5, 64), lip: band(2.84, 3.92, 2.9, 4.0, 64),
    head: new THREE.SphereGeometry(0.1, 5, 4), slab: new THREE.CylinderGeometry(1, 1, 0.5, 48), ball: new THREE.SphereGeometry(0.26, 12, 8), post: new THREE.CylinderGeometry(0.03, 0.03, 1, 6), ringG: new THREE.RingGeometry(0.42, 0.6, 24), line: new THREE.PlaneGeometry(0.12, 4.6), pole: new THREE.CylinderGeometry(0.06, 0.09, 5.6, 6), lamp: new THREE.BoxGeometry(1, 0.55, 0.16) };
  const white = gloss(0xeef2fa), dark = gloss(0x0e1322, { roughness: 0.4 }), yel = gloss(0xffd21f, { emissive: 0x6a5200 });
  const _m = new THREE.Matrix4(), _c = new THREE.Color(), _v = new THREE.Vector3(), _ray = new THREE.Raycaster();
  const RX = A + 4.7, RZ = B + 4.7, FW = 10, FH = 4.6;

  function makeStadium() {
    const root = new THREE.Group(), S = new THREE.Group(); root.add(S); scene.add(root);
    const Z = { root, S, ex: [0, 0], flash: 0, col: new THREE.Color(1, 1, 1), ballX: 0, ballT: 0, sig: "", born: 0, pos: null, sc: 0 };
    const slab = new THREE.Mesh(GEO.slab, gloss(0x141a2e)); slab.scale.set(RX, 1, RZ); slab.position.y = -0.27; S.add(slab);
    Z.neon = glow(S, 0, -0.45, 0, RX * 2.9, 0x4a7dff, 0.4); Z.neon.scale.set(RX * 2.9, RZ * 1.7, 1);
    const fc = cnv(512, 236), ftex = new THREE.CanvasTexture(fc); ftex.colorSpace = THREE.SRGBColorSpace; ftex.anisotropy = 4; Z.fc = fc; Z.ftex = ftex;
    const field = new THREE.Mesh(new THREE.PlaneGeometry(FW, FH), new THREE.MeshStandardMaterial({ map: ftex, roughness: 0.85, envMapIntensity: 0.2 })); field.rotation.x = -Math.PI / 2; field.position.y = 0.04; S.add(field);
    Z.seatLo = gloss(0x1f4fa8, { roughness: 0.5 }); Z.seatUp = gloss(0x123070, { roughness: 0.5 }); Z.lipM = new THREE.MeshBasicMaterial({ color: 0x4a7dff, side: THREE.DoubleSide });
    S.add(new THREE.Mesh(GEO.apron, white), new THREE.Mesh(GEO.lo, Z.seatLo), new THREE.Mesh(GEO.mid, dark), new THREE.Mesh(GEO.up, Z.seatUp), new THREE.Mesh(GEO.rim, white), new THREE.Mesh(GEO.out, gloss(0xdfe6f5)), new THREE.Mesh(GEO.roof, gloss(0xf4f7ff, { roughness: 0.2, metalness: 0.3 })), new THREE.Mesh(GEO.lip, Z.lipM));
    // the crowd
    const seats = [], NCR = 620; Z.crowd = new THREE.InstancedMesh(GEO.head, new THREE.MeshStandardMaterial({ roughness: 0.6, envMapIntensity: 0.3 }), NCR); Z.crowd.frustumCulled = false; S.add(Z.crowd);
    for (const [o0, y0, o1, y1, R] of [[0.3, 0.42, 1.9, 1.5, 5], [1.95, 1.95, 3.5, 3.25, 5]]) for (let r = 0; r < R; r++) { const k = (r + 0.5) / R, o = o0 + (o1 - o0) * k, y = y0 + (y1 - y0) * k + 0.11; for (let i = 0; i < 62; i++) { const th = ((i + (r % 2) * 0.5) / 62) * Math.PI * 2, p = ring(th, o); seats.push({ x: p[0], y, z: p[1], th, ph: Math.random() * 6.28, side: Math.cos(th) < -0.4 ? 0 : 1 }); } }
    Z.seats = seats; Z.crowd.count = seats.length;
    Z.pose = (t) => { for (let i = 0; i < seats.length; i++) { const s = seats[i], e = Z.ex[s.side], hop = e > 0.02 ? Math.abs(Math.sin(t * 9 + s.ph)) * 0.22 * e : 0; _m.makeTranslation(s.x, s.y + hop, s.z); Z.crowd.setMatrixAt(i, _m); } Z.crowd.instanceMatrix.needsUpdate = true; };
    // goalposts, four lights
    for (const sx of [-1, 1]) for (const [x, y, z, sy, rx] of [[0, 0.3, 0, 0.6, 0], [0, 0.6, 0, 0.9, Math.PI / 2], [0, 1.07, -0.45, 0.95, 0], [0, 1.07, 0.45, 0.95, 0]]) { const m = new THREE.Mesh(GEO.post, yel); m.position.set(sx * 5.25 + x, y, z); m.scale.y = sy; m.rotation.x = rx; S.add(m); }
    Z.lamps = [[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sz]) => { const x = sx * (A + 3.3), z = sz * (B + 3.3), pole = new THREE.Mesh(GEO.pole, dark); pole.position.set(x, 2.8, z); S.add(pole); const head = new THREE.Mesh(GEO.lamp, new THREE.MeshBasicMaterial({ color: 0xffffff })); head.position.set(x, 5.7, z); head.lookAt(0, 1.5, 0); S.add(head); return glow(S, x, 5.7, z, 3.6, 0xfff4d8, 0.8); });
    // the ball where the ball is, whose it is, and the line to gain
    Z.ball = new THREE.Mesh(GEO.ball, new THREE.MeshBasicMaterial({ color: 0xffffff })); Z.ball.position.y = 0.35; S.add(Z.ball); Z.ballG = glow(S, 0, 0.4, 0, 3.4, 0xffffff, 1);
    Z.ringM = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, side: THREE.DoubleSide }); Z.ring = new THREE.Mesh(GEO.ringG, Z.ringM); Z.ring.rotation.x = -Math.PI / 2; Z.ring.position.y = 0.07; S.add(Z.ring);
    Z.ltg = new THREE.Mesh(GEO.line, new THREE.MeshBasicMaterial({ color: 0xffd21f })); Z.ltg.rotation.x = -Math.PI / 2; Z.ltg.position.y = 0.06; S.add(Z.ltg);
    Z.los = new THREE.Mesh(GEO.line, new THREE.MeshBasicMaterial({ color: 0x4aa3ff })); Z.los.rotation.x = -Math.PI / 2; Z.los.position.y = 0.06; S.add(Z.los);
    return Z;
  }
  function paint(Z, g) {
    const x = Z.fc.getContext("2d"), ca = g.ca, ch = g.ch;
    for (let i = 0; i < 20; i++) { x.fillStyle = i % 2 ? "#2f9a4c" : "#278a42"; x.fillRect(43 + i * 21.3, 0, 22, 236); }
    x.fillStyle = css(ca, 0.95); x.fillRect(0, 0, 43, 236); x.fillStyle = css(ch, 0.95); x.fillRect(469, 0, 43, 236);
    x.strokeStyle = "rgba(255,255,255,.9)"; x.lineWidth = 3; x.strokeRect(2, 2, 508, 232); x.lineWidth = 1.5; for (let i = 0; i <= 20; i++) { const px = 43 + i * 21.3; x.globalAlpha = i % 2 ? 0.3 : 0.85; x.beginPath(); x.moveTo(px, 0); x.lineTo(px, 236); x.stroke(); } x.globalAlpha = 1;
    x.fillStyle = "#fff"; x.textAlign = "center"; x.textBaseline = "middle"; x.font = "900 34px 'Big Shoulders Display', 'Barlow Condensed', Arial, sans-serif";
    const ez = (t, px, rot) => { x.save(); x.translate(px, 118); x.rotate(rot); x.fillText(String(t || "").toUpperCase().slice(0, 10), 0, 1); x.restore(); }; ez(g.a, 22, -Math.PI / 2); ez(g.h, 490, Math.PI / 2);
    x.beginPath(); x.arc(256, 118, 30, 0, 7); x.fillStyle = css(ch, 1); x.fill(); x.lineWidth = 3; x.strokeStyle = "#fff"; x.stroke(); x.fillStyle = "#fff"; x.font = "900 26px 'Big Shoulders Display', Arial, sans-serif"; x.fillText(g.hab, 256, 120);
    Z.ftex.needsUpdate = true; Z.seatLo.color.setRGB(...ch.map((v) => v * 0.55 + 0.03)); Z.seatUp.color.setRGB(...ch.map((v) => v * 0.32 + 0.02));
    Z.seats.forEach((s, i) => { const base = s.side ? ch : ca, r = Math.random(); _c.setRGB(...(r < 0.75 ? base.map((v) => Math.min(1, v * (0.75 + Math.random() * 0.6) + 0.06)) : r < 0.92 ? [0.92, 0.92, 0.95] : [0.12, 0.13, 0.18])); Z.crowd.setColorAt(i, _c); }); Z.crowd.instanceColor.needsUpdate = true;
  }
  // a point on the board's plane under a screen pixel, and how big a pixel is there
  const at = (px, py, z) => { _v.set((px / innerWidth) * 2 - 1, 1 - (py / innerHeight) * 2, 0.5).unproject(cam).sub(cam.position).normalize(); const k = (z - cam.position.z) / _v.z; return [cam.position.x + _v.x * k, cam.position.y + _v.y * k, z]; };
  const yd = (y) => ((clampY(y) - 50) / 50) * (FW / 2 - 0.84), clampY = (y) => Math.max(0, Math.min(100, y));

  // every frame: which games are on the board, and where (screen px) each one's stadium goes
  W.sync = (list, t, dt) => {
    const seen = new Set();
    for (const L of list) {
      seen.add(L.key); let Z = W.st.get(L.key); if (!Z) { Z = makeStadium(); W.st.set(L.key, Z); Z.pose(t); }
      const g = L.g, sig = g.aab + g.hab; if (sig !== Z.sig) { Z.sig = sig; paint(Z, g); }
      const z = 0.6, p = at(L.x, L.y, z), p2 = at(L.x + L.w, L.y, z), size = Math.abs(p2[0] - p[0]), sc = (size / (RX * 2)) * (1 + 0.06 * Z.flash);
      if (!Z.pos) { Z.pos = p; Z.sc = sc * 0.2; } const k = Math.min(1, dt * 5); for (let i = 0; i < 3; i++) Z.pos[i] += (p[i] - Z.pos[i]) * k; Z.sc += (sc - Z.sc) * Math.min(1, dt * 4);
      const ph = L.key.length * 1.7 + (L.key.charCodeAt(L.key.length - 1) || 0);
      Z.root.position.set(Z.pos[0], Z.pos[1] + Math.sin(t * 0.9 + ph) * size * 0.012, Z.pos[2]); Z.root.scale.setScalar(Z.sc);
      Z.root.rotation.set(1.0 + Math.sin(t * 0.4 + ph) * 0.05, Math.sin(t * 0.22 + ph) * (g.live ? 0.3 : 0.16), Math.sin(t * 0.5 + ph) * 0.02);
      // the play: the ball slides to where it is now; the line to gain ahead of it
      const has = g.live && g.yl != null; Z.ball.visible = Z.ballG.visible = Z.ring.visible = has; Z.los.visible = has; Z.ltg.visible = has && g.togo != null;
      if (has) { const tx = yd(g.yl); if (Math.abs(tx - Z.ballT) > 0.01) { Z.ballT = tx; Z.hop = 1; } Z.ballX += (Z.ballT - Z.ballX) * Math.min(1, dt * 2.2); Z.hop = Math.max(0, (Z.hop || 0) - dt * 1.1);
        const arc = Math.sin((1 - Z.hop) * Math.PI) * (Z.hop > 0 ? 1.4 : 0); Z.ball.position.set(Z.ballX, 0.35 + arc, 0); Z.ballG.position.set(Z.ballX, 0.4 + arc, 0); Z.ring.position.x = Z.ballX; Z.los.position.x = Z.ballX;
        const pc = g.pos === "h" ? g.ch : g.pos === "a" ? g.ca : [1, 1, 1]; Z.ringM.color.setRGB(...pc.map((v) => Math.min(1, v + 0.25))); Z.ballG.material.color.setRGB(...pc.map((v) => Math.min(1, v + 0.4))); const s = 1 + 0.25 * Math.sin(t * 5); Z.ring.scale.set(s, s, 1);
        if (g.togo != null) Z.ltg.position.x = yd(g.yl + (g.pos === "h" ? -1 : 1) * g.togo); }
      for (let i = 0; i < 2; i++) Z.ex[i] = Math.max(0, Z.ex[i] - dt * 0.28); if (Z.ex[0] > 0.02 || Z.ex[1] > 0.02) { Z.pose(t); Z.still = false; } else if (!Z.still) { Z.pose(t); Z.still = true; }
      Z.flash = Math.max(0, Z.flash - dt * 0.5); const mc = g.live ? new THREE.Color(...g.ch).lerp(new THREE.Color(1, 1, 1), 0.25) : new THREE.Color(0.25, 0.35, 0.6);
      Z.lipM.color.copy(mc).lerp(Z.col, Z.flash); Z.neon.material.color.copy(mc).lerp(Z.col, Z.flash); Z.neon.material.opacity = (g.live ? 0.42 : 0.2) + 0.1 * Math.sin(t * 2 + ph) + Z.flash * 0.5;
      for (const l of Z.lamps) { l.material.color.set(0xfff4d8).lerp(Z.col, Z.flash); l.material.opacity = g.live ? 0.8 : 0.3; l.scale.setScalar(3.6 + Z.flash * 5 * (0.6 + 0.4 * Math.sin(t * 22))); }
    }
    for (const [k, Z] of W.st) if (!seen.has(k)) { scene.remove(Z.root); Z.crowd.dispose(); Z.ftex.dispose(); W.st.delete(k); }
  };
  W.score = (key, col, big, side) => { const Z = W.st.get(key); if (!Z) return; if (side == null) Z.ex[0] = Z.ex[1] = 1.3; else Z.ex[side ? 1 : 0] = big ? 1.7 : 1; Z.flash = 1; Z.col = C3(col); W.punch = Math.max(W.punch, big ? 0.8 : 0.4); };
  W.cheer = (key, col) => { const Z = key && W.st.get(key); if (Z) { Z.ex[0] = Z.ex[1] = 1.6; Z.flash = 1; Z.col = C3(col); } W.punch = 1; };
  // above a stadium's roof, in screen pixels: where its fireworks go up
  W.topPx = (key, th = 0, up = 2) => { const Z = W.st.get(key); if (!Z) return null; const p = ring(th, 3.4); _v.set(p[0], 4.2 + up, p[1]); Z.S.localToWorld(_v); _v.project(cam); return [(_v.x * 0.5 + 0.5) * innerWidth, (-_v.y * 0.5 + 0.5) * innerHeight]; };
  W.frame = (t, dt, aspect) => {
    W.t = t; if (cam.aspect !== aspect) { cam.aspect = aspect; cam.updateProjectionMatrix(); }
    W.punch = Math.max(0, W.punch - dt * 0.9); const ang = Math.sin(t * 0.11) * 0.03 + Math.sin(t * 0.047) * 0.015, d = 15.4 * (1 - 0.03 * W.punch * W.punch);
    cam.position.set(Math.sin(ang) * d, 0.9 + Math.sin(t * 0.09) * 0.2, Math.cos(ang) * d); cam.lookAt(0, 0.55, 0); cam.updateMatrixWorld();
  };
  return W;
}
