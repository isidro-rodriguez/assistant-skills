#!/usr/bin/env node
// Render LaTeX to self-contained SVG with MathJax.
// stdin:  JSON array of {"tex": "...", "display": true|false}
// stdout: JSON array of {"svg": "<svg…>"} or {"error": "..."} in the same order.
// Used by build_pdf.py; requires `npm install` in this folder.

const MathJax = require("mathjax");

async function main() {
  const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
  const mj = await MathJax.init({
    loader: { load: ["input/tex", "output/svg"] },
    tex: { packages: { "[+]": ["ams"] } },
    svg: { fontCache: "local", linebreaks: { inline: false } }, // self-contained, one SVG per formula
  });
  const adaptor = mj.startup.adaptor;
  const out = [];
  for (const { tex, display } of input) {
    try {
      const node = await mj.tex2svgPromise(tex, { display: !!display });
      const svg = adaptor.firstChild(node);
      if (adaptor.getAttribute(svg, "data-mjx-error") || /merror/.test(adaptor.outerHTML(svg))) {
        const msg = adaptor.textContent(svg) || "TeX error";
        out.push({ error: msg });
      } else {
        out.push({ svg: adaptor.outerHTML(svg) });
      }
    } catch (e) {
      out.push({ error: String(e.message || e) });
    }
  }
  process.stdout.write(JSON.stringify(out));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
