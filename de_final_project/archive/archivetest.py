import pdfplumber
import re
import pandas as pd
import logging

# =======================
# CONFIG
# =======================
VERBOSITY = 2  # 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG
pdf_path = "source/crime_news.pdf"
csv_out = "results/crime_news.csv"
json_out = "results/crime_news.json"
log_file = "log/parser.log"
# =======================

# Configure logging
log_levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
logging.basicConfig(
    filename=log_file,
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=log_levels[VERBOSITY],
)

records = []
current_type = None
current_record = None

# Regex for case start
case_pattern = re.compile(
    r"^(25\d+): On (\d{1,2}/\d{1,2}/\d{2}) at approximately ([\d: ]+[APM]+),? (.*)",
    re.IGNORECASE,
)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        lines = page.extract_text().split("\n")

        logging.info(f"Processing page {page_num} with {len(lines)} lines")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip Crime Log headers
            if line.startswith("Crime Log"):
                if current_record:
                    records.append(current_record)
                    logging.debug(f"Closed record {current_record['Case Number']} at new Crime Log header")
                    current_record = None
                logging.info(f"Found Crime Log header: {line}")
                continue

            # Detect short headings like "Assault", "Arrest"
            if not line.startswith("25") and len(line.split()) < 6:
                current_type = line
                logging.debug(f"Detected incident type: {current_type}")
                continue

            # Detect case start
            match = case_pattern.match(line)
            if match:
                # Save any open record
                if current_record:
                    records.append(current_record)
                    logging.debug(f"Closed record {current_record['Case Number']} at new case")

                case_number, date, time, details = match.groups()
                logging.info(f"New case found: {case_number} ({date} {time})")

                # Normalize description
                if "for report of" in details.lower():
                    rest = details.split("for report of", 1)[1].strip()
                    clean_desc = f"Somerville Police responded to a report of {rest}"
                else:
                    clean_desc = f"Somerville Police responded to {details.strip()}"

                current_record = {
                    "Case Number": case_number,
                    "Date": date,
                    "Time": time,
                    "Type": current_type,
                    "Description": clean_desc,
                }
            elif current_record:
                # Continuation of description
                current_record["Description"] += " " + line
                logging.debug(f"Appended to case {current_record['Case Number']}: {line}")

# Save last record
if current_record:
    records.append(current_record)
    logging.debug(f"Closed final record {current_record['Case Number']}")

# Convert to DataFrame
df = pd.DataFrame(records)

# Export
df.to_csv(csv_out, index=False)
df.to_json(json_out, orient="records", indent=2)

logging.info(f"Parsing complete. {len(records)} records saved to {csv_out} and {json_out}")