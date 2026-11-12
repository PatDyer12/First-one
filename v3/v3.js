// Sweat Board V3: the TV display. The page's engine (bets, scores, grading, settling) keeps running underneath; this takes the
// screen: a lane per game (the score, then every bet riding on it with its live state and a meter), parlays with their legs,
// a background that moves with the room (each game glows in its colours, a score sends a ripple through it, the whole field
// leans green or red with how the room's doing), and the shows when a bet's placed, a leg hits, a bet cashes or dies (3D).
// ?v3demo runs it on made-up games and bets, no sign-in needed.
import * as THREE from "three";

const sb = window.__sb3, V = window.__v3, DEMO = /[?&]v3demo/.test(location.search);
let SR = null;   // the display lives in a shadow root: none of the page's own styles reach it
const $ = (s, r) => (r || SR).querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const hex = (h, d) => { const m = /^#?([0-9a-f]{6})$/i.exec(String(h || "").trim()); if (!m) return d || [0.3, 0.35, 0.45]; const n = parseInt(m[1], 16); return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; };
const lum = (c) => 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2];
// a team colour that shows on a dark screen (a near-black primary gives way to the alternate)
const teamCol = (t) => { const c = hex(t && t.col), a = hex(t && t.alt, c); const p = lum(c) < 0.12 && lum(a) > lum(c) ? a : c; const k = lum(p) < 0.18 ? 0.18 / Math.max(0.02, lum(p)) : 1; return p.map((v) => clamp(v * k + (k > 1 ? 0.05 : 0), 0, 1)); };
const css = (c) => `rgb(${c.map((v) => Math.round(v * 255)).join(",")})`;
const G = [0.21, 0.88, 0.54], R = [1, 0.33, 0.41], A = [1, 0.76, 0.28], GOLD = [1, 0.8, 0.25];

// ---------- where the data comes from: the page's engine, or the demo ----------
const demo = DEMO ? makeDemo() : null;
const X = demo || {
  bets: () => [...sb.S.bets.values()].filter((b) => b.status === "open"),
  games: () => [...sb.S.games.values()],
  gameOf: (sel) => sb.gameOf(sel), evalSel: (sel) => sb.evalSel(sel), legsOf: (b) => sb.legsOf(b),
  name: (b) => sb.personName(b), col: (b) => sb.personCol(b), key: (b) => sb.personKey(b), me: (b) => sb.isMe(b),
  people: () => { try { return sb.standings("day").map((p) => ({ k: p.k, name: p.name, col: p.col, net: p.net || 0, open: (p.open || []).length })); } catch (e) { return []; } },
  unit: () => sb.S.unit || 10,
};
const fOdds = (o) => (o > 0 ? "+" + o : String(o).replace("-", "−"));
const fU = (u, sign) => { const v = Math.round(Math.abs(u) * 100) / 100; return (sign ? (u > 0.004 ? "+" : u < -0.004 ? "−" : "") : "") + String(v) + "u"; };
const ppu = (o) => (o > 0 ? o / 100 : 100 / Math.abs(o || -110));
const SCALE = { NFL: 10, CFB: 12, NBA: 12, CBB: 12, NHL: 2, MLB: 3 };

// ---------- the model: what's on the board right now ----------
function cardOf(b) {
  const who = X.name(b), col = X.col(b), toWin = b.units * ppu(b.odds);
  const base = { id: b.id, b, who, col, odds: b.odds, units: b.units, toWin, me: X.me(b) };
  if (b.kind === "parlay") {
    const legs = X.legsOf(b).map((l) => { const g = l.sel ? X.gameOf(l.sel) : null, ev = l.ev; const live = !l.st && ev && !ev.fin ? (ev.res === "W" ? "lw" : ev.res === "L" ? "ll" : "le") : "";
      return { t: l.t, st: l.st || "", live, x: l.st === "hit" ? "Hit" : l.st === "miss" ? "Missed" : ev ? ev.txt : g ? (g.st === "pre" ? when(g.t) : "") : "", g }; });
    const hit = legs.filter((l) => l.st === "hit").length, dead = legs.some((l) => l.st === "miss"), down = legs.some((l) => l.live === "ll"), up = legs.some((l) => l.live === "lw");
    const cls = dead ? "lost" : hit === legs.length && legs.length ? "won" : down ? "l" : up ? "w" : hit ? "e" : "pre";
    const live = legs.some((l) => l.live);
    return Object.assign(base, { par: true, legs, cls, live, pick: `${legs.length}-leg parlay`, tx: dead ? "Dead" : `${hit}/${legs.length} legs in` + (live ? " · live" : ""), heat: live ? 2 : hit ? 1 : 0 });
  }
  const sel = b.sel || null, g = sel ? X.gameOf(sel) : null, ev = sel && g ? X.evalSel(sel) : null;
  let cls = "pre", tx = g ? (g.st === "pre" ? when(g.t) : "") : "Open", p = 0.5, fill = false, sweat = false;
  if (ev) {
    cls = ev.fin ? (ev.res === "W" ? "won" : ev.res === "L" ? "lost" : "e") : ev.res === "W" ? "w" : ev.res === "L" ? "l" : "e"; tx = ev.txt;
    if (ev.v != null && ev.l != null) { fill = true; const tgt = Math.floor(ev.l) + 1; p = sel.s === "u" ? clamp(1 - ev.v / tgt, 0, 1) : clamp(ev.v / tgt, 0, 1); }
    else { const sc = SCALE[g.sport] || 10; p = 0.5 + 0.5 * Math.tanh((ev.m || 0) / sc); sweat = !ev.fin && g.st === "in" && Math.abs(ev.m || 0) <= sc * 0.35 && done(g) > 0.7; }
  }
  return Object.assign(base, { sel, g, ev, cls, tx, p, fill, sweat, pick: b.pick, live: !!(g && g.st === "in"), heat: g && g.st === "in" ? 2 + (sweat ? 1 : 0) : 0 });
}
const when = (t) => { const d = new Date(t), n = new Date(); const tm = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }); return d.toDateString() === n.toDateString() ? tm : d.toLocaleDateString([], { weekday: "short" }) + " " + tm; };
const done = (g) => { try { return demo ? demo.done(g) : sb.gameDone(g); } catch (e) { return 0; } };
function model() {
  const cards = X.bets().map((b) => { try { return cardOf(b); } catch (e) { return null; } }).filter(Boolean);
  const lanes = new Map(), pars = [], loose = [];
  for (const c of cards) { if (c.par) pars.push(c); else if (c.g) { if (!lanes.has(c.g.id)) lanes.set(c.g.id, { k: "g" + c.g.id, g: c.g, cards: [] }); lanes.get(c.g.id).cards.push(c); } else loose.push(c); }
  const rank = (g) => (g.st === "in" ? 0 : g.st === "pre" ? 1 : 2);
  const L = [...lanes.values()].sort((x, y) => rank(x.g) - rank(y.g) || (x.g.st === "in" ? Math.max(...y.cards.map((c) => c.heat)) - Math.max(...x.cards.map((c) => c.heat)) : 0) || x.g.t - y.g.t || (x.g.id < y.g.id ? -1 : 1));
  for (const l of L) l.cards.sort((x, y) => y.units * 1 - x.units * 1 || (x.id < y.id ? -1 : 1));
  pars.sort((x, y) => y.heat - x.heat || y.toWin - x.toWin || (x.id < y.id ? -1 : 1));
  const liveL = L.filter((l) => l.g.st === "in"), restL = L.filter((l) => l.g.st !== "in");
  const out = [...liveL]; if (pars.length) out.push({ k: "par", tag: ["Parlays", `${pars.length} riding`], cards: pars }); out.push(...restL); if (loose.length) out.push({ k: "loose", tag: ["Other bets", "Not on a game"], cards: loose });
  const risk = cards.reduce((a, c) => a + c.units, 0), toWin = cards.reduce((a, c) => a + c.toWin, 0);
  const live = cards.filter((c) => !c.par && c.ev && !c.ev.fin), up = live.filter((c) => c.ev.res === "W").length, dn = live.filter((c) => c.ev.res === "L").length;
  const hold = live.reduce((a, c) => a + (c.ev.res === "W" ? c.toWin : c.ev.res === "L" ? -c.units : 0), 0);
  return { lanes: out, n: cards.length, risk, toWin, up, dn, liveN: live.length, hold, mood: live.length ? clamp(hold / Math.max(1, live.reduce((a, c) => a + c.units, 0)), -1, 1) : 0 };
}

// ---------- the DOM ----------
let root, lanesEl, tickEl, pagesEl, stageEl, first = true;
const laneEls = new Map(), cardEls = new Map(), prevSc = new Map(), prevCls = new Map();
function build() {
  const out = document.createElement("style"); out.textContent = `body.v3on { background: #04060b !important; overflow: hidden !important; }
body.v3on > :not(#v3host):not(#v3gl):not(#v3fx):not(#toast):not(#updReady):not(script):not(style) { visibility: hidden !important; pointer-events: none !important; }
body.v3on > :not(#v3host):not(#v3gl):not(#v3fx) * { animation: none !important; transition: none !important; }
#v3gl, #v3fx { position: fixed; inset: 0; width: 100vw; height: 100vh; display: block; pointer-events: none; } #v3gl { z-index: 9000; } #v3fx { z-index: 9200; }
#v3host { position: fixed; inset: 0; z-index: 9100; }`; document.head.append(out);
  const host = document.createElement("div"); host.id = "v3host"; SR = host.attachShadow({ mode: "open" });
  const l = document.createElement("link"); l.rel = "stylesheet"; l.href = new URL("./v3.css", import.meta.url).href.replace(/\?.*$/, "") + "?v=" + ((sb && sb.BUILD) || Date.now()); SR.append(l);
  const gl = document.createElement("canvas"); gl.id = "v3gl"; const fx = document.createElement("canvas"); fx.id = "v3fx";
  root = document.createElement("div"); root.id = "v3";
  root.innerHTML = `<div class="v3-top"><div class="v3-brand">SWEAT <i>BOARD</i></div><div class="v3-clock" id="v3clock"></div><div class="v3-sum" id="v3sum"></div><div class="v3-ppl" id="v3ppl"></div><button class="v3-x" id="v3x" type="button">Exit V3</button></div>
    <div class="v3-main"><div class="v3-lanes" id="v3lanes"></div><div class="v3-pages" id="v3pages"></div></div><div class="v3-tick" id="v3tick"></div>`;
  stageEl = document.createElement("div"); stageEl.className = "v3-stage";
  SR.append(root, stageEl); document.body.append(gl, host, fx);
  lanesEl = $("#v3lanes"); tickEl = $("#v3tick"); pagesEl = $("#v3pages");
  $("#v3x").addEventListener("click", () => { try { localStorage.removeItem("sb-v3"); } catch (e) {} location.replace(location.pathname); });
  glInit(gl); fxInit(fx);
}
const gameHtml = (g) => {
  const row = (s) => { const t = g[s], o = g[s === "a" ? "h" : "a"], live = g.st !== "pre", lead = live && t.sc > o.sc, trail = live && t.sc < o.sc;
    const ball = g.st === "in" && g.sit && g.sit.pos && String(g.sit.pos) === String(t.id) ? `<i class="ball${g.sit.rz ? " rz" : ""}"></i>` : "";
    return `<div class="row${lead ? " lead" : trail ? " trail" : ""}">${t.lg ? `<img src="${esc(t.lg)}" alt="" referrerpolicy="no-referrer" onerror="this.style.visibility='hidden'">` : "<span></span>"}<span class="ab">${esc(t.ab)}${ball}</span><span class="sc num" data-s="${s}">${live ? esc(t.sc ?? "") : ""}</span></div>`; };
  const sit = g.st === "in" && g.sit && g.sit.dd ? g.sit.dd : g.st === "pre" ? g.net || g.sport : g.sport;
  return `${row("a")}${row("h")}<div class="st"><b>${esc(g.st === "pre" ? when(g.t) : g.st === "post" ? "Final" : g.d || "Live")}</b><span>${esc(sit || "")}</span></div>`;
};
const meter = (c) => { const p = Math.round(c.p * 1000) / 10; return c.fill ? `<div class="v3-m fill"><i style="left:0;width:${p}%"></i><b style="left:${p}%"></b></div>` : `<div class="v3-m"><i style="left:${Math.min(50, p)}%;width:${Math.abs(p - 50)}%"></i><b style="left:${p}%"></b></div>`; };
function cardHtml(c) {
  const hd = `<div class="hd"><span class="who">${esc(c.who)}</span><span>${fU(c.units)} to win ${fU(c.toWin)}</span><span class="od num">${fOdds(c.odds)}</span></div>`;
  if (c.par) return `${hd}<div class="v3-prog">${c.legs.map((l) => `<i class="${l.st || l.live}"></i>`).join("")}</div><div class="v3-legs">${c.legs.map((l, i) => `<div class="v3-leg ${l.st || l.live}" data-i="${i}"><span class="pip">${l.st === "hit" ? "✓" : l.st === "miss" ? "✕" : ""}</span><span class="t">${esc(l.t)}</span><span class="x">${esc(l.x || "")}</span></div>`).join("")}</div>`;
  return `${hd}<div class="pk">${esc(c.pick)}</div>${c.ev && c.g && c.g.st !== "pre" ? meter(c) : ""}<div class="stt"><span class="tx">${esc(c.tx || "")}</span></div>`;
}
function setHtml(el, h) { if (el.__h !== h) { el.__h = h; el.innerHTML = h; return true; } return false; }
// first, last, invert, play: whatever moved glides to where it is now
function flip(els, fn) {
  const a = new Map(); for (const e of els) if (e.isConnected && e.offsetParent) a.set(e, e.getBoundingClientRect());
  fn();
  for (const [e, r0] of a) { if (!e.isConnected || !e.offsetParent) continue; const r1 = e.getBoundingClientRect(), dx = r0.left - r1.left, dy = r0.top - r1.top; if (Math.abs(dx) + Math.abs(dy) < 2) continue;
    e.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: 650, easing: "cubic-bezier(.2,.8,.2,1)" }); }
}
let M = null, page = 0, pages = 1, pageAt = 0;
function render() {
  M = model();
  const n = M.n; root.style.setProperty("--k", n <= 6 ? 1.3 : n <= 10 ? 1.14 : n <= 16 ? 1 : n <= 24 ? 0.88 : 0.78);
  // header
  $("#v3clock").textContent = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  setHtml($("#v3sum"), n ? `<div class="v3-chip"><b>${n}</b><em>open</em></div><div class="v3-chip"><b>${fU(M.risk)}</b><em>riding</em></div>${M.liveN ? `<div class="v3-chip ${M.hold > 0.004 ? "g" : M.hold < -0.004 ? "r" : ""}"><b>${fU(M.hold, true)}</b><em>if it holds · ${M.up} up ${M.dn} down</em></div>` : `<div class="v3-chip"><b>${fU(M.toWin)}</b><em>to win</em></div>`}` : "");
  setHtml($("#v3ppl"), X.people().slice(0, 6).map((p) => `<div class="v3-p" data-k="${esc(p.k)}" style="--c:${esc(p.col)}"><span class="av">${esc(String(p.name || "?").slice(0, 1).toUpperCase())}</span><span class="nm">${esc(p.name)}</span><span class="nt num ${p.net > 0.004 ? "g" : p.net < -0.004 ? "r" : ""}">${fU(p.net, true)}</span>${p.open ? `<span class="op">${p.open} open</span>` : ""}</div>`).join(""));
  // lanes and cards, kept by key so they can glide and react instead of being redrawn
  const all = [...laneEls.values(), ...cardEls.values()];
  flip(all, () => {
    const seenL = new Set(), seenC = new Set();
    M.lanes.forEach((L, i) => {
      seenL.add(L.k); let el = laneEls.get(L.k);
      if (!el) { el = document.createElement("div"); el.className = "v3-lane" + (L.g ? "" : " plain"); el.innerHTML = `<div class="v3-g${L.g ? "" : " tag"}"></div><div class="v3-cards"></div>`; laneEls.set(L.k, el); }
      el.__L = L; const ge = el.firstChild, ce = el.lastChild;
      if (L.g) { const g = L.g, ca = teamCol(g.a), ch = teamCol(g.h); ge.style.setProperty("--ca", css(ca)); ge.style.setProperty("--ch", css(ch)); ge.classList.toggle("live", g.st === "in"); setHtml(ge, gameHtml(g)); el.__col = [ca, ch];
        const k = g.id, was = prevSc.get(k), now = [g.a.sc, g.h.sc]; if (was && g.st !== "pre") ["a", "h"].forEach((s, j) => { if (now[j] != null && was[j] != null && now[j] > was[j]) scored(el, s, j ? ch : ca, now[j] - was[j]); }); prevSc.set(k, now);
      } else setHtml(ge, `<b>${esc(L.tag[0])}</b><small>${esc(L.tag[1])}</small>`);
      if (lanesEl.children[i] !== el) lanesEl.insertBefore(el, lanesEl.children[i] || null);
      L.cards.forEach((c, j) => {
        seenC.add(c.id); let x = cardEls.get(c.id);
        if (!x) { x = document.createElement("div"); cardEls.set(c.id, x); if (!first) { x.__born = 1; } }
        x.__c = c; x.className = `v3-c ${c.cls}${c.par ? " par" : ""}${c.sweat ? " sweat" : ""}`; x.style.setProperty("--c", c.col); setHtml(x, cardHtml(c));
        if (x.__born === 1) { x.__born = 2; x.classList.add("born"); setTimeout(() => x.classList.remove("born"), 950); }
        const pc = prevCls.get(c.id), side = (k) => (k === "w" || k === "won" ? 1 : k === "l" || k === "lost" ? -1 : 0); prevCls.set(c.id, c.cls);
        if (pc && side(pc) !== side(c.cls) && side(c.cls) && !first) turned(x, side(c.cls) > 0);
        if (ce.children[j] !== x) ce.insertBefore(x, ce.children[j] || null);
      });
    });
    for (const [k, el] of laneEls) if (!seenL.has(k)) { el.remove(); laneEls.delete(k); }
    for (const [k, el] of cardEls) if (!seenC.has(k)) { el.remove(); cardEls.delete(k); prevCls.delete(k); }
    paginate();
  });
  let em = $(".v3-empty"); if (!M.lanes.length) { if (!em) { em = document.createElement("div"); em.className = "v3-empty"; em.innerHTML = "No open bets<small>Add one from your phone and it lands here</small>"; lanesEl.append(em); } } else if (em) em.remove();
  ticker(); first = false;
}
// more lanes than the screen holds: pages of them, the live games first, turning every so often
function paginate() {
  const H = lanesEl.clientHeight, gap = parseFloat(getComputedStyle(lanesEl).rowGap) || 0, els = [...lanesEl.children].filter((e) => e.classList.contains("v3-lane"));
  for (const e of els) e.classList.remove("off");
  let pg = 0, used = 0; const of = [];
  for (const e of els) { const h = e.offsetHeight; if (used && used + gap + h > H) { pg++; used = 0; } of.push(pg); used += (used ? gap : 0) + h; }
  pages = pg + 1; if (page >= pages) page = 0;
  if (pages > 1 && Date.now() - pageAt > 14000) { if (pageAt) page = (page + 1) % pages; pageAt = Date.now(); }
  els.forEach((e, i) => e.classList.toggle("off", of[i] !== page));
  setHtml(pagesEl, pages > 1 ? Array.from({ length: pages }, (_, i) => `<i class="${i === page ? "on" : ""}"></i>`).join("") : "");
}
function ticker() {
  const inLane = new Set(M.lanes.filter((l) => l.g).map((l) => l.g.id)), now = Date.now();
  const gs = X.games().filter((g) => !inLane.has(g.id) && g.a && g.h && (g.st === "in" || (g.st === "post" && now - g.t < 8 * 3600e3) || (g.st === "pre" && g.t - now < 10 * 3600e3 && g.t > now - 3600e3))).sort((x, y) => (x.st === "in" ? 0 : 1) - (y.st === "in" ? 0 : 1) || x.t - y.t).slice(0, 24);
  const one = gs.map((g) => `<span class="${g.st}">${esc(g.a.ab)} <b class="num">${g.st === "pre" ? "" : esc(g.a.sc ?? "")}</b> · ${esc(g.h.ab)} <b class="num">${g.st === "pre" ? "" : esc(g.h.sc ?? "")}</b><em>${esc(g.st === "pre" ? when(g.t) : g.st === "post" ? "Final" : g.d || "")}</em></span>`).join("");
  const sig = gs.map((g) => g.id).join(); if (tickEl.__sig !== sig) { tickEl.__sig = sig; tickEl.innerHTML = gs.length ? `<div class="run" style="--d:${Math.max(30, gs.length * 7)}s">${one}${one}</div>` : ""; tickEl.style.visibility = gs.length ? "" : "hidden"; }
  else if (gs.length) { const sp = tickEl.querySelectorAll("span"), tmp = document.createElement("div"); tmp.innerHTML = one + one; [...tmp.children].forEach((n, i) => { if (sp[i] && sp[i].innerHTML !== n.innerHTML) { sp[i].innerHTML = n.innerHTML; sp[i].className = n.className; } }); }
}
const mid = (el) => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2, r]; };

// ---------- reactions on the board ----------
function scored(lane, side, col, pts) {
  const ge = lane.firstChild, [x, y] = mid(ge); lane.style.setProperty("--sc", css(col));
  lane.classList.remove("scored"); void lane.offsetWidth; lane.classList.add("scored"); setTimeout(() => lane.classList.remove("scored"), 1500);
  setTimeout(() => { const s = ge.querySelector(`.sc[data-s="${side}"]`); if (s) { s.classList.add("flip"); setTimeout(() => s.classList.remove("flip"), 950); } }, 0);
  ripple(x, y, col, pts >= 6 ? 1.3 : 0.8); sparks(x, y, col, pts >= 6 ? 90 : 40, 1); gl.surge = Math.min(1.5, gl.surge + 0.6);
}
function turned(el, good) { if (!el.isConnected || !el.offsetParent) return; el.classList.add("turn"); setTimeout(() => el.classList.remove("turn"), 950); const [x, y] = mid(el); ripple(x, y, good ? G : R, 0.5); sparks(x, y, good ? G : R, 26, 0.7); }

// ---------- the background: one shader the whole board feeds ----------
const gl = { r: null, mat: null, mood: 0, surge: 0, rip: [], pts: null };
const N_EM = 10, N_RIP = 5;
function glInit(cv) {
  const r = new THREE.WebGLRenderer({ canvas: cv, antialias: false, alpha: false, powerPreference: "high-performance" }); r.setPixelRatio(1); gl.r = r;
  gl.scene = new THREE.Scene(); gl.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  gl.mat = new THREE.ShaderMaterial({ depthTest: false, uniforms: { uT: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) }, uMood: { value: 0 }, uSurge: { value: 0 }, uFlash: { value: new THREE.Vector4(1, 1, 1, 0) },
      uEm: { value: Array.from({ length: N_EM }, () => new THREE.Vector4(0, 0, 0, 0)) }, uEmC: { value: Array.from({ length: N_EM }, () => new THREE.Vector3()) },
      uRip: { value: Array.from({ length: N_RIP }, () => new THREE.Vector4(0, 0, -99, 0)) }, uRipC: { value: Array.from({ length: N_RIP }, () => new THREE.Vector3()) } },
    vertexShader: "void main(){ gl_Position = vec4(position.xy, 0.0, 1.0); }",
    fragmentShader: `precision highp float;
uniform float uT, uMood, uSurge; uniform vec2 uRes; uniform vec4 uFlash; uniform vec4 uEm[${N_EM}]; uniform vec3 uEmC[${N_EM}]; uniform vec4 uRip[${N_RIP}]; uniform vec3 uRipC[${N_RIP}];
float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * n(p); p = p * 2.03 + 11.7; a *= 0.5; } return s; }
void main(){
  vec2 px = gl_FragCoord.xy, uv = px / uRes; float asp = uRes.x / uRes.y; vec2 q = vec2(uv.x * asp, uv.y);
  float t = uT * (0.05 + 0.05 * uSurge);
  // slow curtains of light, bent by a second field
  vec2 w = q * 1.3 + vec2(fbm(q * 1.1 + t), fbm(q * 1.1 - t + 4.0)) * 0.9;
  float f = fbm(w + vec2(t * 0.7, -t * 0.4)), band = smoothstep(0.42, 0.78, f);
  vec3 cool = vec3(0.07, 0.12, 0.3), good = vec3(0.04, 0.34, 0.2), bad = vec3(0.4, 0.06, 0.1);
  vec3 tone = mix(cool, uMood > 0.0 ? good : bad, min(1.0, abs(uMood)) * 0.85);
  vec3 c = vec3(0.012, 0.018, 0.035) + tone * band * (0.5 + 0.5 * uSurge) + tone * 0.12;
  // a floor of lines running off to the horizon, drifting toward you
  float hz = 0.36; if (uv.y < hz) { float d = (hz - uv.y) / hz, z = 1.0 / max(0.02, d); vec2 g = vec2((uv.x - 0.5) * asp * z * 1.6, z + uT * (0.35 + 0.5 * uSurge));
    float ln = max(smoothstep(0.94, 1.0, abs(fract(g.x) * 2.0 - 1.0)), smoothstep(0.92, 1.0, abs(fract(g.y) * 2.0 - 1.0))); c += tone * ln * d * 1.5 * (0.5 + uSurge); }
  // every game on the board glows where it sits, in its own colours
  for (int i = 0; i < ${N_EM}; i++) { vec4 e = uEm[i]; if (e.z <= 0.0) continue; vec2 dl = (px - e.xy) / uRes.y; dl.x *= 0.55; float d2 = dot(dl, dl);
    c += uEmC[i] * e.z * exp(-d2 / (e.w * e.w)) * (0.8 + 0.2 * sin(uT * 1.7 + float(i) * 2.1)); }
  // a score, a bet turning, a win: rings running out through the field
  for (int i = 0; i < ${N_RIP}; i++) { vec4 rp = uRip[i]; float age = uT - rp.z; if (age < 0.0 || age > 2.6) continue; float d = length((px - rp.xy) / uRes.y), rad = age * 0.75;
    float ring = exp(-pow((d - rad) * 16.0, 2.0)) * (1.0 - age / 2.6); c += uRipC[i] * ring * rp.w * 1.6; }
  c += uFlash.rgb * uFlash.a * (0.35 + 0.65 * band);
  float vg = smoothstep(1.25, 0.35, length((uv - 0.5) * vec2(1.15, 1.0))); c *= 0.55 + 0.45 * vg;
  c += (h(px + uT) - 0.5) * 0.012;
  gl_FragColor = vec4(c, 1.0);
}` });
  gl.scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), gl.mat));
  // light running along each live lane, from the score out across its bets
  const NP = 520, pos = new Float32Array(NP * 3), colr = new Float32Array(NP * 3), g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("color", new THREE.BufferAttribute(colr, 3));
  const tex = dotTex(); gl.pts = { NP, pos, col: colr, g, lane: new Int16Array(NP).fill(-1), u: new Float32Array(NP), v: new Float32Array(NP), sp: new Float32Array(NP) };
  for (let i = 0; i < NP; i++) { gl.pts.u[i] = Math.random(); gl.pts.v[i] = Math.random(); gl.pts.sp[i] = 0.5 + Math.random(); }
  gl.pscene = new THREE.Scene(); gl.pcam = new THREE.OrthographicCamera(0, 1, 1, 0, -1, 1);
  const pm = new THREE.PointsMaterial({ size: 7, map: tex, vertexColors: true, transparent: true, depthTest: false, blending: THREE.AdditiveBlending, sizeAttenuation: false });
  const P = new THREE.Points(g, pm); P.frustumCulled = false; gl.pscene.add(P); gl.pm = pm;
  r.autoClear = false;
}
function dotTex() { const c = document.createElement("canvas"); c.width = c.height = 64; const x = c.getContext("2d"), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.3, "rgba(255,255,255,.6)"); gr.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = gr; x.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c); }
function ripple(x, y, col, str) { gl.rip.push({ x, y, col, str, t: gl.t || 0 }); if (gl.rip.length > N_RIP) gl.rip.shift(); }
let flash = { c: [1, 1, 1], a: 0 };
function glFrame(t, dt) {
  const W = innerWidth, H = innerHeight, r = gl.r, u = gl.mat.uniforms; gl.t = t;
  if (gl.w !== W || gl.h !== H) { gl.w = W; gl.h = H; const k = W > 2600 ? 0.5 : W > 1400 ? 0.75 : 1; r.setSize(Math.round(W * k), Math.round(H * k), false); gl.k = k; fxSize(W, H); }
  const k = gl.k; u.uT.value = t; u.uRes.value.set(W * k, H * k);
  gl.mood += ((M ? M.mood : 0) - gl.mood) * Math.min(1, dt * 0.8); u.uMood.value = gl.mood; gl.surge = Math.max(0, gl.surge - dt * 0.35); u.uSurge.value = gl.surge;
  flash.a = Math.max(0, flash.a - dt * 0.9); u.uFlash.value.set(flash.c[0], flash.c[1], flash.c[2], flash.a);
  // the lanes on screen are the lights
  const lanes = [...laneEls.values()].filter((e) => e.__L && e.__L.g && !e.classList.contains("off") && e.isConnected);
  for (let i = 0; i < N_EM; i++) { const e = lanes[i >> 1], em = u.uEm.value[i], ec = u.uEmC.value[i];
    if (!e) { em.z = 0; continue; } const g = e.__L.g, rr = e.firstChild.getBoundingClientRect(), side = i & 1, c = e.__col[side], live = g.st === "in";
    em.set((rr.left + rr.width * (side ? 0.72 : 0.28)) * k, (H - (rr.top + rr.height / 2)) * k, live ? 0.22 : 0.07, live ? 0.2 : 0.14); ec.set(c[0], c[1], c[2]); }
  for (let i = 0; i < N_RIP; i++) { const p = gl.rip[i], rp = u.uRip.value[i]; if (!p) { rp.z = -99; continue; } rp.set(p.x * k, (H - p.y) * k, p.t, p.str); u.uRipC.value[i].set(p.col[0], p.col[1], p.col[2]); }
  // the streams
  const P = gl.pts, liveL = lanes.filter((e) => e.__L.g.st === "in"), rects = liveL.map((e) => [e.firstChild.getBoundingClientRect(), e.getBoundingClientRect(), e.__col, e.__L.cards]);
  for (let i = 0; i < P.NP; i++) {
    const li = liveL.length ? i % Math.max(liveL.length, 4) : -1, L = rects[li];
    if (!L) { P.pos[i * 3] = -9; P.pos[i * 3 + 1] = -9; continue; }
    P.u[i] += dt * 0.11 * P.sp[i] * (1 + gl.surge); if (P.u[i] > 1) { P.u[i] -= 1; P.v[i] = Math.random(); }
    const x0 = L[0].right, x1 = L[1].right, uu = P.u[i], x = x0 + (x1 - x0) * uu, y = L[1].top + L[1].height * (0.12 + 0.76 * P.v[i]) + Math.sin(uu * 9 + i) * 5;
    P.pos[i * 3] = x / W; P.pos[i * 3 + 1] = 1 - y / H; const c = L[2][i & 1], a = Math.sin(uu * Math.PI) * 0.5; P.col[i * 3] = c[0] * a; P.col[i * 3 + 1] = c[1] * a; P.col[i * 3 + 2] = c[2] * a;
  }
  P.g.attributes.position.needsUpdate = true; P.g.attributes.color.needsUpdate = true; gl.pm.size = Math.max(4, 7 * (W / 1920) * k);
  r.clear(); r.render(gl.scene, gl.cam); r.render(gl.pscene, gl.pcam);
}

// ---------- the show layer: 3D over the board (coins, shards, sparks, rings) ----------
const fx = { r: null, coins: [], shards: [], sp: null, rings: [] };
const CAM_Z = 12, FOV = 38;
function fxInit(cv) {
  const r = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true, premultipliedAlpha: true, powerPreference: "high-performance" }); r.setPixelRatio(1); r.setClearColor(0x000000, 0); fx.r = r;
  fx.scene = new THREE.Scene(); fx.cam = new THREE.PerspectiveCamera(FOV, 16 / 9, 0.1, 100); fx.cam.position.z = CAM_Z;
  fx.scene.add(new THREE.AmbientLight(0xfff0d0, 0.9)); const d1 = new THREE.DirectionalLight(0xffffff, 2.6); d1.position.set(3, 6, 8); const d2 = new THREE.DirectionalLight(0xffb040, 1.4); d2.position.set(-6, -2, 5); fx.scene.add(d1, d2);
  // coins: one mesh, hundreds of them
  const NC = 520, cg = new THREE.CylinderGeometry(0.2, 0.2, 0.045, 28); cg.rotateX(Math.PI / 2);
  const face = (() => { const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d"); const g = x.createRadialGradient(46, 40, 6, 64, 64, 64); g.addColorStop(0, "#fff3b0"); g.addColorStop(0.5, "#f2b824"); g.addColorStop(1, "#b97a08"); x.fillStyle = g; x.fillRect(0, 0, 128, 128);
    x.strokeStyle = "#8a5a05"; x.lineWidth = 7; x.beginPath(); x.arc(64, 64, 52, 0, 7); x.stroke(); x.fillStyle = "#7a4f04"; x.font = "900 76px Georgia, serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("$", 64, 70); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
  const side = new THREE.MeshStandardMaterial({ color: 0xd99a14, metalness: 0.75, roughness: 0.3, emissive: 0x3a2400 }), cap = new THREE.MeshStandardMaterial({ map: face, metalness: 0.55, roughness: 0.32, emissive: 0x2a1a00 });
  fx.coinM = new THREE.InstancedMesh(cg, [side, cap, cap], NC); fx.coinM.count = 0; fx.coinM.frustumCulled = false; fx.scene.add(fx.coinM); fx.NC = NC;
  // shards: what's left of a losing ticket
  const NS = 260, sg = new THREE.TetrahedronGeometry(0.16); sg.scale(1.6, 1, 0.25);
  fx.shardM = new THREE.InstancedMesh(sg, new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.2, roughness: 0.5, flatShading: true }), NS); fx.shardM.count = 0; fx.shardM.frustumCulled = false; fx.shardM.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(NS * 3), 3); fx.scene.add(fx.shardM); fx.NS = NS;
  // sparks
  const NSP = 2600, pos = new Float32Array(NSP * 3), col = new Float32Array(NSP * 3), g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const P = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.16, map: dotTex(), vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })); P.frustumCulled = false; fx.scene.add(P);
  fx.sp = { N: NSP, pos, col, g, vel: new Float32Array(NSP * 3), life: new Float32Array(NSP), max: new Float32Array(NSP), base: new Float32Array(NSP * 3), i: 0, grav: new Float32Array(NSP) };
  fx.ringG = new THREE.RingGeometry(0.972, 1, 128);
}
function fxSize(W, H) { fx.r.setSize(W, H, false); fx.cam.aspect = W / H; fx.cam.updateProjectionMatrix(); fx.hh = Math.tan((FOV * Math.PI) / 360) * CAM_Z; fx.hw = fx.hh * (W / H); }
const toW = (x, y) => [((x / innerWidth) * 2 - 1) * fx.hw, (1 - (y / innerHeight) * 2) * fx.hh];
function sparks(x, y, col, n, pow, opt) {
  const S = fx.sp, [wx, wy] = toW(x, y), o = opt || {};
  for (let k = 0; k < n; k++) { const i = S.i = (S.i + 1) % S.N, a = Math.random() * Math.PI * 2, e = Math.acos(2 * Math.random() - 1), v = (o.even ? 0.75 + 0.25 * Math.random() : Math.pow(Math.random(), 0.6)) * 5.5 * pow;
    S.pos[i * 3] = wx; S.pos[i * 3 + 1] = wy; S.pos[i * 3 + 2] = o.z || 0; S.vel[i * 3] = Math.cos(a) * Math.sin(e) * v; S.vel[i * 3 + 1] = Math.sin(a) * Math.sin(e) * v + (o.up || 0); S.vel[i * 3 + 2] = Math.cos(e) * v * 0.5;
    S.life[i] = S.max[i] = (o.life || 1.1) * (0.6 + 0.6 * Math.random()); S.grav[i] = o.grav ?? 2.5; const w = o.white && Math.random() < 0.3 ? 0.6 : 0; S.base[i * 3] = col[0] + (1 - col[0]) * w; S.base[i * 3 + 1] = col[1] + (1 - col[1]) * w; S.base[i * 3 + 2] = col[2] + (1 - col[2]) * w; }
}
function firework(x, y, col) { const [wx, wy] = [x, y]; sparks(wx, wy, col, 220, 1.5, { even: true, life: 1.7, grav: 1.6, white: true }); sparks(wx, wy, [1, 1, 1], 40, 0.5, { life: 0.5 }); ring(x, y, col, 2.4, 0.9); flash = { c: col, a: Math.max(flash.a, 0.25) }; }
function ring(x, y, col, size, life) { const [wx, wy] = toW(x, y), m = new THREE.Mesh(fx.ringG, new THREE.MeshBasicMaterial({ color: new THREE.Color(col[0], col[1], col[2]), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })); m.position.set(wx, wy, 0); fx.scene.add(m); fx.rings.push({ m, t: 0, life: life || 1, size: size || 3 }); }
function coins(x, y, n, pow) {
  const [wx, wy] = toW(x, y);
  for (let k = 0; k < n && fx.coins.length < fx.NC; k++) { const a = -Math.PI / 2 + (Math.random() - 0.5) * 2.5, v = (4 + Math.random() * 9) * pow;
    fx.coins.push({ p: [wx + (Math.random() - 0.5) * 0.6, wy + (Math.random() - 0.5) * 0.3, (Math.random() - 0.5) * 2], v: [Math.sin(a + Math.PI / 2) * v * 0.75, -Math.sin(a) * v, (Math.random() - 0.5) * 5], r: [Math.random() * 6, Math.random() * 6, Math.random() * 6], w: [(Math.random() - 0.5) * 16, (Math.random() - 0.5) * 16, (Math.random() - 0.5) * 8], s: 0.7 + Math.random() * 0.7, t: -k * 0.004, b: 0 }); }
}
function shards(rect, n) {
  for (let k = 0; k < n && fx.shards.length < fx.NS; k++) { const [wx, wy] = toW(rect.left + Math.random() * rect.width, rect.top + Math.random() * rect.height), red = Math.random() < 0.55;
    fx.shards.push({ p: [wx, wy, 0], v: [(Math.random() - 0.5) * 5, 1 + Math.random() * 4, (Math.random() - 0.3) * 6], r: [Math.random() * 6, Math.random() * 6, Math.random() * 6], w: [(Math.random() - 0.5) * 12, (Math.random() - 0.5) * 12, (Math.random() - 0.5) * 12], s: 0.6 + Math.random() * 1.2, t: 0, c: red ? [0.9, 0.16, 0.22] : [0.16, 0.19, 0.27] }); }
}
const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _e = new THREE.Euler(), _v = new THREE.Vector3(), _s = new THREE.Vector3(), _c = new THREE.Color();
function fxFrame(dt) {
  let busy = false; const floor = -fx.hh - 0.4;
  // coins: thrown, spinning, a bounce off the bottom of the screen, then gone
  for (let i = fx.coins.length - 1; i >= 0; i--) { const c = fx.coins[i]; c.t += dt; if (c.t < 0) continue; c.v[1] -= 15 * dt; for (let a = 0; a < 3; a++) { c.p[a] += c.v[a] * dt; c.r[a] += c.w[a] * dt; }
    if (c.p[1] < floor + 0.5 && c.v[1] < 0 && c.b < 1) { c.v[1] *= -0.42; c.b++; c.v[0] *= 0.7; } if (c.p[1] < floor - 1.5 || c.t > 9) fx.coins.splice(i, 1); }
  fx.coinM.count = fx.coins.length; fx.coins.forEach((c, i) => { _e.set(c.r[0], c.r[1], c.r[2]); _q.setFromEuler(_e); _v.set(c.p[0], c.p[1], c.p[2]); const s = c.t < 0 ? 0.0001 : c.s; _s.set(s, s, s); _m.compose(_v, _q, _s); fx.coinM.setMatrixAt(i, _m); });
  if (fx.coins.length) { fx.coinM.instanceMatrix.needsUpdate = true; busy = true; }
  for (let i = fx.shards.length - 1; i >= 0; i--) { const c = fx.shards[i]; c.t += dt; c.v[1] -= 13 * dt; for (let a = 0; a < 3; a++) { c.p[a] += c.v[a] * dt; c.r[a] += c.w[a] * dt; } if (c.p[1] < floor - 1 || c.t > 5) fx.shards.splice(i, 1); }
  fx.shardM.count = fx.shards.length; fx.shards.forEach((c, i) => { _e.set(c.r[0], c.r[1], c.r[2]); _q.setFromEuler(_e); _v.set(c.p[0], c.p[1], c.p[2]); _s.set(c.s, c.s, c.s); _m.compose(_v, _q, _s); fx.shardM.setMatrixAt(i, _m); _c.setRGB(c.c[0], c.c[1], c.c[2]); fx.shardM.setColorAt(i, _c); });
  if (fx.shards.length) { fx.shardM.instanceMatrix.needsUpdate = true; fx.shardM.instanceColor.needsUpdate = true; busy = true; }
  const S = fx.sp; let any = false;
  for (let i = 0; i < S.N; i++) { if (S.life[i] <= 0) continue; any = true; S.life[i] -= dt; const k = Math.max(0, S.life[i] / S.max[i]); S.vel[i * 3 + 1] -= S.grav[i] * dt; const dr = Math.pow(0.35, dt);
    for (let a = 0; a < 3; a++) { S.vel[i * 3 + a] *= dr; S.pos[i * 3 + a] += S.vel[i * 3 + a] * dt; S.col[i * 3 + a] = S.base[i * 3 + a] * k * k; } if (S.life[i] <= 0) S.pos[i * 3] = 999; }
  if (any || fx.spDirty) { S.g.attributes.position.needsUpdate = true; S.g.attributes.color.needsUpdate = true; busy = busy || any; fx.spDirty = any; }
  for (let i = fx.rings.length - 1; i >= 0; i--) { const r = fx.rings[i]; r.t += dt; const k = r.t / r.life; if (k >= 1) { fx.scene.remove(r.m); r.m.material.dispose(); fx.rings.splice(i, 1); continue; } const s = 0.2 + (1 - Math.pow(1 - k, 3)) * r.size; r.m.scale.set(s, s, 1); r.m.material.opacity = (1 - k) * (1 - k) * 0.8; busy = true; }
  if (busy || fx.wasBusy) fx.r.render(fx.scene, fx.cam); fx.wasBusy = busy;
}

// ---------- the shows ----------
const Q = []; let showing = false;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
function enqueue(fn) { Q.push(fn); if (!showing) nextShow(); }
async function nextShow() { const fn = Q.shift(); if (!fn) { showing = false; return; } showing = true; try { await fn(); } catch (e) { console.warn("v3 show", e); } cleanup(); await wait(250); nextShow(); }
function cleanup() { root.classList.remove("dim", "shake"); stageEl.classList.remove("on"); SR.querySelectorAll(".v3-ghost, .v3-bill").forEach((e) => e.remove()); }
// the card as it stood, lifted off the board
function ghostOf(b, cls) {
  const el = cardEls.get(b.id); let r, g;
  if (el && el.isConnected && el.offsetParent) { r = el.getBoundingClientRect(); g = el.cloneNode(true); el.style.visibility = "hidden"; }
  else { const c = (() => { try { return cardOf(b); } catch (e) { return null; } })(); g = document.createElement("div"); g.className = "v3-c" + (b.kind === "parlay" ? " par" : ""); g.style.setProperty("--c", X.col(b)); g.innerHTML = c ? cardHtml(c) : `<div class="pk">${esc(b.pick)}</div>`; const w = innerWidth * 0.26; r = { left: innerWidth / 2 - w / 2, top: innerHeight * 0.4, width: w, height: 0 }; }
  g.classList.remove("born", "turn", "sweat", "w", "l", "e", "pre", "won", "lost"); g.classList.add("v3-ghost", cls); g.style.left = r.left + "px"; g.style.top = r.top + "px"; g.style.width = r.width + "px";
  g.style.setProperty("--u", getComputedStyle(root).getPropertyValue("--u")); g.style.setProperty("--k", getComputedStyle(root).getPropertyValue("--k")); for (const v of ["--g", "--r", "--a", "--ink", "--dim"]) g.style.setProperty(v, getComputedStyle(root).getPropertyValue(v)); g.style.color = "#f4f7fb"; g.style.fontFamily = "Inter, system-ui, sans-serif";
  SR.append(g); const rr = g.getBoundingClientRect(); return { g, r: rr };
}
const bill = (pos, html, col) => { const d = document.createElement("div"); d.className = "v3-bill " + pos; d.style.setProperty("--bc", col); d.style.setProperty("--u", getComputedStyle(root).getPropertyValue("--u")); d.innerHTML = html; SR.append(d); requestAnimationFrame(() => requestAnimationFrame(() => d.classList.add("in"))); return d; };
const usd = (n) => "$" + (Math.abs(n * X.unit()) >= 100 ? Math.round(Math.abs(n * X.unit())) : (Math.round(Math.abs(n * X.unit()) * 100) / 100).toFixed(2).replace(/\.00$/, ""));
async function showWin(b, n) {
  const par = b.kind === "parlay", dollars = Math.abs(n * X.unit()), tier = dollars >= 150 || (par && b.odds >= 800) ? 3 : dollars >= 40 || par || b.odds >= 250 ? 2 : 1, who = X.name(b), me = X.me(b), col = hex(X.col(b), GOLD);
  const { g, r } = ghostOf(b, "won"), cx = innerWidth / 2, cy = innerHeight * 0.5, sc = Math.min(2.1, (innerWidth * (par ? 0.44 : 0.38)) / r.width);
  root.classList.add("dim"); stageEl.classList.add("on"); gl.surge = 1.5; ripple(r.left + r.width / 2, r.top + r.height / 2, G, 1.2);
  // off the board, a full turn in the air, down on centre stage
  const dx = cx - (r.left + r.width / 2), dy = cy - (r.top + r.height / 2);
  await g.animate([{ transform: "perspective(1400px) translate(0,0) rotateY(0) scale(1)" }, { transform: `perspective(1400px) translate(${dx * 0.5}px, ${dy * 0.5 - innerHeight * 0.08}px) rotateY(200deg) scale(${sc * 0.8})`, offset: 0.55 }, { transform: `perspective(1400px) translate(${dx}px, ${dy}px) rotateY(360deg) scale(${sc})` }], { duration: 850, easing: "cubic-bezier(.3,.1,.2,1)", fill: "forwards" }).finished;
  // the hit: stamp, flash, a ring, and the money goes up
  const st = document.createElement("div"); st.className = "v3-stamp"; st.textContent = b.status === "cashout" ? "CASHED OUT" : "CASHED"; g.append(st); requestAnimationFrame(() => st.classList.add("in"));
  flash = { c: tier > 1 ? GOLD : G, a: 0.55 + tier * 0.12 }; ring(cx, cy, GOLD, 5 + tier * 2, 1.1); ring(cx, cy, G, 3 + tier, 0.8); sparks(cx, cy, GOLD, 160 + tier * 120, 1.2 + tier * 0.25, { white: true, life: 1.3 });
  coins(cx, cy + innerHeight * 0.16, clamp(Math.round(50 + dollars * 2.2), 60, tier === 3 ? 480 : 260), 0.85 + tier * 0.12);
  if (tier >= 2) { root.classList.add("shake"); setTimeout(() => root.classList.remove("shake"), 520); }
  bill("top", `<div class="k">${esc(me ? (par ? "Parlay hits" : "Winner") : who + (par ? " hits the parlay" : " cashes"))}</div>`, css(col));
  bill("bot", `<div class="big num">+${usd(n)}</div><div class="sub">${fU(n, true)} · ${esc(fOdds(b.odds))}${par ? ` · ${(b.legs || []).length} legs` : ""}</div>`, css(GOLD));
  // the bigger it is, the longer the sky stays lit
  const hold = tier === 3 ? 6200 : tier === 2 ? 4200 : 2900, t0 = Date.now(); let k = 0;
  while (Date.now() - t0 < hold) { await wait(tier === 3 ? 480 : 700); if (tier >= 2) { firework(innerWidth * (0.12 + 0.76 * Math.random()), innerHeight * (0.12 + 0.4 * Math.random()), [GOLD, G, col, [0.5, 0.75, 1]][k++ % 4]); } if (tier === 3 && k % 3 === 0) coins(innerWidth * (0.2 + 0.6 * Math.random()), innerHeight * 0.3, 60, 0.7); }
  // and it goes home to whoever's it is
  const chip = [...SR.querySelectorAll("#v3ppl .v3-p")].find((e) => e.dataset.k === String(X.key(b))), cr = chip ? chip.getBoundingClientRect() : { left: innerWidth - 200, top: 20, width: 100, height: 40 };
  SR.querySelectorAll(".v3-bill").forEach((e) => (e.style.opacity = "0", e.style.transition = "opacity .3s")); stageEl.classList.remove("on"); root.classList.remove("dim");
  const gx = cr.left + cr.width / 2 - (r.left + r.width / 2), gy = cr.top + cr.height / 2 - (r.top + r.height / 2);
  await g.animate([{ transform: `perspective(1400px) translate(${dx}px, ${dy}px) rotateY(360deg) scale(${sc})`, opacity: 1 }, { transform: `perspective(1400px) translate(${gx}px, ${gy}px) rotateY(360deg) scale(.12)`, opacity: 0.2 }], { duration: 620, easing: "cubic-bezier(.5,0,.8,.4)", fill: "forwards" }).finished;
  if (chip) { chip.classList.remove("pop"); void chip.offsetWidth; chip.classList.add("pop"); sparks(cr.left + cr.width / 2, cr.top + cr.height / 2, hex(X.col(b), GOLD), 50, 0.6); }
}
async function showLoss(b, n) {
  const me = X.me(b), { g, r } = ghostOf(b, "lost"), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  flash = { c: R, a: me ? 0.5 : 0.3 }; ripple(cx, cy, R, 1); gl.surge = 0.8;
  const st = document.createElement("div"); st.className = "v3-stamp r"; st.textContent = "DEAD"; g.append(st); requestAnimationFrame(() => st.classList.add("in"));
  await g.animate([{ transform: "translate(0,0) rotate(0)" }, { transform: "translate(-9px,3px) rotate(-1.2deg)" }, { transform: "translate(8px,-3px) rotate(1deg)" }, { transform: "translate(-5px,2px) rotate(-.6deg)" }, { transform: "translate(0,0) scale(1.06)" }], { duration: 620 }).finished;
  await wait(me ? 650 : 300);
  // it breaks where it stands
  shards(r, clamp(Math.round((r.width * r.height) / 1500), 50, 170)); sparks(cx, cy, R, 80, 0.9, { life: 0.8 }); ring(cx, cy, R, 3, 0.7);
  g.animate([{ opacity: 1, transform: "scale(1.06)", filter: "none" }, { opacity: 0, transform: "scale(1.25)", filter: "blur(6px) brightness(2)" }], { duration: 260, fill: "forwards" });
  if (me) { const d = bill("bot", `<div class="sub" style="color:#ff8c98">${esc(b.kind === "parlay" ? "Parlay" : b.pick)} · ${fU(n, true)}</div>`, css(R)); await wait(1500); d.style.opacity = "0"; } else await wait(700);
}
function note(b, word) {
  const d = document.createElement("div"); d.className = "v3-note"; d.style.setProperty("--c", X.col(b)); d.style.setProperty("--u", getComputedStyle(root).getPropertyValue("--u"));
  d.innerHTML = `<b>${esc(X.name(b))}</b> ${esc(word)} · ${esc(b.kind === "parlay" ? (b.legs || []).length + "-leg parlay" : b.pick)} <em class="num">${esc(fOdds(b.odds))} · ${fU(b.units)}</em>`;
  SR.append(d); requestAnimationFrame(() => requestAnimationFrame(() => d.classList.add("in"))); setTimeout(() => { d.classList.remove("in"); setTimeout(() => d.remove(), 600); }, 4200);
}
// what the engine calls
V.settle = (b, o, n) => { if (o === "W") enqueue(() => showWin(b, n)); else if (o === "L") enqueue(() => showLoss(b, n)); else note(b, b.status === "cashout" ? "cashed out" : "pushed"); };
V.place = (b) => { note(b, "is on"); setTimeout(() => { const el = cardEls.get(b.id); if (el && el.offsetParent) { const [x, y] = mid(el); ripple(x, y, hex(X.col(b), A), 0.9); sparks(x, y, hex(X.col(b), A), 60, 0.8); ring(x, y, hex(X.col(b), A), 2.2, 0.8); } }, 700); };
V.leg = (b, i, st) => { setTimeout(() => { const el = cardEls.get(b.id), lg = el && el.querySelector(`.v3-leg[data-i="${i}"]`); if (!lg || !el.offsetParent) return; lg.classList.add("pop"); setTimeout(() => lg.classList.remove("pop"), 850);
  const [x, y] = mid(lg.querySelector(".pip")), c = st === "miss" ? R : G; sparks(x, y, c, 70, 0.8, { white: st !== "miss" }); ring(x, y, c, 1.6, 0.7); ripple(x, y, c, 0.7); turned(el, st !== "miss"); }, 600); };

// ---------- running ----------
let last = 0, on = false, tick = 0;
function setOn(v) { if (v === on) return; on = v; V.on = v; document.body.classList.toggle("v3on", v); for (const id of ["v3host", "v3gl", "v3fx"]) { const e = document.getElementById(id); if (e) e.style.display = v ? "" : "none"; } if (v) { first = true; render(); } }
function frame(now) {
  requestAnimationFrame(frame);
  const want = DEMO || (sb && sb.tv()); if (want !== on) setOn(want); if (!on || document.hidden) { last = now; return; }
  const dt = Math.min(0.05, (now - last) / 1000 || 0.016); last = now;
  if (demo) demo.step(dt);
  if (now - tick > 500) { tick = now; try { render(); } catch (e) { console.warn("v3 render", e); } }
  try { glFrame(now / 1000, dt); fxFrame(dt); } catch (e) { if (!frame.warned) { frame.warned = 1; console.warn("v3 gl", e); } }
}
build(); setOn(DEMO || (sb && sb.tv())); if (!on) for (const id of ["v3host", "v3gl", "v3fx"]) document.getElementById(id).style.display = "none";
requestAnimationFrame(frame);
window.__v3dbg = { model: () => M, win: (id) => { const b = X.bets().find((x) => x.id === id) || X.bets()[0]; if (b) V.settle(b, "W", b.units * ppu(b.odds)); }, loss: (id) => { const b = X.bets().find((x) => x.id === id) || X.bets()[0]; if (b) V.settle(b, "L", -b.units); }, demo };

// ---------- the demo: four games that play themselves, three people's bets ----------
function makeDemo() {
  const T = (ab, nm, col, alt) => ({ id: ab, ab, nm, col, alt, lg: `https://a.espncdn.com/i/teamlogos/nfl/500-dark/${ab.toLowerCase()}.png`, sc: 0 });
  const now = Date.now(), mk = (id, a, h, st, q, min) => ({ id, sport: "NFL", st, a, h, t: st === "pre" ? now + 95 * 60e3 : now - 3600e3, q, clk: min * 60, d: "", net: "NBC", sit: null });
  const games = [mk("g1", T("DET", "Lions", "#0076b6", "#b0b7bc"), T("KC", "Chiefs", "#e31837", "#ffb612"), "in", 2, 9), mk("g2", T("PHI", "Eagles", "#004c54", "#a5acaf"), T("DAL", "Cowboys", "#002a5c", "#b0b7bc"), "in", 3, 12), mk("g3", T("BUF", "Bills", "#00338d", "#d50a0a"), T("MIA", "Dolphins", "#008e97", "#fc4c02"), "in", 4, 6), mk("g4", T("GB", "Packers", "#204e32", "#ffb612"), T("CHI", "Bears", "#0b162a", "#c83803"), "pre", 0, 15)];
  games[0].a.sc = 10; games[0].h.sc = 14; games[1].a.sc = 17; games[1].h.sc = 13; games[2].a.sc = 24; games[2].h.sc = 23;
  const P = { me: ["You", "#e2c17e"], br: ["Brad", "#f2a65a"], ju: ["Julian", "#6cc4f5"] };
  let n = 0; const bet = (who, pick, odds, units, sel) => ({ id: "d" + ++n, who, pick, odds, units, sel, status: "open", kind: "straight", placedAt: now });
  const bets = new Map(), add = (b) => bets.set(b.id, b);
  add(bet("me", "Lions +3.5", -110, 2, { g: "g1", m: "sp", s: "a", l: 3.5 })); add(bet("br", "Chiefs ML", -180, 1, { g: "g1", m: "ml", s: "h" })); add(bet("ju", "Over 47.5", -110, 1, { g: "g1", m: "tot", s: "o", l: 47.5 }));
  add(bet("me", "Eagles ML", -135, 3, { g: "g2", m: "ml", s: "a" })); add(bet("ju", "Cowboys +2.5", -105, 1.5, { g: "g2", m: "sp", s: "h", l: 2.5 }));
  add(bet("br", "Bills −1.5", -110, 1, { g: "g3", m: "sp", s: "a", l: -1.5 })); add(bet("me", "Under 51.5", -110, 1, { g: "g3", m: "tot", s: "u", l: 51.5 })); add(bet("ju", "Dolphins ML", 120, 1, { g: "g3", m: "ml", s: "h" }));
  add(bet("br", "Packers −3", -115, 2, { g: "g4", m: "sp", s: "a", l: -3 })); add(bet("me", "Bears ML", 140, 1, { g: "g4", m: "ml", s: "h" }));
  add({ id: "p1", who: "me", kind: "parlay", odds: 650, units: 1, status: "open", pick: "4-leg parlay", legs: ["Lions ML", "Eagles ML", "Bills ML", "Packers ML"], legSel: [{ g: "g1", m: "ml", s: "a" }, { g: "g2", m: "ml", s: "a" }, { g: "g3", m: "ml", s: "a" }, { g: "g4", m: "ml", s: "a" }] });
  add({ id: "p2", who: "br", kind: "parlay", odds: 264, units: 0.5, status: "open", pick: "2-leg parlay", legs: ["Over 47.5 DET/KC", "Dolphins +1.5"], legSel: [{ g: "g1", m: "tot", s: "o", l: 47.5 }, { g: "g3", m: "sp", s: "h", l: 1.5 }] });
  const net = { me: 1.8, br: -1, ju: 0.9 }, G0 = (id) => games.find((g) => g.id === id);
  const label = (g) => (g.st === "post" ? "Final" : g.st === "pre" ? "" : g.q > 4 ? "OT" : `${Math.floor(g.clk / 60)}:${String(Math.floor(g.clk % 60)).padStart(2, "0")} - ${["1st", "2nd", "3rd", "4th"][g.q - 1]}`);
  const dn = (g) => (g.st === "post" ? 1 : g.st !== "in" ? 0 : Math.min(0.99, ((g.q - 1) * 900 + (900 - g.clk)) / 3600));
  const ev = (sel) => { const g = G0(sel.g); if (!g || g.st === "pre") return null; const a = g.a.sc, h = g.h.sc, diff = sel.s === "a" ? a - h : h - a, fin = g.st === "post"; let m, txt; const k = (v) => String(Math.round(Math.abs(v) * 10) / 10);
    if (sel.m === "ml") { m = diff; txt = m > 0 ? "Up " + k(m) : m < 0 ? "Down " + k(m) : "Tied"; } else if (sel.m === "sp") { m = diff + sel.l; txt = m > 0 ? "Covering by " + k(m) : m < 0 ? "Needs " + k(m) : "On the number"; }
    else { const t = a + h; if (sel.s === "o") { m = t - sel.l; if (m <= 0 && !fin) { const pace = t - sel.l * dn(g); txt = `Needs ${k(sel.l - t)} more · ${pace >= 0 ? "on pace" : "off pace"}`; m = pace; } else txt = "Over by " + k(m); } else { m = sel.l - t; txt = m > 0 ? k(m) + " to spare" : "Over by " + k(m); } }
    const res = m > 0 ? "W" : m < 0 ? "L" : "P"; if (fin) txt = "Final · " + (res === "W" ? "winner" : res === "L" ? "loser" : "push"); return { m, res, fin, txt, g }; };
  const legs = (b) => (b.legs || []).map((t, i) => { const sel = b.legSel[i], e = ev(sel); return { t, st: e && e.fin ? (e.res === "W" ? "hit" : "miss") : null, ev: e, sel }; });
  let acc = 0, placed = 0;
  const settle = (b, o) => { const nn = o === "W" ? b.units * ppu(b.odds) : -b.units; b.status = o === "W" ? "won" : "lost"; net[b.who] += nn; V.settle && V.settle(b, o, nn); bets.delete(b.id); };
  return {
    bets: () => [...bets.values()], games: () => games, gameOf: (sel) => G0(sel.g), evalSel: ev, legsOf: legs, done: dn,
    name: (b) => P[b.who][0], col: (b) => P[b.who][1], key: (b) => b.who, me: (b) => b.who === "me", unit: () => 15,
    people: () => Object.keys(P).map((k) => ({ k, name: P[k][0], col: P[k][1], net: net[k], open: [...bets.values()].filter((b) => b.who === k).length })).sort((x, y) => y.net - x.net),
    step(dt) {
      for (const g of games) { if (g.st === "in") { g.clk -= dt * 22; if (g.clk <= 0) { if (g.q >= 4 && g.a.sc !== g.h.sc) { g.st = "post"; g.sit = null; } else { g.q++; g.clk = 900; } } } else if (g.st === "pre" && g.t - Date.now() < 93.6 * 60e3) { g.st = "in"; g.q = 1; g.clk = 900; } g.d = label(g); }
      acc += dt; if (acc > 5.5) { acc = 0; const live = games.filter((g) => g.st === "in"); if (live.length) { const g = live[Math.floor(Math.random() * live.length)], s = Math.random() < 0.5 ? "a" : "h"; g[s].sc += Math.random() < 0.62 ? 7 : 3; g.sit = { pos: g[s === "a" ? "h" : "a"].id, dd: ["1st & 10", "2nd & 6", "3rd & 2", "1st & Goal"][Math.floor(Math.random() * 4)], rz: Math.random() < 0.3 }; } }
      // a finished game pays its bets, one at a time; a parlay when its last leg is in (or one's dead)
      if (!showing && !Q.length) for (const b of bets.values()) { if (b.kind === "parlay") { const L = legs(b); if (L.some((l) => l.st === "miss")) { settle(b, "L"); break; } if (L.every((l) => l.st === "hit")) { settle(b, "W"); break; } } else { const e = ev(b.sel); if (e && e.fin && e.res !== "P") { settle(b, e.res); break; } } }
      if (!placed && games[0].q >= 3) { placed = 1; const b = bet("ju", "Chiefs −2.5 live", 105, 2, { g: "g1", m: "sp", s: "h", l: -2.5 }); add(b); V.place && V.place(b); }
    },
  };
}
