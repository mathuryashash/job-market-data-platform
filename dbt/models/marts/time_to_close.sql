-- time_to_close.sql: estimate time-to-close for postings seen across multiple silver_dates
-- Since we typically have one snapshot, this will show first_seen = last_seen for most.
-- With multiple runs, the closed_at will be populated.

{{ config(materialized='table') }}

with daily_seen as (
    select
        key,
        company,
        title,
        seniority,
        region,
        source,
        min(coalesce(posted_at, silver_date))  as first_seen,
        max(silver_date)                        as last_seen_silver,
        count(distinct silver_date)             as days_observed
    from {{ ref('stg_postings') }}
    group by key, company, title, seniority, region, source
)

select
    *,
    -- If only 1 observation, we don't know if it's closed or still open
    case
        when days_observed = 1 then 'open'
        else 'tracked'
    end                                        as status,
    (last_seen_silver - first_seen)            as days_active
from daily_seen
order by days_active desc nulls last
