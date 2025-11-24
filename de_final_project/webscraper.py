import requests
from bs4 import BeautifulSoup
import re
import csv
import json
from urllib.parse import urljoin

BASE_URL = "https://www.new.somervillepd.com/index.php/other-public-safety-news/weekly-crime-log"
DOMAIN = "https://www.new.somervillepd.com"

def get_soup(url):
    res = requests.get(url)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")

def extract_all_links():
    all_links = set()
    offset = 0
    MAX_OFFSET = 25

    while True:
        if offset > MAX_OFFSET:
            print(f"Reached max pagination offset ({MAX_OFFSET}). Stopping search.")
            break

        page_url = f"{BASE_URL}?start={offset}" if offset > 0 else BASE_URL
        print(f"Checking {page_url}")
        soup = get_soup(page_url)

        links = [
            urljoin(DOMAIN, a["href"])
            for a in soup.find_all("a", href=True)
            if "crime-log" in a["href"] and not a["href"].endswith("weekly-crime-log")
        ]

        if not links:
            break

        new_links = len(set(links) - all_links)
        all_links.update(links)

        print(f"Found {len(links)} links on this page, {len(all_links)} total collected so far.")
        offset += 5  # Somerville site increments in steps of 5

    return list(all_links)

def parse_page(url):
    soup = get_soup(url)
    title_tag = soup.find("h3")
    source = title_tag.get_text(strip=True) if title_tag else url

    data = []
    paragraphs = soup.find_all("p", class_="MsoNormal")
    current_type = None

    for p in paragraphs:
        strong = p.find("strong")
        if strong:
            current_type = strong.get_text(strip=True)
            continue

        text = p.get_text(" ", strip=True)
        match = re.match(r"(\d{8}): On (\d{1,2}/\d{1,2}/\d{2}) at approximately ([0-9: ]+[AP]M), (.*)", text)
        if match:
            case_number, date, time, description = match.groups()
            data.append({
                "Source": source,
                "Case Number": case_number,
                "Date": date,
                "Time": time,
                "Type": current_type if current_type else "",
                "Description": description
            })

    return data

def main():
    all_data = []
    links = extract_all_links()
    print(f"\nFound {len(links)} total crime log pages to scrape.\n")

    for link in links:
        print(f"Scraping: {link}")
        try:
            page_data = parse_page(link)
            print(f"  → {len(page_data)} reports extracted.")
            all_data.extend(page_data)
        except Exception as e:
            print(f"Failed on {link}: {e}")

    with open("somerville_crime_log.json", "w", encoding="utf-8") as jf:
        json.dump(all_data, jf, indent=2)

    with open("somerville_crime_log.csv", "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["Source", "Case Number", "Date", "Time", "Type", "Description"])
        writer.writeheader()
        writer.writerows(all_data)

    print(f"\nSaved {len(all_data)} total reports to somerville_crime_log.json and somerville_crime_log.csv")

if __name__ == "__main__":
    main()
