// Renders the study guide HTML to a US Letter PDF (with page-number footer) and runs layout checks.
// PNGs are made from the PDF afterwards by rasterize.py so they match the PDF exactly.
const path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const ROOT = path.resolve(__dirname, '..');
const HTML = path.join(ROOT, 'geol211_exam2_study_guide.html');
const PDF = path.join(ROOT, 'geol211_exam2_study_guide.pdf');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 } });
  await page.goto('file://' + HTML);
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: 'print' });

  // Check: nothing wider than the text column (7.3in = 700.8px), no clipped SVG content.
  const report = await page.evaluate(() => {
    const body = document.body.getBoundingClientRect();
    const out = { wide: [], svgClip: [], fontOk: document.fonts.check('14px SS3') };
    document.querySelectorAll('body *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width && (r.right > body.right + 0.5 || r.left < body.left - 0.5))
        out.wide.push({ tag: el.tagName, cls: el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className,
                        right: Math.round(r.right - body.right), text: (el.textContent || '').slice(0, 50) });
    });
    document.querySelectorAll('svg.dia').forEach((svg, i) => {
      const box = svg.getBoundingClientRect();
      let bad = [];
      svg.querySelectorAll('*').forEach(el => {
        const b = el.getBoundingClientRect();
        if (!b.width && !b.height) return;
        if (b.left < box.left - 1 || b.right > box.right + 1 || b.top < box.top - 1 || b.bottom > box.bottom + 1)
          bad.push((el.textContent || el.tagName).slice(0, 30));
      });
      if (bad.length) out.svgClip.push({ svg: i, near: svg.closest('article') ? svg.closest('article').id : '', bad: bad.slice(0, 5) });
    });
    return out;
  });
  console.log(JSON.stringify(report, null, 1));

  await page.pdf({
    path: PDF, width: '8.5in', height: '11in', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>',
    footerTemplate: '<div style="width:100%;font-size:8.5px;color:#777;font-family:Arial,sans-serif;text-align:center;">' +
      'GEOL 211 · Exam 2 Study Guide · page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
  });
  console.log('pdf written');
  await browser.close();
})();
