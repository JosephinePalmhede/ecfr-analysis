# Makes all calls to to download the current eCFR data and stores it
import requests
import os
import json

# Downloads agencies data
def fetch_agencies():
    url = "https://www.ecfr.gov/api/admin/v1/agencies.json"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    os.makedirs("backend/data", exist_ok=True)
    with open("backend/data/agencies.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Agencies data saved.")

# Downloads title data
def fetch_titles_summary():
    url = "https://www.ecfr.gov/api/versioner/v1/titles.json"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    os.makedirs("backend/data", exist_ok=True)
    with open("backend/data/titles_summary.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Titles summary saved.")

# Downloads full xml documents
def fetch_full_title_xml(date: str, title_number: int) -> bool:
    url = f"https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{title_number}.xml"
    response = requests.get(url)
    if response.status_code == 200:
        os.makedirs("backend/data", exist_ok=True)
        fname = f"backend/data/title_{title_number}_{date}.xml"
        with open(fname, "wb") as f:
            f.write(response.content)
        print(f"Downloaded XML for Title {title_number} on {date}")
    else:
        print(f"    Failed to download Title {title_number} XML: {response.status_code}")
        return False
    return True