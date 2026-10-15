import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
modules = sorted(list((ROOT / "content/modules").glob("*.md")) + list((ROOT / "content/operations/modules").glob("*.md")))
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
    if html.exists() and html.stat().st_mtime < source.stat().st_mtime: errors.append(f"stale HTML older than source: {stem}")
    if pdf.exists() and pdf.stat().st_mtime < source.stat().st_mtime: errors.append(f"stale PDF older than source: {stem}")
    if pdf.exists() and shutil.which("pdfinfo"):
        result = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
        if result.returncode: errors.append(f"unreadable PDF metadata: {stem}")
        info = result.stdout
        pages = next((line for line in info.splitlines() if line.startswith("Pages:")), "Pages: 0")
        page_count = int(pages.split(":", 1)[1].strip()); page_counts[stem] = page_count
        if page_count < 2: errors.append(f"too few PDF pages: {stem}")
        if "612 x 792 pts" not in info: errors.append(f"unexpected page size: {stem}")
    if pdf.exists() and shutil.which("pdftotext"):
        extracted = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True)
        if extracted.returncode: errors.append(f"PDF text extraction failed: {stem}")
        elif len(extracted.stdout.split()) < max(300, int(len(source_text.split()) * 0.65)): errors.append(f"insufficient extractable PDF text: {stem}")
print(f"publication modules: {len(modules)}")
print("page counts: " + ", ".join(f"{stem}={count}" for stem, count in page_counts.items()))
if errors: print("PUBLICATION QA FAILED\n" + "\n".join(errors)); sys.exit(1)
print("PUBLICATION QA PASSED: source depth, references, HTML/PDF outputs, readability metadata, page size, and page counts validated")
