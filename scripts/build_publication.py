import html
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"; DIST.mkdir(exist_ok=True)
modules = sorted((ROOT / "content/modules").glob("*.md"))
if not modules: raise SystemExit("no module sources")
for source in modules:
    stem = source.stem
    parts = []
    for line in source.read_text().splitlines():
        if line.startswith("# "): parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "): parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "): parts.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line == "```": parts.append("</pre>")
        elif line.startswith("```"): parts.append("<pre>")
        elif line.startswith("- "): parts.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.strip(): parts.append(f"<p>{html.escape(line)}</p>")
    out_html = DIST / f"{stem}.html"
    out_html.write_text("<!doctype html><html><head><meta charset='utf-8'><title>" + html.escape(stem) + "</title><style>@page{margin:22mm}body{font:14px system-ui;max-width:850px;margin:35px auto;line-height:1.55}pre{background:#f3f4f6;padding:12px;overflow:auto;white-space:pre-wrap}h1,h2{page-break-after:avoid}</style></head><body>" + "\n".join(parts) + "</body></html>")
    print(out_html)
    if shutil.which("pandoc"):
        pdf = DIST / f"{stem}.pdf"
        result = subprocess.run([
            "pandoc", str(source), "-o", str(pdf),
            "--standalone", "--toc", "--toc-depth=2",
            "-V", "geometry:margin=0.85in", "-V", "fontsize=11pt",
            "-V", "colorlinks=true", "-V", "linkcolor=blue", "-V", "urlcolor=blue",
            "--highlight-style=tango"
        ], capture_output=True, text=True)
        if result.returncode: raise SystemExit(f"PDF failed for {source}: {result.stderr}")
        print(pdf)
