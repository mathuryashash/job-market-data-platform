"""
Streamlit dashboard for the job-market-data-platform.
Reads from DuckDB marts (built by dbt).
Port: 18300.

Run:
    streamlit run dashboard/app.py --server.port 18300
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Job Market Data Platform",
    page_icon="📊",
    layout="wide",
)

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dbt/job_market.duckdb")


@st.cache_resource
def get_conn():
    import duckdb
    if not Path(DUCKDB_PATH).exists():
        return None
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    return conn


def query(sql: str):
    import pandas as pd
    conn = get_conn()
    if conn is None:
        return pd.DataFrame()
    try:
        return conn.execute(sql).df()
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()


st.title("Job Market Data Platform")
st.caption("Public job posting data from Greenhouse, Lever, Ashby — batch pipeline with Kafka, Spark, dbt")

# ---------------------------------------------------------------------------
# Sidebar: filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    region_filter = st.multiselect(
        "Region",
        ["india", "india_remote", "remote_global", "us", "eu", "other", "unknown"],
        default=["india", "india_remote", "remote_global"],
    )
    seniority_filter = st.multiselect(
        "Seniority",
        ["intern", "new_grad", "junior", "mid", "senior", "manager", "unknown"],
        default=["intern", "new_grad", "junior"],
    )
    st.divider()
    st.markdown("**Data source**: DuckDB marts built by dbt")
    st.markdown(f"**DB path**: `{DUCKDB_PATH}`")

conn = get_conn()
if conn is None:
    st.warning(
        f"DuckDB file not found at `{DUCKDB_PATH}`. "
        "Run `make dbt-build` first to build the marts."
    )
    st.stop()

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
kpis = query("SELECT count(*) as total, count(distinct company) as companies, "
             "sum(case when is_remote then 1 else 0 end) as remote_count, "
             "sum(case when seniority in ('intern','new_grad','junior') then 1 else 0 end) as entry_level "
             "FROM stg_postings")
if not kpis.empty:
    col1.metric("Total Postings", f"{kpis['total'][0]:,}")
    col2.metric("Companies", f"{kpis['companies'][0]:,}")
    col3.metric("Remote", f"{kpis['remote_count'][0]:,}")
    col4.metric("Entry-Level", f"{kpis['entry_level'][0]:,}")

st.divider()

# ---------------------------------------------------------------------------
# Top Skills
# ---------------------------------------------------------------------------
st.subheader("Top 10 Skills in Demand")
region_sql = "','".join(region_filter) if region_filter else "''"
skills_df = query("""
    SELECT skill, sum(postings_count) as postings_count, sum(companies_count) as companies_count
    FROM skill_demand_weekly
    GROUP BY skill
    ORDER BY postings_count DESC
    LIMIT 10
""")
if not skills_df.empty:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.bar_chart(skills_df.set_index("skill")["postings_count"])
    with col_b:
        st.dataframe(skills_df, use_container_width=True, hide_index=True)
else:
    st.info("No skill data yet. Run the pipeline.")

# ---------------------------------------------------------------------------
# Entry-Level India / Remote
# ---------------------------------------------------------------------------
st.subheader("Entry-Level Roles — India / Remote")
entry_df = query("""
    SELECT company, title, region, seniority, posted_at, url
    FROM entry_level_india_remote
    ORDER BY posted_at DESC NULLS LAST
    LIMIT 50
""")
if not entry_df.empty:
    st.dataframe(entry_df, use_container_width=True, hide_index=True)
else:
    st.info("No entry-level India/Remote postings found.")

# ---------------------------------------------------------------------------
# Postings per day
# ---------------------------------------------------------------------------
st.subheader("Postings Opened Per Day")
daily_df = query("""
    SELECT posting_date, sum(postings_count) as postings_count
    FROM fct_postings_daily
    GROUP BY posting_date
    ORDER BY posting_date
""")
if not daily_df.empty:
    st.line_chart(daily_df.set_index("posting_date")["postings_count"])

# ---------------------------------------------------------------------------
# Top hiring companies
# ---------------------------------------------------------------------------
st.subheader("Top Hiring Companies")
company_df = query("""
    SELECT company, source, total_postings, remote_postings, india_postings, entry_level_postings
    FROM dim_company
    ORDER BY total_postings DESC
    LIMIT 20
""")
if not company_df.empty:
    st.dataframe(company_df, use_container_width=True, hide_index=True)
