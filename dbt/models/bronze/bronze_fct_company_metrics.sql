{{ config(
    materialized='view',
    schema='bronze',
    alias='bronze_fct_company_metrics'
) }}

-- Bronze Fact Table: Cleaned company metrics from raw layer
-- Applies data quality improvements and standardization

select
    company_id,
    company_name,
    
    -- Fortune rank (validate range 1-1000)
    case 
        when fortune_rank is not null 
            and fortune_rank >= 1 
            and fortune_rank <= 1000
        then fortune_rank
        else null
    end as fortune_rank,
    
    -- Employee count (ensure non-negative)
    case 
        when employee_count is not null and employee_count >= 0
        then employee_count
        else null
    end as employee_count,
    
    -- Revenue metrics (ensure non-negative)
    case 
        when revenue_millions is not null and revenue_millions >= 0
        then revenue_millions
        else null
    end as revenue_millions,
    
    revenue_percent_change,
    profits_m,
    profits_percent_change,
    assets_m,
    market_cap_updated_m,
    
    -- Metric date (validate)
    case 
        when metric_date is not null 
            and metric_date >= dateadd(year, -10, current_date())
            and metric_date <= current_date()
        then metric_date
        else current_date()
    end as metric_date,
    
    -- Source tracking
    source_system,
    
    -- Metadata
    loaded_at,
    current_timestamp() as bronze_processed_at
from {{ ref('raw_fct_company_metrics') }}
where company_id is not null
    and company_name is not null
    and length(trim(company_name)) > 0

