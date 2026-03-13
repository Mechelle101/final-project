
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

# The path to the SQLite database file
DB_PATH = Path("db/mlb_history.sqlite")

# Program 3 depends on the DB existing, 
# If it is missing the user needs to run Program 2 first
def require_db():
    """Check if the database file exists."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
          f"Database file not found at {DB_PATH}. Run file 02_import_sqlite.py first."
        )  

# Runs a query, returns the results as a pandas DataFrame
# Using pandas here makes printing results easier
def run_query(conn, sql, params):
    return pd.read_sql_query(sql, conn, params=params)
  
# 1) Build the command line UI
# argparse reads "python3 03_query_db.py
parser = argparse.ArgumentParser(
  description="Query the MLB history database."
)

# Subcommands, standings, leaders, join
subparsers = parser.add_subparsers(dest="command", required=True)

# ----------- Standings command -----------
p_standings = subparsers.add_parser("standings", help="Show standings for a year")
p_standings.add_argument("--year", type=int, required=True)
p_standings.add_argument("--division", type=str, default=None, help="East or West")
p_standings.add_argument("--team", type=str, default=None, help="Team name contains this text")
p_standings.add_argument("--top", type=int, default=10)

# ----------- Leaders command -----------
p_leaders = subparsers.add_parser("leaders", help="Show stat leaders for a year")
p_leaders.add_argument("--year", type=int, required=True)
p_leaders.add_argument("--type", choices=["hitting", "pitching"], required=True)
p_leaders.add_argument("--stat", type=str, required=True, help="Example: 'Home Runs' or 'ERA'")
p_leaders.add_argument("--player", type=str, default=None, help="Player name contains this text")
p_leaders.add_argument("--team", type=str, default=None, help="Team name contains this text")

# ----------- Events, (year in review) -----------
p_events = subparsers.add_parser("events", help="Query year in review text by year")
p_events.add_argument("--year", type=int, required=True)
p_events.add_argument("--section", type=str, default=None, help="Exact section title match")
p_events.add_argument("--keyword", type=str, default=None, help="Search text for keyword")

# ----------- Join command -----------
p_join = subparsers.add_parser("join", help="Join leader with year in review text")
p_join.add_argument("--year", type=int, required=True)
p_join.add_argument("--type", choices=["hitting", "pitching"], required=True)
p_join.add_argument("--stat", type=str, required=True)
p_join.add_argument("--keyword", type=str, default=None, help="Filter review text by keyword")

args = parser.parse_args()

# 2) Validate prerequisites
require_db()

# 3) Run the selected query
try:
  with sqlite3.connect(DB_PATH) as conn:
    # Standings query
    if args.command == "standings":
        sql = """
        SELECT Year, Division, Team, W, L, WP, GB, Payroll
        FROM standings
        WHERE Year = :year
        """
        params = {"year": args.year, "top": args.top}
        
        if args.division:
            sql += " AND lower(Division) = lower(:division) "
            params["division"] = args.division.lower()
            
        if args.team:
            sql += " AND lower(Team) LIKE lower(:team) "
            params["team"] = f"%{args.team}%"
            
        sql += " ORDER BY W DESC, Payroll DESC LIMIT :top "
        
        df = run_query(conn, sql, params)
        if df.empty:
            print("No standings results. Check year/division/team.")
        else:
            print(df.to_string(index=False))
        
    # Leaders query
    elif args.command == "leaders":
      table = "player_review" if args.type == "hitting" else "pitcher_review"
      
      # The stat value column is #
      # SQLite needs it to be quoted
      sql = f"""
      SELECT Year, Statistic, Name, Team, l."#" AS StatValue
      FROM {table} l
      WHERE Year = :year 
        AND lower(Statistic) = lower(:stat)
      """
      params = {"year": args.year, "stat": args.stat}
      
      if args.player:
          sql += " AND lower(Name) LIKE lower(:player) "
          params["player"] = f"%{args.player}%"
          
      if args.team:
          sql += " AND lower(Team) LIKE lower(:team) "
          params["team"] = f"%{args.team}%"
          
      sql += ' ORDER BY CAST(l."#" AS REAL) DESC '
      
      df = run_query(conn, sql, params)
      if df.empty:
          print("No leaders results. Check year/type/stat/player/team.")
      else:
          print(df.to_string(index=False))
      
    # Events query
    elif args.command == "events":
      sql = """
      SELECT Year, Section, Content
      FROM year_in_review
      WHERE Year = :year
      """
      params = {"year": args.year}
      
      if args.section:
          sql += " AND Section = :section "
          params["section"] = args.section
          
      if args.keyword:
          sql += " AND lower(Content) LIKE lower(:kw) "
          params["kw"] = f"%{args.keyword}%"
          
      sql += " ORDER BY Section "
          
      df = run_query(conn, sql, params)
      
      if df.empty:
          print("No events text results. Check year/section/keyword.")
      else:
          print(df.to_string(index=False))
      
# Join query
    elif args.command == "join":
      table = "player_review" if args.type == "hitting" else "pitcher_review"
      sql = f"""
      SELECT
        l.Year,
        l.Statistic,
        l.Name,
        l.Team,
        l."#" AS StatValue,
        r.Section,
        r.Content
      FROM {table} l
      JOIN year_in_review r 
        ON l.Year = r.Year
      WHERE l.Year = :year
        AND lower(l.Statistic) = lower(:stat)
      """
      params = {"year": args.year, "stat": args.stat}
      
      if args.keyword:
          sql += " AND lower(r.Content) LIKE lower(:kw) "
          params["kw"] = f"%{args.keyword}%"
        
      sql += " ORDER BY r.Section "
      
      df = run_query(conn, sql, params)
      
      if df.empty:
          print("No join results. Check year/type/stat/keyword.")
      else:
        # prevent printing large paragraphs
        df["Content"] = df["Content"].astype(str).str.slice(0, 100) + "..."
        print(df.to_string(index=False))
      
except sqlite3.Error as e:
    print(f"Database error: {e}")

