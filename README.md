# Federal Regulation Analyzer

A full-stack application that allows users to analyze U.S. federal regulations by agency using data from the [eCFR.gov](https://www.ecfr.gov/) API. Built in Python with FastAPI (backend) and Streamlit (frontend).

## Project Structure
```
project_root/
├── backend/
│    ├── main.py             # FastAPI app
│    ├── fetcher.py          # Downloads eCFR data
│    ├── analyzer.py         # Computes metrics (word count, checksums, etc)
│    └── data/               # Cached data (after fetching)
├── frontend/
│    └── app.py              # Streamlit UI
├── requirements.txt        # Shared dependencies
└── README.md               # Setup and usage instructions
```


## Features
- Download and analyze regulatory text by agency (word count, complexity, checksum)  
- Compare regulation data historically across two dates 
- Parse and display relevant chapters for each agency
- APIs to retrieve the stored data
- Optional download for specific CFR XML files from eCFR.gov 
- Interactive UI for browsing, analysis, and downloads  
- All data stored and reused locally

## Setup
- `pip install -r requirements.txt` 
    Python 3.9 required
- Run the FastAPI backend: `uvicorn backend.main:app --reload`
    Runs at http://localhost:8000
- In a separate terminal, run the Streamlit frontend: `streamlit run frontend/app.py`
    Opens at http://localhost:8501

## Usage
Analyze Titles Per Agency:
- Select an agency from dropdown
- Choose start and end dates
- Click Analyze to compute:
    Word Count
    Complexity (Flesch-Kincaid Grade Level)
    Checksum
    Changes over time (delta)
    Relevant Chapters (text parsed from XML)
- Only downloads and analyzes relevant titles/chapters
- Chapter text is shown in collapsible sections

Download specific XML files:
- Select a date and one or more CFR titles (1–50)
- Click Download Selected Titles
- Downloads each XML into `backend/data/`

## API Endpoints
`GET /api/agencies`
Returns list of all agencies (from agencies.json)

`GET /api/historical?agency=A&dates=YYYY-MM-DD&dates=YYYY-MM-DD`
Returns word count, complexity, and checksum for the given agency over time. Also includes delta (change) if two dates are provided.

`GET /api/agency_sections?agency=A&date=YYYY-MM-DD`
Returns parsed chapter titles and text relevant to the agency on the given date.

`GET /api/wordcount?agency=A&date=YYYY-MM-DD`, 
`GET /api/checksums?agency=A&date=YYYY-MM-DD`, 
`GET /api/complexity?agency=A&date=YYYY-MM-DD`
Return respective metrics for a specified agency on a single date.

## Notes
- XML fetches may occasionally fail (504 or 404). Try again later or reduce load.
- Chapter filtering relies on cfr_references in agencies.json
- Local XML files are cached in backend/data/

Built by Josephine Palmhede for USDS technical assessment
