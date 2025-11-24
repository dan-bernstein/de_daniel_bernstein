import pdfplumber
import re
import pandas as pd
import logging
import json
import subprocess
import os

# =======================
# CONFIG
# =======================
VERBOSITY = 2  # 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG
json_file = "source/files.json"
output_csv = "results/all_crime_news.csv"
output_json = "results/all_crime_news.json"
log_file = "log/parser.log"
download_dir = "downloads"
# =======================

# Logging setup
log_levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
logging.basicConfig(
    filename=log_file,
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=log_levels[VERBOSITY],
)

# Regex for case start
case_pattern = re.compile(
        r"^(\d{8}): On (\d{1,2}/\d{1,2}/\d{2})(?: at(?: approximately)? ([\d: ]+[APM]*))?, (.*)",
    re.IGNORECASE,
)

def parse_pdf(pdf_path, source_title):
    """Parse a single PDF and return list of records"""
    records = []
    current_type = None
    current_record = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                lines = page.extract_text().split("\n")
                logging.info(f"[{source_title}] Page {page_num}, {len(lines)} lines")

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Skip headers like "Crime Log ..."
                    if line.startswith("Crime Log"):
                        if current_record:
                            records.append(current_record)
                            logging.debug(f"Closed record {current_record['Case Number']} at new Crime Log header")
                            current_record = None
                        continue

                    # Detect short headings like "Assault", "Arrest"
                    if not line.startswith("25") and len(line.split()) < 6:
                        current_type = line
                        continue

                    # Start of new case
                    match = case_pattern.match(line)
                    if match:
                        if current_record:
                            records.append(current_record)
                        case_number, date, time, details = match.groups()

                        # Normalize description
                        if "for report of" in details.lower():
                            rest = details.split("for report of", 1)[1].strip()
                            clean_desc = f"Somerville Police responded to a report of {rest}"
                        else:
                            clean_desc = f"{details.strip()}"

                        current_record = {
                            "Source": source_title,
                            "Case Number": case_number,
                            "Date": date,
                            "Time": time,
                            "Type": current_type,
                            "Description": clean_desc,
                        }
                    elif current_record:
                        # Continuation of description
                        current_record["Description"] += " " + line

        if current_record:
            records.append(current_record)

    except Exception as e:
        logging.error(f"Failed to parse {pdf_path}: {e}")

    return records


def main():
    os.makedirs(download_dir, exist_ok=True)

    # Load URLs
    with open(json_file, "r") as f:
        data = json.load(f)

    all_records = []

    for entry in data["crime_news_pdfs"]:
        title = entry["title"]
        url = entry["url"]
        pdf_path = os.path.join(download_dir, title.replace(" ", "_") + ".pdf")

        logging.info(f"Downloading {url} -> {pdf_path}")
        try:
            subprocess.run(["curl", "-k", "-L", "-o", pdf_path, url], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Download failed for {url}: {e}")
            continue

        logging.info(f"Parsing {pdf_path}")
        records = parse_pdf(pdf_path, title)
        all_records.extend(records)

    # Save combined outputs
    df = pd.DataFrame(all_records)
    df.to_csv(output_csv, index=False)
    df.to_json(output_json, orient="records", indent=2)

    logging.info(f"Done. Saved {len(all_records)} records to {output_csv} and {output_json}")


if __name__ == "__main__":
    main()
