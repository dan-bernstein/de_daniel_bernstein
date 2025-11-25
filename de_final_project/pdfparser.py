import pdfplumber
import re
import pandas as pd
import json
import subprocess
import os


json_file = "source/files.json"
output_csv = "results/all_crime_news.csv"
output_json = "results/all_crime_news.json"
download_dir = "downloads"

os.makedirs(download_dir, exist_ok=True)
os.makedirs(os.path.dirname(output_csv), exist_ok=True)

#8-digit case numbers
case_pattern = re.compile(
    r"^(\d{8}): On (\d{1,2}/\d{1,2}/\d{2})(?: at(?: approximately)? ([\d: ]+[APM]*))?, (.*)",
    re.IGNORECASE,
)

def parse_pdf(pdf_path, source_title):
    """Parse a single PDF and return a list of records."""
    records = []
    current_record = None
    current_type = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text:
                    continue

                text = text.replace("-\n", "")

                lines = text.split("\n")

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if re.match(r"^(Page \d+|Crime Log.*)$", line, re.IGNORECASE):
                        continue

                    if len(line.split()) < 6 and not re.match(r"^\d{8}:", line):
                        current_type = line
                        continue

                    match = case_pattern.match(line)
                    if match:
                        if current_record:
                            current_record["Description"] = " ".join(current_record["Description"]).replace("\u2028", " ").strip()
                            records.append(current_record)

                        case_number, date, time, details = match.groups()
                        current_record = {
                            "Source": source_title,
                            "Case Number": case_number,
                            "Date": date,
                            "Time": time if time else "",
                            "Type": current_type,
                            "Description": [details.strip()],
                        }
                    elif current_record:
                        current_record["Description"].append(line.strip())

        if current_record:
            current_record["Description"] = " ".join(current_record["Description"]).replace("\u2028", " ").strip()
            records.append(current_record)

    except Exception as e:
        print(f"Failed to parse {pdf_path}: {e}")

    return records

def download_pdf(url, dest):
    """Download PDF if it doesn't exist."""
    if os.path.exists(dest):
        return
    try:
        subprocess.run(["curl", "-k", "-L", "-o", dest, url], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Download failed for {url}: {e}")

def main():
    # Load URLs
    with open(json_file, "r") as f:
        data = json.load(f)

    all_records = []

    for idx, entry in enumerate(data["crime_news_pdfs"], start=1):
        title = entry["title"]
        url = entry["url"]
        pdf_path = os.path.join(download_dir, title.replace(" ", "_") + ".pdf")

        print(f"[{idx}/{len(data['crime_news_pdfs'])}] Processing: {title}")
        download_pdf(url, pdf_path)
        records = parse_pdf(pdf_path, title)
        all_records.extend(records)

    # Save output
    df = pd.DataFrame(all_records)
    df.to_csv(output_csv, index=False)
    df.to_json(output_json, orient="records", indent=2)
    print(f"Done. Saved {len(all_records)} records to {output_csv} and {output_json}")

if __name__ == "__main__":
    main()