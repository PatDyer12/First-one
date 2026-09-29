// Renders the notes HTML to a US Letter PDF + one PNG per page, and runs layout checks.
const path = require('path');
const fs = require('fs');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const ROOT = path.resolve(__dirname, '..');
const HTML = path.join(ROOT, 'geol211_exam2_notes.html');
const PNG_DIR = path.join(ROOT, 'pages');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 860, height: 1100 }, deviceScaleFactor: 2 });
  await page.goto('file://' + HTML);
  await page.evaluate(() => document.fonts.ready);

  // ---- checks
  const report = await page.evaluate(() => {
    const RULE0 = 96, GAP = 27, SIT = 1.5;
    const out = { baseline: [], overflow: [], tight: [], diagrams: [], pageOverflow: [] };
    document.querySelectorAll('.page').forEach((pg, pi) => {
      const pr = pg.getBoundingClientRect();
      pg.querySelectorAll('.ln').forEach(ln => {
        const n = +ln.dataset.line;
        const t = ln.querySelector('.t');
        // baseline probe
        const probe = document.createElement('span');
        probe.style.cssText = 'display:inline-block;width:0;height:0;vertical-align:baseline';
        t.appendChild(probe);
        const by = probe.getBoundingClientRect().top - pr.top;
        probe.remove();
        const want = RULE0 + GAP * (n - 1) - SIT;
        if (Math.abs(by - want) > 0.6) out.baseline.push({ page: pi + 1, line: n, by, want, text: t.textContent.slice(0, 40) });
        const avail = ln.clientWidth, used = t.getBoundingClientRect().width;
        if (used > avail + 0.5) out.overflow.push({ page: pi + 1, line: n, used: Math.round(used), avail, text: t.textContent });
        else if (!ln.classList.contains("tag") && !ln.classList.contains("idx") && used > avail * 0.93 && avail > 300)
          out.tight.push({ page: pi + 1, line: n, pct: Math.round(100 * used / avail), text: t.textContent });
        const r = ln.getBoundingClientRect();
        if (r.right > pr.right || r.bottom > pr.bottom) out.pageOverflow.push({ page: pi + 1, line: n });
      });
      pg.querySelectorAll('.dwrap').forEach(dw => {
        const box = dw.getBoundingClientRect();
        const svg = dw.querySelector('svg');
        let minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
        svg.querySelectorAll('*').forEach(el => {
          if (!el.getBBox) return;
          const b = el.getBoundingClientRect();
          if (b.width === 0 && b.height === 0) return;
          minx = Math.min(minx, b.left); miny = Math.min(miny, b.top);
          maxx = Math.max(maxx, b.right); maxy = Math.max(maxy, b.bottom);
        });
        const d = { page: pi + 1, lines: dw.dataset.lines,
          outL: Math.round(box.left - minx), outT: Math.round(box.top - miny),
          outR: Math.round(maxx - box.right), outB: Math.round(maxy - box.bottom) };
        if (d.outL > 1 || d.outT > 1 || d.outR > 1 || d.outB > 1) out.diagrams.push(d);
      });
    });
    return out;
  });
  console.log(JSON.stringify(report, null, 1));

  // ---- PNGs
  fs.rmSync(PNG_DIR, { recursive: true, force: true });
  fs.mkdirSync(PNG_DIR, { recursive: true });
  const pages = await page.$$('.page');
  for (let i = 0; i < pages.length; i++) {
    await pages[i].screenshot({ path: path.join(PNG_DIR, `page-${String(i + 1).padStart(2, '0')}.png`) });
  }
  // ---- PDF
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: path.join(ROOT, 'geol211_exam2_notes.pdf'), width: '8.5in', height: '11in',
                   printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 },
                   preferCSSPageSize: true });
  console.log('pages rendered:', pages.length);
  await browser.close();
})();
