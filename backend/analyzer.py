# backend/analyzer.py
import os
import json
import hashlib
import textstat
import xml.etree.ElementTree as ET

from backend.fetcher import fetch_full_title_xml, fetch_agencies, fetch_titles_summary

DATA_FOLDER = "backend/data"

# Processes a raw XML document located in file_path and (when return_sections is True) returns a dict where
#   keys = chapter headings (ex. Chapter II-Department of Agrictulture)
#   values = full text from that chapter
# Params:
#   file_path (str) path to the xml file (ex. backend/data/title_2_2024-07-01.xml)
#   target_chapters (list[str] or None) optional list of chapter numbers to extract
#   return_sections (bool) if True returns a full keyed dict, otherwise returns a str
def parse_title_xml(file_path, target_chapters=None, return_sections=False):
    tree = ET.parse(file_path)
    root = tree.getroot()

    # If no sections, just return as one chunk
    if not return_sections:
        text_blocks = []

        # If no filtering, gather all text in document (for analysis)
        if not target_chapters:
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    text_blocks.append(elem.text.strip())
            return " ".join(text_blocks)

        for chapter_elem in root.findall(".//DIV3[@TYPE='CHAPTER']"):
            chapter_number = chapter_elem.attrib.get("N", "").upper()
            if any(chap and chap.upper() == chapter_number for chap in target_chapters):
                for elem in chapter_elem.iter():
                    if elem.text and elem.text.strip():
                        text_blocks.append(elem.text.strip())
        return " ".join(text_blocks)

    # Dict output for chapters separated into sections (for displaying in ui)
    else:
        chapter_texts = {}
        for chapter_elem in root.findall(".//DIV3[@TYPE='CHAPTER']"):
            chapter_number = chapter_elem.attrib.get("N", "").upper()
            if (not target_chapters) or any(chap and chap.upper() == chapter_number for chap in target_chapters):
                heading_elem = chapter_elem.find("HEAD")
                heading = heading_elem.text.strip() if heading_elem is not None else f"Chapter {chapter_number}"
                text_blocks = []

                for elem in chapter_elem.iter():
                    if elem.text and elem.text.strip():
                        text_blocks.append(elem.text.strip())
                chapter_texts[heading] = " ".join(text_blocks)
        return chapter_texts

# Simple word count
def compute_word_count(text):
    return len(text.split())

# Computes a SHA-256 checksum of the full regulatory text.
def compute_checksum(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# Computes a complexity score for the text based on the Flesch-Kincaid Grade Level
def compute_complexity(text):
    try:
        return textstat.flesch_kincaid_grade(text)
    except:
        return None

# Performs three analysis on a provided xml file
# Outdated, left in to show why parse_title_xml has optional params
#def analyze_title(file_path):
#    text = parse_title_xml(file_path)
#    return {
#        "word_count": compute_word_count(text),
#        "checksum": compute_checksum(text),
#        "complexity": compute_complexity(text)
#    }

# Loads a json file from file_path and if the file does not exist it attempts to fetch it
def load_json(file_path):
    if not os.path.exists(file_path):
        print(f"{file_path} not found. Attempting to fetch...")

        # Check which file is missing and fetch it
        if file_path.endswith("agencies.json"):
            fetch_agencies()
        elif file_path.endswith("titles_summary.json") or file_path.endswith("titles.json"):
            fetch_titles_summary()

        # Catch still missing error
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Failed to fetch required file: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Builds a dict with agencies_data where
#   keys = agency name
#   values = a nested dict with titles -> chapters list and name -> agency name
def build_agency_title_map(agencies_data):
    agency_map = {}
    # Flatten agencies with IDs and names (recursively for children)
    for agency in agencies_data.get("agencies", []):
        name = agency.get("name") # or agency.get("display_name")
        titles = [ref["title"] for ref in agency.get("cfr_references") if "title" in ref]

        if titles:
            agency_map[name] = {
                "titles": titles,
                "name": name
            }

    return agency_map

# Analyzses an agency's relevant title chapters for word count, complexity, and its checksum
# Params:
#   DATA_FOLDER (str) path to the folder where xml and json files are stored
#   date (str) The date "YYYY-MM-DD" used to identify which xml documents to analyze
#   agency_filter (str) optional agency name to filter for
# Returns:
#   a dict that looks like:
#{
#    "Agency Name": {
#        "agency_name": str,
#        "word_count": int,
#        "checksum": str,
#        "complexity": float,
#        "titles_count": int,
#        "titles analyzed": [int]
#    },
#   ...
#}
def analyze_agencies(DATA_FOLDER, date, agency_filter=None):
    agencies_data = load_json(os.path.join(DATA_FOLDER, "agencies.json"))
    #print(json.dumps(agencies_data)) #debug
    agency_map = build_agency_title_map(agencies_data)
    #print(json.dumps(agency_map)) #debug
    results = {}

    for agency_id, info in agency_map.items():
        # Skip unrelated agencies if agency filter
        if agency_filter and agency_id != agency_filter:
            continue  

        print(f"\nAnalyzing agency: {agency_id}") #debug
        combined_text = ""
        total_word_count = 0
        analyzed_titles = []

        for title_num in info["titles"]:
            xml_file = os.path.join(DATA_FOLDER, f"title_{title_num}_{date}.xml")

            # Download xml file if it is missing
            if not os.path.exists(xml_file):
                print(f"XML not found locally. Fetching from eCFR for title {title_num}...")
                success = fetch_full_title_xml(date, title_num)
                # Skip if fetch fails
                if not success:
                    print(f"    Skipping Title {title_num} due to fetch failure.")
                    continue

            print(f"  Analyzing title {title_num}")
    
            # Get relevant chapters for this title
            relevant_chapters = [
                cref.get("chapter")
                for agency in agencies_data["agencies"]
                if (agency.get("display_name") or agency.get("name")) == agency_id
                for cref in agency.get("cfr_references", [])
                if cref.get("title") == title_num and cref.get("chapter") is not None
            ]
            print(f"    Relevant chapters: {relevant_chapters}") #debug

            if not relevant_chapters or any(chap is None for chap in relevant_chapters):
                relevant_chapters = None
                print("    No chapters specified or missing chapter info, parsing entire title") #debug

            text = parse_title_xml(xml_file, target_chapters=relevant_chapters)
            print(f"    Extracted text length: {len(text)}") #debug

            if text.strip():
                total_word_count += compute_word_count(text)
                combined_text += " " + text
                analyzed_titles.append(title_num)
            else:
                print(f"    No relevant text found for title {title_num}") #debug

        # Build dict
        if combined_text.strip():
            #print(f"Data found for {agency_id}") #debug
            results[agency_id] = {
                "agency_name": info["name"],
                "word_count": total_word_count,
                "checksum": compute_checksum(combined_text),
                "complexity": compute_complexity(combined_text),
                "titles_count": len(analyzed_titles),
                "titles analyzed": analyzed_titles
            }
        else:
            print(f"No data for {agency_id} on {date}") #debug
    return results

# Extracts chapter headings and text connected to a specific agency for use in api. Returns a dict where
#   keys = chapter headings (ex. Chapter II-Department of Agrictulture)
#   values = full text from that chapter
# Params:
#   DATA_FOLDER (str) path to the folder where xml and json files are stored
#   agency_name (str) name of the agency to extract chapters for
#   date (str) The date "YYYY-MM-DD" used to identify which xml documents to analyze
def extract_relevant_text_for_agency(DATA_FOLDER, agency_name, date):
    agencies_data = load_json(os.path.join(DATA_FOLDER, "agencies.json"))
    agency_map = build_agency_title_map(agencies_data)
    info = agency_map[agency_name]
    sections = {}

    # error catch
    if agency_name not in agency_map:
        return sections #as {}

    for title_num in info["titles"]:
        xml_file = os.path.join(DATA_FOLDER, f"title_{title_num}_{date}.xml")
        if not os.path.exists(xml_file):
            print(f"    XML not found locally. Fetching from eCFR for title {title_num}...") #debug
            fetch_full_title_xml(date, title_num)

        if os.path.exists(xml_file):

            relevant_chapters = [
                cref.get("chapter")
                for agency in agencies_data["agencies"]
                if (agency.get("display_name") or agency.get("name")) == agency_name
                for cref in agency.get("cfr_references", [])
                if cref.get("title") == title_num and cref.get("chapter") is not None
            ]

            if not relevant_chapters or any(chap is None for chap in relevant_chapters):
                relevant_chapters = None

            # use dict from parse_title_xml
            chapter_text = parse_title_xml(xml_file, target_chapters=relevant_chapters, return_sections=True)
            for heading, text in chapter_text.items():
                if text.strip():
                    sections[heading] = text

    return sections

# Analyzes an agency on two dates in time for their metrics and returns data for both dates as well as a comparison between the two
# Params:
#   DATA_FOLDER (str) path to the folder where xml and json files are stored
#   date (str) The date "YYYY-MM-DD" used to identify which xml documents to analyze
#   agency_filter (str) optional agency name to filter for
# Returns:
#   a nested dict that looks like:
#{
#  "Agency name": {
#    "date 1": {
#      "word_count": int,
#      "checksum": str,
#      "complexity": float
#    },
#    "date 2": {
#      "word_count": int,
#      "checksum": str,
#      "complexity": float
#    },
#    "delta": {
#      "word_count": int,
#      "complexity_change": float
#    }
#  },
#   ...
#}
def analyze_agencies_over_time(DATA_FOLDER, dates, agency_filter=None):
    history = {}  # {agency: {date: metrics}}

    for date in dates:
        agency_metrics = analyze_agencies(DATA_FOLDER, date, agency_filter=agency_filter)
        for agency, metrics in agency_metrics.items():
            if agency not in history:
                history[agency] = {}
            history[agency][date] = {
                "word_count": metrics["word_count"],
                "checksum": metrics["checksum"],
                "complexity": metrics["complexity"]
            }

    # Add deltas if two dates are given
    if len(dates) == 2:
        start, end = dates
        for agency, records in history.items():
            if start in records and end in records:
                delta = {
                    "word_count": records[end]["word_count"] - records[start]["word_count"],
                    "complexity_change": (
                        records[end]["complexity"] - records[start]["complexity"]
                        if records[end]["complexity"] is not None and records[start]["complexity"] is not None
                        else None
                    )
                }
                records["delta"] = delta

    return history


#print(json.dumps(analyze_agencies(DATA_FOLDER, "2024-07-01"))) #debug