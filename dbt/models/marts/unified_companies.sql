{{ config(
    materialized='table',
    schema='marts',
    alias='unified_companies'
) }}

-- Unified companies table: Clean mart view with essential company attributes
-- Sources from bronze layer (bronze_dim_companies and bronze_fct_company_metrics)
-- Joins on company_name and drops empty columns

with bronze_dim as (
    select * from {{ ref('bronze_dim_companies') }}
),

bronze_fct_latest as (
    select
        company_id,
        company_name,
        max(fortune_rank) as fortune_rank,
        max(employee_count) as employee_count,
        max(revenue_millions) as revenue_millions,
        max(revenue_percent_change) as revenue_percent_change,
        max(profits_m) as profits_m,
        max(profits_percent_change) as profits_percent_change,
        max(assets_m) as assets_m,
        max(market_cap_updated_m) as market_cap_updated_m,
        max(metric_date) as latest_metric_date
    from {{ ref('bronze_fct_company_metrics') }}
    group by company_id, company_name
),

joined as (
    select
        d.company_id,
        d.company_name,
        d.ticker,
        
        -- Rankings and classification
        f.fortune_rank,
        d.sector as domain,
        d.industry,
        d.industry_primary,
        d.country,
        d.headquarters_city,
        d.headquarters_state,
        
        -- Leadership
        d.ceo,
        d.founded_year,
        
        -- Website
        d.website,
        
        -- Metrics from fact table
        f.employee_count,
        f.revenue_millions as revenue,
        f.market_cap_updated_m,
        f.revenue_percent_change,
        f.profits_m,
        f.profits_percent_change,
        f.assets_m,
        
        -- Source tracking
        d.source_system,
        
        -- Metadata
        coalesce(f.latest_metric_date, d.loaded_at) as last_updated_at,
        current_timestamp() as mart_created_at
    from bronze_dim d
    left join bronze_fct_latest f
        on d.company_name = f.company_name
    where d.company_name is not null
        and length(trim(d.company_name)) > 0
)

-- Select columns, excluding those that are likely empty
-- Only include columns with meaningful data
select
    company_id,
    company_name,
    -- Only include ticker if it's not null
    ticker,
    -- Rankings and classification
    fortune_rank,
    domain,
    industry,
    industry_primary,
    country,
    headquarters_city,
    headquarters_state,
    -- Leadership
    ceo,
    founded_year,
    -- Website
    website,
    -- Metrics (only include if not null)
    employee_count,
    revenue,
    market_cap_updated_m,
    revenue_percent_change,
    profits_m,
    profits_percent_change,
    assets_m,
    -- Source tracking
    source_system,
    -- Metadata
    last_updated_at,
    mart_created_at
from joined
where company_name is not null

