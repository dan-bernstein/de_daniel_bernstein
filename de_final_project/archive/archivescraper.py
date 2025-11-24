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

def extract_links():
    """Finds all weekly crime log links from the main log page and archived pages."""
    soup = get_soup(BASE_URL)
    links = []

    # find <a> tags with href containing 'crime-log'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "crime-log" in href and href.endswith("2025"):
            full_url = urljoin(DOMAIN, href)
            links.append(full_url)
    links = list(set(links))
    return links

def parse_page(url):
    """Extracts all crime reports from a single crime log page."""
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
    links = extract_links()
    print(f"Found {len(links)} crime log pages")

    for link in links:
        print(f"Scraping: {link}")
        try:
            page_data = parse_page(link)
            all_data.extend(page_data)
        except Exception as e:
            print(f"Failed on {link}: {e}")

    # Save JSON
    with open("somerville_crime_log.json", "w", encoding="utf-8") as jf:
        json.dump(all_data, jf, indent=2)

    # Save CSV
    with open("somerville_crime_log.csv", "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["Source", "Case Number", "Date", "Time", "Type", "Description"])
        writer.writeheader()
        writer.writerows(all_data)

    print(f"✅ Saved {len(all_data)} total reports to somerville_crime_log.json and somerville_crime_log.csv")

if __name__ == "__main__":
    main()
