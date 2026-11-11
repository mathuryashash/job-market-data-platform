-- stg_postings.sql
-- Staging model: clean & validate postings from silver layer.
-- In CI/tests (var use_fixture=true), reads from postings_fixture seed.
-- In production, reads from the silver source (Parquet via DuckDB httpfs).

{{ config(materialized='view') }}

{% if var('use_fixture', false) %}
  {%- set source_rel = ref('postings_fixture') -%}
{% else %}
  {%- set source_rel = source('silver', 'postings') -%}
{% endif %}

with raw as (
    select * from {{ source_rel }}
),

cleaned as (
    select
        key,
        source,
        company,
        external_id,
        title,
        -- Coerce nulls
        coalesce(department, '')         as department,
        coalesce(employment_type, 'unknown') as employment_type,
        coalesce(seniority, 'unknown')   as seniority,
        coalesce(is_remote, false)       as is_remote,
        coalesce(region, 'unknown')      as region,
        -- Date fields: reject future dates (> today + 1 day tolerance)
        case
            when posted_at > current_date + interval '1 day' then null
            else cast(posted_at as date)
        end as posted_at,
        case
            when updated_at > current_date + interval '1 day' then null
            else cast(updated_at as date)
        end as updated_at,
        url,
        -- skills: normalize to list regardless of source format.
        -- CSV seeds produce VARCHAR; real silver produces VARCHAR[].
        -- Cast everything through regexp_extract_all via try_cast to string first.
        regexp_extract_all(
            coalesce(skills::varchar, '[]'),
            '[''\"](.*?)[''\"]+',
            1
        )                                as skills,
        len(regexp_extract_all(
            coalesce(skills::varchar, '[]'),
            '[''\"](.*?)[''\"]+',
            1
        ))                               as skill_count,
        silver_date::date                as silver_date
    from raw
    where
        -- Basic quality gate: must have a title and company
        title is not null
        and trim(title) != ''
        and company is not null
        and trim(company) != ''
)

select * from cleaned
