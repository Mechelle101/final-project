
import time
from io import StringIO
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

YEAR_MENU_URL = "https://www.baseball-almanac.com/yearmenu.shtml"
YEAR_URL = "https://www.baseball-almanac.com/yearly/yr1991a.shtml"

START_YEAR = 1991
END_YEAR = 1992

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

def build_driver(headless=True):
    options = Options()
    if headless: 
      options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    
    # User-agent header (mimics a real browser)
    options.add_argument(
      "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36"
    )
    
    return webdriver.Chrome(
      service=Service(ChromeDriverManager().install()), 
      options=options
    )
    
def get_al_year_links(driver):
    driver.get(YEAR_MENU_URL)
    time.sleep(1.0)  # Wait for the page to load
        
    soup = BeautifulSoup(driver.page_source, "html.parser")
    year_links = {}
        
    # the American League links are /year/yr1991a.shtml
    for a in soup.select("a[href*='yearly/yr'][href$='a.shtml']"):
        txt = (a.get_text() or "").strip()
        href = a.get("href", "").strip()
            
        if txt.isdigit():
          year = int(txt)
          
          # Keep only american league years
          if year >= 1901:
            if href.startswith("/"):
              href = "https://www.baseball-almanac.com" + href
            elif not href.startswith("http"):
              href = "https://www.baseball-almanac.com/" + href
            
            year_links[year] = href
            
    return year_links
  
def clean_review_table(df, year):
  cleaned =  df.copy()
  
  # row 0 = title row, row 1 = real header row
  cleaned.columns = cleaned.iloc[1]
  cleaned = cleaned.iloc[2:].reset_index(drop=True)
  cleaned.columns = [str(col).strip() for col in cleaned.columns]
  
  # removing repeated header/footer junk rows
  cleaned = cleaned[cleaned["Statistic"].notna()]
  cleaned = cleaned[cleaned["Name"].notna()]
  cleaned = cleaned[cleaned["Team"].notna()]
  cleaned = cleaned[cleaned["Statistic"] != "Statistic"]
  cleaned = cleaned[~cleaned["Statistic"].astype(str).str.contains("History", case=False, na=False)]
  cleaned = cleaned[~cleaned["Name"].astype(str).str.contains("History", case=False, na=False)]
  
  cleaned = cleaned.reset_index(drop=True)
  
  #  Adding year column here
  cleaned.insert(0, "Year", year)
  
  return cleaned
      
def clean_standings_table(df, year):
  cleaned =  df.copy()
  
  # row 0 = title row, row 1 = real header row
  cleaned.columns = cleaned.iloc[1]
  cleaned = cleaned.iloc[2:].reset_index(drop=True)
  
  # normalize column names
  cleaned.columns = [str(col).replace("\xa0", " ").strip() for col in cleaned.columns]
  
  # rename ugly names to clean ones
  div_col = cleaned.columns[0]
  team_col = cleaned.columns[1]
  cleaned = cleaned.rename(columns={
    div_col: "Division",
    team_col: "Team"
  })
  
  # normalize stat column names across years
  rename_map = {}
  for col in cleaned.columns:
    c = str(col).strip().lower()
    if c in ["wins", "win"]:
      rename_map[col] = "W"
    elif c in ["losses", "loss"]:
      rename_map[col] = "L"
    elif c in ["wp", "pct", "winning percentage", "winning pct"]:
      rename_map[col] = "WP"
    elif c in ["gb", "games back"]:
      rename_map[col] = "GB"
    elif c == "payroll":
      rename_map[col] = "Payroll"
      
  cleaned = cleaned.rename(columns=rename_map)
  
  # Keeping real team rows
  if "W" not in cleaned.columns:
    raise KeyError(f"Could not find W column after renaming. Columns are: {list(cleaned.columns)}")
  
  cleaned["W_num"] = pd.to_numeric(cleaned["W"], errors="coerce")
  cleaned = cleaned[cleaned["W_num"].notna()].drop(columns=["W_num"]).reset_index(drop=True)
  
  # Adding year column here
  cleaned.insert(0, "Year", year)
  
  return cleaned

def extract_year_in_review(soup, year):
  # section headings on the year page
  section_titles = [
    "Off the field...",
    "In the American League...",
    "In the National League...",
    "Around the league..."
  ]
  
  rows = []
  
  for title in section_titles:
    heading = soup.find(
      lambda tag: tag.name in ["h2", "h3"] and tag.get_text(strip=True) == title
    ) 
    
    # if a section is missing skip it
    if not heading:
      continue
    
    parts = []
    
    for sibling in heading.find_all_next():
      if sibling.name in ["h2", "h3"]:
        break
      
      if sibling.name == "p":
        text = sibling.get_text(strip=True)
        if text:
          parts.append(text)
          
    if parts:
      rows.append({
        "Year": year,
        "Section": title,
        "Content": "\n\n".join(parts)
      })
      
  return rows

driver = build_driver(headless=True)

try:
    year_links = get_al_year_links(driver)
    years = [year for year in sorted(year_links.keys()) if START_YEAR <= year <= END_YEAR]
  
    print(f"Found {len(year_links)} AL year links total.")
    print("Scraping years:", years)
    
    all_player_dfs = []
    all_pitcher_dfs = []
    all_standings_dfs = []
    all_review_rows = []
    
    for year in years:
      url = year_links[year]
      print(f"\nScraping {year}: {url}")
  
      driver.get(url)
      time.sleep(1.5)  # Wait for the page to load
      
      html = driver.page_source
      soup = BeautifulSoup(html, "html.parser")
      
      # Extract review content
      review_rows = extract_year_in_review(soup, year)
      all_review_rows.extend(review_rows)
      
      # Extract tables
      tables = pd.read_html(StringIO(html))
      
      player_df = None
      pitcher_df = None
      standings_df = None
      
      for df in tables:
        title_text = str(df.iloc[0, 0]).strip()
        
        if "Player Review" in title_text:
          player_df = clean_review_table(df, year)
          
        elif "Pitcher Review" in title_text:
          pitcher_df = clean_review_table(df, year)
            
        elif "Standings" in title_text:
          standings_df = clean_standings_table(df, year)
            
      if player_df is not None:
        all_player_dfs.append(player_df)
        
      if pitcher_df is not None:
        all_pitcher_dfs.append(pitcher_df)
        
      if standings_df is not None:
        all_standings_dfs.append(standings_df)
        
    # combine all years
    final_player_df = pd.concat(all_player_dfs, ignore_index=True) if all_player_dfs else pd.DataFrame()
    final_pitcher_df = pd.concat(all_pitcher_dfs, ignore_index=True) if all_pitcher_dfs else pd.DataFrame()
    final_standings_df = pd.concat(all_standings_dfs, ignore_index=True) if all_standings_dfs else pd.DataFrame()
    final_review_df = pd.DataFrame(all_review_rows)

    # overwrite files each run to avoid duplicates
    final_player_df.to_csv(RAW_DIR / "player_review_raw.csv", index=False)
    final_pitcher_df.to_csv(RAW_DIR / "pitcher_review_raw.csv", index=False)
    final_standings_df.to_csv(RAW_DIR / "standings_raw.csv", index=False)
    final_review_df.to_csv(RAW_DIR / "year_in_review_raw.csv", index=False)
    
    print("\nSaved:")
    print("data/raw/player_review_raw.csv")
    print("data/raw/pitcher_review_raw.csv")
    print("data/raw/standings_raw.csv")
    print("data/raw/year_in_review_raw.csv")
    
    print("\nPlayer Review rows:", len(final_player_df))
    print("Pitcher Review rows:", len(final_pitcher_df))
    print("Standings rows:", len(final_standings_df))
    print("Year in Review rows:", len(final_review_df))
    
    if not final_standings_df.empty:
      print("\nFinal Standings columns:", list(final_standings_df.columns))
    
    if not final_review_df.empty:
      print("Year in Review columns:", list(final_review_df.columns))
  
finally:    
    driver.quit()
