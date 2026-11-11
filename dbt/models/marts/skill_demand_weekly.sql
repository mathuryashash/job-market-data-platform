-- skill_demand_weekly.sql: how many postings mention each skill per ISO week

{{ config(materialized='table') }}

with exploded as (
    select
        p.key,
        p.company,
        p.source,
        p.seniority,
        p.region,
        coalesce(p.posted_at, p.silver_date) as posting_date,
        -- DuckDB: unnest list column
        unnest(p.skills) as skill
    from {{ ref('stg_postings') }} p
    where len(p.skills) > 0
)

select
    date_trunc('week', posting_date)::date     as week_start,
    skill,
    count(distinct key)                        as postings_count,
    count(distinct company)                    as companies_count,
    -- entry-level breakdown
    count(distinct case when seniority in ('intern','new_grad','junior') then key end) as entry_level_count
from exploded
group by 1, 2
order by 1 desc, 3 desc
