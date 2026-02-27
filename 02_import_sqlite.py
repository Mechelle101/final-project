
import sqlite3
from pathlib import Path

import pandas as pd

# inputs from program 1
RAW_DIR = Path("data/raw")
PLAYER_CSV = RAW_DIR / "player_review_raw.csv"
PITCHER_CSV = RAW_DIR / "pitcher_review_raw.csv"
STANDINGS_CSV = RAW_DIR / "standings_raw.csv"
REVIEW_CSV = RAW_DIR / "year_in_review_raw.csv"

# Output for program 2
DB_DIR = Path("db")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "mlb_history.sqlite" 

def require_file(path: Path) -> None:
  if not path.exists():
    raise FileNotFoundError(f"Required file not found: {path}")
  
def to_int(series: pd.Series) -> pd.Series:
    """Convert a pandas Series to integer, handling errors."""
    return pd.to_numeric(series, errors='coerce').astype('Int64')

def to_float(series: pd.Series) -> pd.Series:
    """Convert a pandas Series to float, handling errors."""
    return pd.to_numeric(series, errors='coerce')
  
def clean_money(series: pd.Series) -> pd.Series:
    """Remove dollar signs and commas from a pandas Series and convert to float."""
    s = series.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors='coerce')
  
def clean_player_pitcher(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # strip whitespace in text columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
            
    # enforce types, int or decimal as appropriate
    df["Year"] = to_int(df["Year"])
    df["#"] = to_float(df["#"])
    
    # remove rows missing required fields
    df = df.dropna(subset=["Year", "Statistic", "Name", "Team"]).reset_index(drop=True)
    return df
  
def cleaning_standings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # strip whitespace in text columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
            
    # enforce types, int or decimal as appropriate
    df["Year"] = to_int(df["Year"])
    df["W"] = to_int(df["W"])
    df["L"] = to_int(df["L"])
    df["WP"] = to_float(df["WP"])
    df["GB"] = to_float(df["GB"])
    df["Payroll"] = clean_money(df["Payroll"])
    
    # remove rows missing required fields
    df = df.dropna(subset=["Year", "Division", "Team", "W", "L"]).reset_index(drop=True)
    return df
  
def clean_year_in_review(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # strip whitespace in text columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
            
    # enforce types, int or decimal as appropriate
    df["Year"] = to_int(df["Year"])
    
    # remove rows missing required fields
    df = df.dropna(subset=["Year", "Section", "Content"]).reset_index(drop=True)
    return df
  
def import_table(conn: sqlite3.Connection, df: pd.DataFrame, table_name: str) -> None:
    """Import a DataFrame into a SQLite database table."""
    if df.empty:
        raise ValueError(f"{table_name} is empty after cleaning. Import aborted.")
    
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    # verify row counts match
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    db_count = cur.fetchone()[0]
    if db_count != len(df):
        raise RuntimeError(f"Row count mismatch for {table_name}: df={len(df)} db={db_count}")

# --------------- Program 2 ---------------

# 1) Verify required scv files exist
for p in [PLAYER_CSV, PITCHER_CSV, STANDINGS_CSV, REVIEW_CSV]:
    require_file(p)
    
# 2) Load raw CSVs
players_raw = pd.read_csv(PLAYER_CSV)
pitchers_raw = pd.read_csv(PITCHER_CSV)
standings_raw = pd.read_csv(STANDINGS_CSV)
review_raw = pd.read_csv(REVIEW_CSV)

print("Load raw shapes:")
print("Players:", players_raw.shape)
print("Pitchers:", pitchers_raw.shape)
print("Standings:", standings_raw.shape)
print("year_in_review:", review_raw.shape)

# 3) Clean & enforce types
player = clean_player_pitcher(players_raw)
pitcher = clean_player_pitcher(pitchers_raw)
standings = cleaning_standings(standings_raw)
year_in_review = clean_year_in_review(review_raw)

print("After cleaning shapes:")
print("Players:", player.shape)
print("Pitchers:", pitcher.shape)
print("Standings:", standings.shape)
print("year_in_review:", year_in_review.shape)

# 4) Rebuild SQLite database fresh each run
if DB_PATH.exists():
    DB_PATH.unlink()
    
with sqlite3.connect(DB_PATH) as conn:
  # 5) import each csv as its own table
    import_table(conn, player, "player_review")
    import_table(conn, pitcher, "pitcher_review")
    import_table(conn, standings, "standings")
    import_table(conn, year_in_review, "year_in_review")
    
    # 6) Proof query (verify the db is readable & imported)
    top_teams = pd.read_sql_query(
      """
      SELECT Year, Division, Team, W, Payroll
      FROM standings
      WHERE Year = ?
      ORDER BY W DESC, Payroll DESC
      LIMIT 5
      """,
      conn,
      params=(1991,),
    )
    
    
    print(f"\nSQLite BD created at: {DB_PATH}")
    print("Top 5 teams in 1991 by wins:")
    print(top_teams.to_string(index=False))
