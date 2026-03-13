## Overview
This project collects Major League Baseball historical data (1990–2010) from Baseball Almanac, saves the raw scraped data as CSV files, imports the cleaned data into a SQLite database, provides a command-line query tool (including joins), and displays an interactive Streamlit dashboard with multiple visualizations.

## Data Source
- Baseball Almanac (Year-by-Year MLB pages)

## Project Requirements Covered
- **Program 1 (Web Scraping):** Selenium scraping + HTML parsing, saves raw CSVs
- **Program 2 (Database Import):** Cleans data, enforces numeric types, imports into SQLite
- **Program 3 (Database Query):** Command line queries + join query across tables
- **Program 4 (Dashboard):** Streamlit app with at least 3 visualizations + interactive controls
- **Documentation:** Setup steps + screenshot (included below)

## Repository Structure
- `01_scrape_mlb_history.py`  
  Scrapes Baseball Almanac year pages (1990–2010) using Selenium and saves raw CSV files to `data/raw/`.
- `02_import_sqlite.py`  
  Loads the raw CSVs, cleans and transforms data, enforces data types, and imports each dataset as a separate SQLite table.
- `03_query_db.py`  
  Command-line querying tool with filters and a join query.
- `04_dashboard.py`  
  Streamlit dashboard with interactive charts and event text explorer.
- `data/raw/`  
  Raw CSV output from Program 1.
- `db/mlb_history.sqlite`  
  SQLite database created by Program 2.

## Setup
### 1) Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate      # Windows