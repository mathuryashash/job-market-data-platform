-- fct_postings_daily.sql: fact table of postings per day

{{ config(materialized='table') }}

select
    coalesce(posted_at, silver_date)      as posting_date,
    source,
    region,
    seniority,
    employment_type,
    count(distinct key)                   as postings_count,
    count(distinct company)               as companies_count,
    sum(skill_count)                      as total_skills_mentioned
from {{ ref('stg_postings') }}
group by 1, 2, 3, 4, 5
