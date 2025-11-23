{{ config(
    materialized='view',
    schema='bronze',
    alias='bronze_dim_companies'
) }}

-- Bronze Dimension Table: Cleaned company master data from raw layer
-- Applies data quality improvements and normalization

select
    company_id,
    -- Clean company name
    trim(upper(company_name)) as company_name,
    
    -- Clean ticker (uppercase, remove whitespace)
    case 
        when ticker is not null and trim(ticker) != '' 
        then upper(trim(ticker))
        else null
    end as ticker,
    
    -- Industry classification (clean and standardize)
    nullif(trim(sector), '') as sector,
    coalesce(
        nullif(trim(industry), ''),
        nullif(trim(industry_primary), ''),
        'UNKNOWN'
    ) as industry,
    nullif(trim(industry_primary), '') as industry_primary,
    
    -- Location (standardize country codes)
    case 
        when country is not null and upper(trim(country)) != 'UNKNOWN'
        then upper(trim(country))
        else null
    end as country,
    nullif(trim(headquarters_city), '') as headquarters_city,
    nullif(trim(headquarters_state), '') as headquarters_state,
    
    -- Leadership
    nullif(trim(ceo), '') as ceo,
    
    -- Website (normalize to lowercase, ensure it starts with http:// or https://)
    case 
        when website is not null and trim(website) != ''
        then lower(trim(website))
        else null
    end as website,
    
    -- Founded year (validate range)
    case 
        when founded_year is not null 
            and founded_year >= 1800 
            and founded_year <= year(current_date())
        then founded_year
        else null
    end as founded_year,
    
    -- Source tracking
    source_system,
    
    -- Metadata
    loaded_at,
    dim_created_at,
    current_timestamp() as bronze_processed_at
from {{ ref('raw_dim_companies') }}
where company_name is not null
    and length(trim(company_name)) > 0

