{{ config(
    materialized='table',
    schema='raw',
    alias='raw_dim_companies'
) }}

-- Raw Dimension Table: Company master data from STAGING tables
-- Reads from STG_FORTUNE1000 and STG_GLOBAL_COMPANIES staging tables
-- Handles null values and deduplicates companies across both sources

with fortune1000 as (
    select
        -- Generate unified company ID using company_name and country (for matching with global_companies)
        md5(concat(
            coalesce(upper(trim(company)), ''),
            '|',
            coalesce(upper(trim(country)), '')
        )) as company_id,
        
        -- Primary identifiers
        trim(upper(company)) as company_name,
        nullif(trim(ticker), '') as ticker,
        
        -- Industry classification
        nullif(trim(sector), '') as sector,
        -- Industry from fortune1000 source
        nullif(trim(industry), '') as industry,
        nullif(trim(industry), '') as industry_primary,
        null as industry_secondary,
        
        -- Location
        nullif(trim(upper(country)), '') as country,
        nullif(trim(headquarterscity), '') as headquarters_city,
        nullif(trim(headquartersstate), '') as headquarters_state,
        
        -- Company attributes
        nullif(trim(ceo), '') as ceo,
        
        -- Website
        nullif(trim(website), '') as website,
        
        -- Founded year (not available in fortune1000 source)
        cast(null as integer) as founded_year,
        cast(null as date) as founded_year_date,
        
        -- Financial metrics removed from fortune1000
        cast(null as integer) as employee_count,
        cast(null as float) as revenue,
        
        -- Source tracking
        'kaggle: https://www.kaggle.com/datasets/jeannicolasduval/2024-fortune-1000-companies' as source_system,
        
        -- Metadata
        current_timestamp() as loaded_at
    from {{ source('staging', 'stg_fortune1000') }}
    where company is not null
        and trim(company) != ''
),

global_companies as (
    select
        -- Generate unified company ID (using company_name and country for matching)
        md5(concat(
            coalesce(upper(trim(company_name)), ''),
            '|',
            coalesce(upper(trim(country)), '')
        )) as company_id,
        
        -- Primary identifiers - need company_name for matching with fortune1000
        trim(upper(company_name)) as company_name,
        null as ticker,
        
        -- Industry classification - select industry from source
        null as sector,
        nullif(trim(industry), '') as industry,
        nullif(trim(industry), '') as industry_primary,
        null as industry_secondary,
        
        -- Location - country selected from source (needed for matching)
        nullif(trim(upper(country)), '') as country,
        null as headquarters_city,
        null as headquarters_state,
        
        -- Company attributes (not in source selection)
        null as ceo,
        
        -- Website - select domain from source
        nullif(trim(domain), '') as website,
        
        -- Founded year - ONLY founded_year selected from source (this is what we want to enrich)
        founded_year,
        cast(null as date) as founded_year_date,
        
        -- Financial metrics (not in source selection)
        cast(null as integer) as employee_count,
        cast(null as float) as revenue,
        
        -- Source tracking - ONLY source_system selected from source
        coalesce(nullif(trim(source_system), ''), 'global_companies') as source_system,
        
        -- Metadata - ONLY last_updated_at selected from source, converted to loaded_at
        coalesce(
                    try_to_timestamp_ntz(
                nullif(trim(last_updated_at), ''),
                'YYYY-MM-DD"T"HH24:MI:SS.FF'
            ),
            try_to_timestamp_ntz(
                nullif(trim(last_updated_at), ''),
                'YYYY-MM-DD"T"HH24:MI:SS'
                ),
                current_timestamp()
        ) as loaded_at
    from {{ source('staging', 'stg_global_companies') }}
    -- Selecting: company_name (for matching), country, industry, founded_year, source_system, last_updated_at
    where company_name is not null
        and trim(company_name) != ''
        and country is not null
        and trim(country) != ''
),

-- Enrich fortune1000 with founded_year from global_companies by matching on company_name
enriched_fortune1000 as (
    select
        f.company_id,
        f.company_name,
        f.ticker,
        f.sector,
        f.industry,
        f.industry_primary,
        f.industry_secondary,
        f.country,
        f.headquarters_city,
        f.headquarters_state,
        f.ceo,
        -- Use website from global_companies if fortune1000 doesn't have it, otherwise prefer fortune1000
        coalesce(f.website, g.website) as website,
        -- Use founded_year from global_companies if available, otherwise null
        coalesce(g.founded_year, f.founded_year) as founded_year,
        f.founded_year_date,
        f.employee_count,
        f.revenue,
        f.source_system,
        f.loaded_at
    from fortune1000 f
    left join global_companies g
        on upper(trim(f.company_name)) = upper(trim(g.company_name))
        and upper(trim(f.country)) = upper(trim(g.country))
),

unioned as (
    select * from enriched_fortune1000
    union all
    -- Only include global_companies records that don't match any fortune1000 company
    select g.*
    from global_companies g
    where not exists (
        select 1
        from fortune1000 f
        where upper(trim(f.company_name)) = upper(trim(g.company_name))
        and upper(trim(f.country)) = upper(trim(g.country))
    )
),

-- Handle null values and normalize
normalized as (
    select
        company_id,
        company_name,
        coalesce(ticker, 'UNKNOWN') as ticker,
        coalesce(sector, 'UNKNOWN') as sector,
        coalesce(industry, industry_primary, 'UNKNOWN') as industry,
        industry_primary,
        industry_secondary,
        coalesce(country, 'UNKNOWN') as country,
        headquarters_city,
        headquarters_state,
        ceo,
        website,
        founded_year,
        founded_year_date,
        employee_count,
        revenue,
        source_system,
        loaded_at
    from unioned
),

-- Deduplicate: prefer records with more complete data, especially founded_year
-- Partition by both company_id and company_name to catch duplicates
deduplicated as (
    select
        *,
        row_number() over (
            partition by company_id, company_name
            order by
                -- Prefer records with founded_year (this ensures we keep enriched records)
                case when founded_year is not null then 0 else 1 end,
                -- Prefer records with ticker (more complete fortune1000 data)
                case when ticker is not null and ticker != 'UNKNOWN' then 0 else 1 end,
                -- Prefer records with sector (more complete data)
                case when sector is not null and sector != 'UNKNOWN' then 0 else 1 end,
                -- Prefer records with more employee/revenue data
                case when employee_count > 0 then 0 else 1 end,
                case when revenue > 0 then 0 else 1 end,
                -- Prefer Kaggle Fortune 1000 data (but only if it has founded_year from enrichment)
                case when source_system like 'kaggle:%' and founded_year is not null then 0 
                     when source_system like 'kaggle:%' then 1
                     else 2 end,
                -- Prefer more recent updates
                loaded_at desc nulls last
        ) as rn
    from normalized
    where company_name is not null  -- Filter out any null company_names
)

select
    company_id,
    company_name,
    ticker,
    sector,
    industry,
    industry_primary,
    industry_secondary,
    country,
    headquarters_city,
    headquarters_state,
    ceo,
        website,
    founded_year,
    source_system,
    loaded_at,
    current_timestamp() as dim_created_at
from deduplicated
where rn = 1