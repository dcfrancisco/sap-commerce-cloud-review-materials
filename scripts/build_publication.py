import html
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"; DIST.mkdir(exist_ok=True)
source = ROOT / "content/modules/01-architecture-fundamentals.md"
out_html = DIST / "m01-architecture-fundamentals.html"
parts = []
for line in source.read_text().splitlines():
    if line.startswith("# "): parts.append(f"<h1>{html.escape(line[2:])}</h1>")
    elif line.startswith("## "): parts.append(f"<h2>{html.escape(line[3:])}</h2>")
    elif line.startswith("### "): parts.append(f"<h3>{html.escape(line[4:])}</h3>")
    elif line == "```": parts.append("</pre>")
    elif line.startswith("```"): parts.append("<pre>")
    elif line.startswith("- "): parts.append(f"<li>{html.escape(line[2:])}</li>")
    elif line.strip(): parts.append(f"<p>{html.escape(line)}</p>")
out_html.write_text("<!doctype html><html><head><meta charset='utf-8'><title>M01 Manual</title><style>body{font:14px system-ui;max-width:850px;margin:35px auto;line-height:1.55}pre{background:#f3f4f6;padding:12px;overflow:auto}h1,h2{page-break-after:avoid}</style></head><body>" + "\n".join(parts) + "</body></html>")
print(out_html)
if shutil.which("pandoc"):
    pdf = DIST / "m01-architecture-fundamentals.pdf"
    result = subprocess.run(["pandoc", str(source), "-o", str(pdf), "--metadata", "title=SAP Commerce Cloud Architecture and Fundamentals"], capture_output=True, text=True)
    if result.returncode == 0: print(pdf)
    else: print("PDF not generated: " + result.stderr.strip())
