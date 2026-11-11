-- entry_level_india_remote.sql: entry-level postings in India or remote

{{ config(materialized='table') }}

select
    key,
    company,
    source,
    title,
    seniority,
    region,
    is_remote,
    department,
    employment_type,
    posted_at,
    url,
    skills,
    skill_count
from {{ ref('stg_postings') }}
where
    seniority in ('intern', 'new_grad', 'junior', 'unknown')
    and (is_remote = true or region in ('india', 'india_remote', 'remote_global'))
order by posted_at desc nulls last
