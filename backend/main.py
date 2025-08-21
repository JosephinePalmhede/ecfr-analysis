# Provides api endpoints to retrieve stored data
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from backend.analyzer import analyze_agencies, analyze_agencies_over_time, extract_relevant_text_for_agency, load_json

app = FastAPI()
DATA_FOLDER = "backend/data"
DEFAULT_DATE = "2024-07-01"

#needed so that my streamlit app can use a different port
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Provides the agencies.json
# `GET /api/agencies`
@app.get("/api/agencies")
def get_agencies():
    agencies_data = load_json(f"{DATA_FOLDER}/agencies.json")
    return sorted([
        agency.get("display_name") or agency.get("name")
        for agency in agencies_data.get("agencies", [])
    ])

# Provides the relevant chapter sections for a specified agency on a specified date
# `GET /api/agency_sections?agency=A&date=YYYY-MM-DD`
@app.get("/api/agency_sections")
def get_agency_sections(agency: str, date: str):
    sections = extract_relevant_text_for_agency(DATA_FOLDER, agency, date)
    if not sections:
        raise HTTPException(status_code=404, detail="No sections found for this agency.")
    return {"agency": agency, "sections": sections}

# Provides word count, complexity, and checksum for the given agency over time. Also includes delta (change) if two dates are provided.
# `GET /api/historical?agency=A&dates=YYYY-MM-DD&dates=YYYY-MM-DD`
@app.get("/api/historical")
def historical(
    dates: list[str] = Query(...), 
    agency: str = Query(..., description="Agency name required"),
    data_folder: str = "backend/data"):

    if not agency:
        raise HTTPException(status_code=400, detail="Agency must be specified.")

    print(f"Dates received: {dates}")

    history = analyze_agencies_over_time(DATA_FOLDER, dates, agency_filter=agency)
    print(f"Returning: {history}")
    return history

# Return wordcount metrics for a given agency on a single date.
# `GET /api/wordcount?agency=A&date=YYYY-MM-DD`
@app.get("/api/wordcount")
def wordcount(
    date: Optional[str] = Query(DEFAULT_DATE),
    agency: Optional[str] = Query(None)
):
    results = analyze_agencies(DATA_FOLDER, date, agency_filter=agency)
    return {name: info["word_count"] for name, info in results.items()}

# Return checksum for a given agency on a single date.
# `GET /api/checksums?agency=A&date=YYYY-MM-DD`
@app.get("/api/checksums")
def checksums(
    date: Optional[str] = Query(DEFAULT_DATE),
    agency: Optional[str] = Query(None)
):
    results = analyze_agencies(DATA_FOLDER, date, agency_filter=agency)
    return {name: info["checksum"] for name, info in results.items()}

# Return complexity metrics for a given agency on a single date.
# `GET /api/complexity?agency=A&date=YYYY-MM-DD`
@app.get("/api/complexity")
def complexity(
    date: Optional[str] = Query(DEFAULT_DATE),
    agency: Optional[str] = Query(None)
):
    results = analyze_agencies(DATA_FOLDER, date, agency_filter=agency)
    return {name: info["complexity"] for name, info in results.items()}