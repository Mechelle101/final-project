
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path("db/mlb_history.sqlite") 

st.set_page_config(page_title="MLB History Dashboard", layout="wide")
st.title("MLB History Dashboard")

# stop if the db is missing
if not DB_PATH.exists():
    st.error(f"Database not found at {DB_PATH}. Please run the data collection script first.")
    st.stop()
    
# load tables from sqlite
with sqlite3.connect(DB_PATH) as conn:
  standings = pd.read_sql_query("SELECT * FROM standings", conn)
  year_in_review = pd.read_sql_query("SELECT * FROM year_in_review", conn)
  
  # "#" = StatValue
  player_review = pd.read_sql_query(
    'SELECT Year, Statistic, Name, Team, "#" AS StatValue FROM player_review',
  conn
  )
  pitcher_review = pd.read_sql_query(
    'SELECT Year, Statistic, Name, Team, "#" AS StatValue FROM pitcher_review',
  conn
  )
  
# prevent empty filters
standings["Year"] = pd.to_numeric(standings["Year"], errors="coerce")
year_in_review["Year"] = pd.to_numeric(year_in_review["Year"], errors="coerce")

# Drop columns that are completely empty
standings = standings.dropna(axis=1, how="all")

# Drop columns with missing/null columns names
standings = standings.loc[:, standings.columns.notnull()]

# If a column named "nan" exists, drop it
standings = standings.drop(columns=["nan"], errors="ignore")

# Drop empty "Ties" column
if "Ties" in standings.columns:
  ties = standings["Ties"]
  ties_missing = ties.isna() | ties.astype(str).str.strip().str.lower().isin({"none", "nan", ""})
  if ties_missing.all():
    standings = standings.drop(columns=["Ties"])
  
st.subheader("Load Tables")
st.write("Standings:", len(standings))
st.write("Year in Review:", len(year_in_review))
st.write("Player Review:", len(player_review))
st.write("Pitcher Review:", len(pitcher_review))

st.subheader("Standings Overview preview")

# Making a copy for display purposes
standings_display = standings.copy()

# Renaming the columns for better readability
standings_display = standings_display.rename(columns={
  "Year": "Season",
  "Division": "Division",
  "Team": "Team",
  "W": "Wins",
  "L": "Losses",
  "WP": "Win %",
  "GB": "Games Back",
  "Payroll": "Payroll (USD)",
})

# Format Win % to 1 decimal places
if "Win %" in standings_display.columns:
    standings_display["Win %"] = pd.to_numeric(standings_display["Win %"], errors="coerce")
    standings_display["Win %"] = standings_display["Win %"].apply(
      lambda x: f"{x:.1%}" if pd.notna(x) else x
    )

# Format for currency visualization, adding commas and dollar sign 
if "Payroll (USD)" in standings_display.columns:
    payroll_num = pd.to_numeric(standings_display["Payroll (USD)"], errors="coerce")
    standings_display["Payroll (USD)"] = payroll_num.apply(
      lambda x: f"${int(x):,}" if pd.notna(x) else x
    )

if {"Season", "Division", "Wins"}.issubset(set(standings_display.columns)):
  standings_display = standings_display.sort_values(
    ["Season", "Division", "Wins"],
    ascending=[False, True, False]
  )

st.dataframe(standings_display.head(100), use_container_width=True)

st.header("Standings Insights")

# Year dropdown (interactive control)
years = standings["Year"].dropna().unique().tolist()
years = sorted([int(y) for y in years])

if not years:
  st.error("No valid years found in standings.")
  st.stop()

selected_year = st.selectbox("Select season", years, index=len(years)-1)

# Filter to selected year
standings_year = standings[standings["Year"] == selected_year].copy()

st.subheader(f"Payroll vs Wins - {selected_year}")

# Ensure numeric 
standings_year["Payroll"] = pd.to_numeric(standings_year.get("Payroll"), errors="coerce")
standings_year["W"] = pd.to_numeric(standings_year.get("W"), errors="coerce")

# Scatter plot of Payroll vs Wins
plot_df = standings_year.dropna(subset=["Payroll", "W", "Team"]).copy()

if plot_df.empty:
  st.info("No payroll/wins data available for that season.")
else:
  fig = px.scatter(
    plot_df,
    x="Payroll",
    y="W",
    hover_name="Team",
    title="Do higher payroll teams win more?",
    labels={
      "Payroll": "Payroll (USD)", 
      "W": "Wins",
      },
  )
  st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader(f"Team Wins Trend")

# Year range slider
min_year = int(standings["Year"].min())
max_year = int(standings["Year"].max())

year_range = st.slider(
  "Select year range (standings)", 
  min_year, 
  max_year, 
  (min_year, max_year)
)

# Team dropdown
teams = sorted(standings["Team"].dropna().unique().tolist())
selected_team = st.selectbox("Select team", teams)

# Filter data for team and range
team_df = standings[
  (standings["Team"] == selected_team) &
  (standings["Year"] >= year_range[0]) &
  (standings["Year"] <= year_range[1])
].copy()

team_df["W"] = pd.to_numeric(team_df["W"], errors="coerce")
team_df = team_df.dropna(subset=["Year", "W"]).sort_values("Year")

# Line chart
if team_df.empty:
  st.info("No data available for this team and year range.")
else:
  fig2 = px.line(
    team_df, 
    x="Year", 
    y="W", 
    title=f"{selected_team} Wins ({year_range[0]} - {year_range[1]})",
    labels={"Year": "Season", "W": "Wins"}
  )
  st.plotly_chart(fig2, use_container_width=True)
  
st.divider()
st.subheader("Stat Leaders Trend (1990-2010)")

# Picking the dataset to use
stat_type = st.radio("Choose Dataset", ["Hitting", "Pitching"], horizontal=True)
review_df = player_review if stat_type == "Hitting" else pitcher_review

# copying review df and enforcing types
review_df = review_df.copy()
review_df["Year"] = pd.to_numeric(review_df["Year"], errors="coerce")
review_df["StatValue"] = pd.to_numeric(review_df["StatValue"], errors="coerce")
review_df["Statistic"] = review_df["Statistic"].astype(str).str.strip()
review_df["Name"] = review_df["Name"].astype(str).str.strip()
review_df["Team"] = review_df["Team"].astype(str).str.strip()

# # Remove junk rows just in case
junk_pattern = r"\||Year-by-Year|Requirements|Rookies|History"
review_df = review_df[~review_df["Statistic"].str.contains(junk_pattern, case=False, na=False)]

# Separate year slider for stat dropdown
min_stat_year = int(review_df["Year"].min())
max_stat_year = int(review_df["Year"].max())
default_start = max(min_stat_year, 1990)
default_end = min(max_stat_year, 2010)
if default_start > default_end:
  default_start, default_end = min_stat_year, max_stat_year
  
stat_year_range = st.slider(
  "Select year range (leaders)",
  min_stat_year,
  max_stat_year,
  (default_start, default_end)
)

# Build stat dropdown
stats = sorted(review_df["Statistic"].dropna().unique().tolist())
selected_stat = st.selectbox("Select a stat", stats)

trend_df = review_df[
  (review_df["Statistic"].str.lower() == str(selected_stat).lower())
  & (review_df["Year"] >= stat_year_range[0])
  & (review_df["Year"] <= stat_year_range[1])
].dropna(subset=["Year", "StatValue", "Name", "Team"]).copy()

if trend_df.empty:
  st.info("No data for that stat in the selected range.")
else:
  # Hover label
  trend_df["Leader"] = trend_df["Name"] + " (" + trend_df["Team"] + ")"
  trend_df = trend_df.sort_values("Year")
  
  fig3 = px.line(
    trend_df,
    x="Year",
    y="StatValue",
    markers=True,
    hover_name="Leader",
    title=f"{stat_type} - {selected_stat} leader value by year ({stat_year_range[0]}-)({stat_year_range[1]}",
    labels={"Year": "Season", "StatValue": selected_stat},
  )
  st.plotly_chart(fig3, use_container_width=True)
  # Show the exact leader each year
  st.dataframe(trend_df[["Year", "Leader", "StatValue"]].reset_index(drop=True),
  use_container_width=True)
  
st.divider()
st.subheader(f"Year-in-Review (Events) - {selected_year}")
  
# Build section dropdown from the data
sections = sorted(year_in_review["Section"].dropna().unique().tolist())
selected_section = st.selectbox("Select event section", sections)
  
events = year_in_review[
  (year_in_review["Year"] == selected_year) &
  (year_in_review["Section"] == selected_section) 
].copy()
  
if events.empty:
  st.info("No event text found for that year/section.")
else:
  st.text_area("Event text", value=str(events["Content"].iloc[0]), height=250)
