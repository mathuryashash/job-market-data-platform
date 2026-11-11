-- dim_company.sql: one row per company, aggregated stats

{{ config(materialized='table') }}

select
    company,
    source,
    count(distinct key)                                      as total_postings,
    count(distinct case when is_remote then key end)         as remote_postings,
    count(distinct case when region = 'india' or region = 'india_remote' then key end) as india_postings,
    count(distinct case when seniority in ('intern','new_grad','junior') then key end) as entry_level_postings,
    min(posted_at)                                           as earliest_posting,
    max(posted_at)                                           as latest_posting,
    max(silver_date)                                         as last_seen
from {{ ref('stg_postings') }}
group by company, source
