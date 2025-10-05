import re
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict
import requests
from PyPDF2 import PdfReader

# ========== CONFIG ==========
LOG_LEVEL = 2  # 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG
INPUT_JSON = "files.json"
OUT_CSV = "results/all_crime_news.csv"
OUT_JSON = "results/all_crime_news.json"
SOURCE_DIR = Path("source")
RESULTS_DIR = Path("results")
# ============================

# Setup logging
levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
logging.basicConfig(
    level=levels[LOG_LEVEL],
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("parser.log"), logging.StreamHandler()]
)

case_pattern = re.compile(
    r"^(25\d+): On (\d{1,2}/\d{1,2}/\d{2})(?: at(?: approximately)? ([\d: ]+[APM]*))?, (.*)",
    re.IGNORECASE
)

def download_pdf(url: str, dest: Path):
    if not dest.exists():
        logging.info(f"Downloading {url} -> {dest}")
        r = requests.get(url, verify=False)  # ignore SSL
        dest.write_bytes(r.content)
    else:
        logging.info(f"Already downloaded {dest}")

def extract_text_from_pdf(pdf_path: Path) -> List[str]:
    logging.info(f"Parsing {pdf_path}")
    reader = PdfReader(str(pdf_path))
    lines = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        page_lines = text.splitlines()
        lines.extend(page_lines)
        logging.debug(f"[{pdf_path.stem}] Page {i}, {len(page_lines)} lines")
    return lines

def parse_cases(lines: List[str]) -> List[Dict]:
    cases = []
    buffer = []
    for line in lines:
        if re.match(r"^25\d+:", line.strip()):
            if buffer:
                cases.append(" ".join(buffer).strip())
                buffer = []
            buffer.append(line.strip())
        else:
            if buffer:
                buffer.append(line.strip())
    if buffer:
        cases.append(" ".join(buffer).strip())

    results = []
    for entry in cases:
        m = case_pattern.match(entry)
        if m:
            case_num, date, time, intro = m.groups()
            desc = entry[entry.find(intro):]  # full description after intro
            results.append({
                "case_number": case_num,
                "date": date,
                "time": time if time else "",
                "description": f"Somerville Police responded to {desc}"
            })
        else:
            logging.warning(f"Unmatched case: {entry[:120]}...")
    return results

def main():
    SOURCE_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    files = json.loads(Path(INPUT_JSON).read_text())
    all_records = []

    for entry in files["crime_news_pdfs"]:
        url = entry["url"]
        title = entry["title"]
        fname = SOURCE_DIR / Path(url).name.replace(" ", "_")
        download_pdf(url, fname)
        lines = extract_text_from_pdf(fname)
        cases = parse_cases(lines)
        all_records.extend(cases)

    # Save CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_number", "date", "time", "description"])
        writer.writeheader()
        writer.writerows(all_records)

    # Save JSON
    Path(OUT_JSON).write_text(json.dumps(all_records, indent=2), encoding="utf-8")

    logging.info(f"Done. Saved {len(all_records)} records to {OUT_CSV} and {OUT_JSON}")

if __name__ == "__main__":
    main()
