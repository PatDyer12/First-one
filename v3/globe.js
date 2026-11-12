// V3's flight between stadiums: up out of one, across the globe along the great circle, down into the next
import * as THREE from "three";
const R = 5;
// where the home stadiums are (lat, lon)
export const SPOT = { ARI: [33.53, -112.26], ATL: [33.76, -84.4], BAL: [39.28, -76.62], BUF: [42.77, -78.79], CAR: [35.23, -80.85], CHI: [41.86, -87.62], CIN: [39.1, -84.52], CLE: [41.51, -81.7], DAL: [32.75, -97.09], DEN: [39.74, -105.02],
  DET: [42.34, -83.05], GB: [44.5, -88.06], HOU: [29.68, -95.41], IND: [39.76, -86.16], JAX: [30.32, -81.64], KC: [39.05, -94.48], LV: [36.09, -115.18], LAC: [33.95, -118.34], LAR: [33.95, -118.34], MIA: [25.96, -80.24], MIN: [44.97, -93.26],
  NE: [42.09, -71.26], NO: [29.95, -90.08], NYG: [40.81, -74.07], NYJ: [40.81, -74.07], PHI: [39.9, -75.17], PIT: [40.45, -80.02], SF: [37.4, -121.97], SEA: [47.6, -122.33], TB: [27.98, -82.5], TEN: [36.17, -86.77], WSH: [38.91, -76.86],
  // other leagues' cities that aren't NFL ones
  BOS: [42.37, -71.06], BKN: [40.68, -73.97], NY: [40.75, -73.99], NYK: [40.75, -73.99], NYR: [40.75, -73.99], NYI: [40.71, -73.73], NJ: [40.73, -74.17], TOR: [43.64, -79.38], MIL: [43.04, -87.92], ORL: [28.54, -81.38], CHA: [35.23, -80.84], WAS: [38.9, -77.02],
  OKC: [35.46, -97.52], SA: [29.43, -98.44], MEM: [35.14, -90.05], UTAH: [40.77, -111.9], UTA: [40.77, -111.9], POR: [45.53, -122.67], SAC: [38.58, -121.5], GS: [37.77, -122.39], PHX: [33.45, -112.07], LAL: [34.04, -118.27], LA: [34.04, -118.27], ANA: [33.81, -117.88],
  SJ: [37.33, -121.9], VGK: [36.1, -115.18], COL: [39.75, -105.01], STL: [38.63, -90.2], NSH: [36.16, -86.78], CBJ: [39.97, -83.01], MTL: [45.5, -73.57], OTT: [45.3, -75.93], WPG: [49.89, -97.14], EDM: [53.55, -113.5], CGY: [51.04, -114.05], VAN: [49.28, -123.11], FLA: [26.16, -80.33] };
const VENUE = [[/bernab/i, [40.45, -3.69]], [/wembley|tottenham|london/i, [51.55, -0.2]], [/allianz|munich|bayern/i, [48.22, 11.62]], [/frankfurt|deutsche bank/i, [50.07, 8.65]], [/azteca|banorte|mexico/i, [19.3, -99.15]], [/corinthians|s[aã]o paulo|maracan/i, [-23.55, -46.47]], [/melbourne|mcg/i, [-37.82, 144.98]], [/stade de france|paris/i, [48.92, 2.36]], [/croke|dublin/i, [53.36, -6.25]]];
export function spotOf(ab, venue) { for (const [re, p] of VENUE) if (re.test(venue || "")) return p; if (SPOT[ab]) return SPOT[ab]; let h = 0; for (const c of String(ab || "x")) h = (h * 31 + c.charCodeAt(0)) % 9973; return [31 + (h % 14), -118 + ((h * 7) % 44)]; }
const xyz = (ll, r = R) => { const ph = ((90 - ll[0]) * Math.PI) / 180, th = ((ll[1] + 180) * Math.PI) / 180; return new THREE.Vector3(-r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph), r * Math.sin(ph) * Math.sin(th)); };
const slerp = (a, b, t) => { const w = a.angleTo(b); if (w < 1e-4) return a.clone(); const s = Math.sin(w); return a.clone().multiplyScalar(Math.sin((1 - t) * w) / s).add(b.clone().multiplyScalar(Math.sin(t * w) / s)); };
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export function makeGlobe(base) {
  const G = { on: false }, scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(45, 16 / 9, 0.02, 200);
  const L = new THREE.TextureLoader(), day = L.load(base + "img/earth_atmos_2048.jpg"), night = L.load(base + "img/earth_lights_2048.png"); day.colorSpace = night.colorSpace = THREE.SRGBColorSpace; day.anisotropy = night.anisotropy = 8;
  const earth = new THREE.Mesh(new THREE.SphereGeometry(R, 96, 64), new THREE.MeshStandardMaterial({ map: day, color: 0xa9c0ee, emissiveMap: night, emissive: 0xffd9a0, emissiveIntensity: 1.5, roughness: 1, metalness: 0 })); scene.add(earth);
  scene.add(new THREE.AmbientLight(0x9fb8ff, 1.1)); const sun = new THREE.DirectionalLight(0xffffff, 1.9); scene.add(sun);
  const atm = new THREE.Mesh(new THREE.SphereGeometry(R * 1.045, 64, 48), new THREE.ShaderMaterial({ side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    vertexShader: "varying vec3 vN; void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: "varying vec3 vN; void main(){ float f = pow(0.72 - dot(vN, vec3(0.0, 0.0, 1.0)), 3.0); gl_FragColor = vec4(0.3, 0.6, 1.0, 1.0) * clamp(f, 0.0, 1.0) * 1.6; }" })); scene.add(atm);
  { const N = 1400, pos = new Float32Array(N * 3); for (let i = 0; i < N; i++) { const a = Math.random() * 6.283, e = Math.acos(2 * Math.random() - 1), r = 60 + Math.random() * 40; pos[i * 3] = Math.sin(e) * Math.cos(a) * r; pos[i * 3 + 1] = Math.cos(e) * r; pos[i * 3 + 2] = Math.sin(e) * Math.sin(a) * r; }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); scene.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 1.6, color: 0xbfd0ff, sizeAttenuation: false, transparent: true, opacity: 0.8 }))); }
  const dot = (() => { const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d"), g = x.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, "#fff"); g.addColorStop(0.25, "rgba(255,255,255,.6)"); g.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = g; x.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c); })();
  const mark = () => { const g = new THREE.Group(), s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); g.add(s); const r = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 48), new THREE.MeshBasicMaterial({ transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })); g.add(r); scene.add(g); return { g, s, r }; };
  const mA = mark(), mB = mark(); let arc = null;
  const arcM = new THREE.MeshBasicMaterial({ color: 0xffd66b, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending, depthWrite: false });
  const head = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: 0xfff1c0, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true })); scene.add(head);
  const place = (m, p, col) => { m.g.position.copy(p).multiplyScalar(1.004); m.g.lookAt(p.clone().multiplyScalar(2)); m.s.material.color.setRGB(col[0], col[1], col[2]); m.r.material.color.setRGB(col[0], col[1], col[2]); };
  // a: [lat, lon] or null (arriving from far off); b: [lat, lon]
  G.start = (a, b, ms, ca, cb) => {
    G.b = xyz(b).normalize(); G.a = a ? xyz(a).normalize() : xyz([b[0] + 14, b[1] + 46]).normalize(); if (G.a.angleTo(G.b) < 0.004) G.a = xyz([b[0] + 3, b[1] + 6]).normalize();
    G.w = G.a.angleTo(G.b); G.t0 = performance.now(); G.ms = ms; G.on = true; G.from = !!a; G.peak = 2.6 + G.w * 5.5;
    place(mA, G.a.clone().multiplyScalar(R), ca || [1, 1, 1]); place(mB, G.b.clone().multiplyScalar(R), cb || [1, 0.84, 0.42]); mA.g.visible = !!a;
    if (arc) { scene.remove(arc); arc.geometry.dispose(); } const pts = []; for (let i = 0; i <= 80; i++) { const t = i / 80; pts.push(slerp(G.a, G.b, t).multiplyScalar(R * (1.006 + Math.sin(t * Math.PI) * Math.min(0.09, G.w * 0.16)))); }
    arc = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 160, Math.max(0.006, G.w * 0.012), 6, false), arcM); arc.userData.pts = pts; scene.add(arc); G.n = arc.geometry.index.count;
  };
  G.stop = () => { G.on = false; };
  G.frame = (now, aspect) => {
    if (!G.on) return false; if (cam.aspect !== aspect) { cam.aspect = aspect; cam.updateProjectionMatrix(); }
    const p = Math.min(1, (now - G.t0) / G.ms), e = ease(p), dir = slerp(G.a, G.b, e), up = Math.sin(Math.PI * p), alt = 1.15 + Math.pow(up, 0.85) * G.peak;
    cam.position.copy(dir).multiplyScalar(R + alt);
    // looking straight down at the ends, out ahead along the route in the middle
    const ahead = slerp(G.a, G.b, Math.min(1, e + 0.12)).multiplyScalar(R), down = dir.clone().multiplyScalar(R), tgt = down.lerp(ahead, up * 0.75);
    const tan = G.b.clone().sub(G.a).normalize(), upv = tan.lerp(dir, up * 0.85).normalize(); cam.up.copy(upv); cam.lookAt(tgt);
    sun.position.copy(cam.position).add(new THREE.Vector3(3, 4, 2));
    arc.geometry.setDrawRange(0, Math.floor((G.n * Math.min(1, e * 1.05)) / 6) * 6); const hp = arc.userData.pts[Math.min(80, Math.round(e * 80))]; head.position.copy(hp); const hs = 0.05 + alt * 0.06; head.scale.set(hs, hs, 1);
    const t = now / 1000, ms2 = 0.02 + alt * 0.035; for (const [m, k] of [[mA, 0], [mB, 1.3]]) { m.s.scale.set(ms2 * 2.4, ms2 * 2.4, 1); const q = (t * 0.9 + k) % 1; m.r.scale.setScalar(ms2 * (0.5 + q * 2.4)); m.r.material.opacity = 1 - q; }
    earth.rotation.y = 0; return true;
  };
  G.scene = scene; G.cam = cam; G.p = (now) => (G.on ? Math.min(1, (now - G.t0) / G.ms) : 0);
  return G;
}
