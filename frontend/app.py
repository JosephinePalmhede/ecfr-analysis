# Frontend Streamlit display for users
import sys
import os
import streamlit as st
import requests
import pandas as pd
# force the parent directory of this file to be on the module search path because it could not find the backend folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.fetcher import fetch_full_title_xml

st.title("Federal Regulation Analyzer")

## Download the XML files from eCFR
st.header("Download eCFR XML Files")

download_date = st.date_input("Select a date for XML download", pd.to_datetime("2024-07-01"))
available_titles = list(range(1, 51))

selected_titles = st.multiselect(
    "Select CFR Titles to Download",
    options=available_titles,
    default=[2] 
)

download_button = st.button("Download Selected Titles")

if download_button:
    if not selected_titles:
        st.warning("Please select at least one title.")
    else:
        with st.spinner("Downloading selected XML files from eCFR.gov..."):
            date = download_date.strftime("%Y-%m-%d")
            download_dir = "../backend/data"
            os.makedirs(download_dir, exist_ok=True)

            successes = []
            failures = []

            for title in selected_titles:
                success = fetch_full_title_xml(date, title)
                if success:
                    successes.append(title)
                else:
                    failures.append(title)

            if successes:
                st.success(f"Downloaded {len(successes)} XML file(s): {successes}")
            if failures:
                st.error(f"Failed to download Title(s): {failures}")

## Analyze the titles
st.header("Analyze Titles Per Agency")
# Fetch list of agencies for dropdown
@st.cache_data
def fetch_agencies():
    try:
        response = requests.get("http://localhost:8000/api/agencies")
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []

agencies = fetch_agencies()

if not agencies:
    st.error("Failed to load agency list.")
    st.stop()

# UI: select agency and dates
selected_agency = st.selectbox("Select an Agency", agencies)
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", pd.to_datetime("2020-07-01"))
with col2:
    end_date = st.date_input("End Date", pd.to_datetime("2025-07-01"))

# When user clicks button
if st.button("Analyze"):
    # Validate date entries
    if end_date < start_date:
        st.error("End Date must be on or after Start Date.")
        st.stop()
    
    with st.spinner("Running analysis..."):
        try:
            params = {
                "agency": selected_agency,
                "dates": [start_date.isoformat(), end_date.isoformat()]
            }

            #st.write(params) #raw params for debug
            response = requests.get("http://localhost:8000/api/historical", params=params)
            response.raise_for_status()
            data = response.json()

            # st.write("Raw API response:", data) #raw response for debug
            # Display analytics
            if selected_agency in data:
                agency_data = data[selected_agency]

                st.subheader(f"Metrics for {selected_agency}")
                for date in [start_date.isoformat(), end_date.isoformat()]:
                    if date in agency_data:
                        st.markdown(f"**{date}**")
                        st.write({
                            "Word Count": agency_data[date]["word_count"],
                            "Complexity": agency_data[date]["complexity"],
                            "Checksum": agency_data[date]["checksum"]
                        })
            
                if "delta" in agency_data:
                
                    st.subheader("Delta (Change Between Dates)")
                    delta = agency_data["delta"]
                    st.write({
                        "Word Count Change": delta["word_count"],
                        "Complexity Change": delta["complexity_change"]
                    })

                # Fetch and display relevant chapter sections for the latest date
                sections_url = "http://localhost:8000/api/agency_sections"
                sections_params = {"agency": selected_agency, "date": end_date.isoformat()}

                sections_response = requests.get(sections_url, params=sections_params)
                sections_response.raise_for_status()
                sections_data = sections_response.json()

                st.subheader(f"Latest chapters for {selected_agency} as of {end_date.isoformat()}")

                #st.write("Sections data:", sections_data["sections"]) #raw response for debug
                for i, (chapter_title, chapter_text) in enumerate(sections_data.get("sections", {}).items(), start=1):
                    #expander
                    with st.expander(f"{i}: {chapter_title}"):
                        #st.markdown(snippet)
                        if len(chapter_text) > 300:
                            #st.markdown("**Full Text:**")
                            st.text_area("Full Chapter Text", chapter_text, height=300, key=f"chapter_{i}")

            else:
                st.warning("No data available for selected agency and dates.")

        except requests.RequestException as e:
            st.error(f"Failed to load data: {e}")
