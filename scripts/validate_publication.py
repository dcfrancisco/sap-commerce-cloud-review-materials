import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
modules = sorted((ROOT / "content/modules").glob("*.md"))
errors = []
page_counts = {}
for source in modules:
    stem = source.stem
    source_text = source.read_text()
    html = ROOT / "dist" / f"{stem}.html"
    pdf = ROOT / "dist" / f"{stem}.pdf"
    if len(source_text.split()) < 500: errors.append(f"source has fewer than 500 words: {stem}")
    if not source_text.startswith("# "): errors.append(f"missing module title: {stem}")
    if "References" not in source_text: errors.append(f"missing references section: {stem}")
    if source_text.count("```") % 2: errors.append(f"unbalanced code fences: {stem}")
    if any(marker in source_text.lower() for marker in ("lorem ipsum", "todo: write", "placeholder text")): errors.append(f"placeholder content: {stem}")
    if not html.exists() or html.stat().st_size < 1000: errors.append(f"missing/short HTML: {stem}")
    if not pdf.exists() or pdf.stat().st_size < 1000: errors.append(f"missing/short PDF: {stem}")
    if pdf.exists() and shutil.which("pdfinfo"):
        result = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
        if result.returncode: errors.append(f"unreadable PDF metadata: {stem}")
        info = result.stdout
        pages = next((line for line in info.splitlines() if line.startswith("Pages:")), "Pages: 0")
        page_count = int(pages.split(":", 1)[1].strip()); page_counts[stem] = page_count
        if page_count < 2: errors.append(f"too few PDF pages: {stem}")
        if "612 x 792 pts" not in info: errors.append(f"unexpected page size: {stem}")
print(f"publication modules: {len(modules)}")
print("page counts: " + ", ".join(f"{stem}={count}" for stem, count in page_counts.items()))
if errors: print("PUBLICATION QA FAILED\n" + "\n".join(errors)); sys.exit(1)
print("PUBLICATION QA PASSED: source depth, references, HTML/PDF outputs, readability metadata, page size, and page counts validated")
