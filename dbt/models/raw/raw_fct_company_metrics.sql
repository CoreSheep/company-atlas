{{ config(
    materialized='table',
    schema='raw',
    alias='raw_fct_company_metrics'
) }}

-- Raw Fact Table: Company metrics and financial data from staging tables
-- Handles null values and deduplicates metrics by company and date

with fortune1000 as (
    select
        -- Generate company ID for joining
        md5(concat(
            coalesce(upper(trim(company)), ''),
            '|',
            coalesce(upper(trim(ticker)), ''),
            '|',
            coalesce(upper(trim(country)), '')
        )) as company_id,
        
        trim(upper(company)) as company_name,
        coalesce(rank, 0) as fortune_rank,
        coalesce(number_of_employees, 0) as employee_count,
        coalesce(revenues_m, 0) * 1000000 as revenue_millions,
        coalesce(revenuepercentchange, 0) as revenue_percent_change,
        coalesce(profits_m, 0) as profits_m,
        coalesce(profitspercentchange, 0) as profits_percent_change,
        coalesce(assets_m, 0) as assets_m,
        coalesce(marketcap_march28_m, 0) as market_cap_march_m,
        coalesce(marketcap_updated_m, 0) as market_cap_updated_m,
        coalesce(updated, current_date()) as metric_date,
        'fortune1000' as source_system,
        current_timestamp() as loaded_at
    from {{ source('staging', 'stg_fortune1000') }}
    where company is not null
        and trim(company) != ''
),

-- Handle null values
normalized as (
    select
        company_id,
        company_name,
        coalesce(fortune_rank, 0) as fortune_rank,
        employee_count,
        coalesce(revenue_millions, 0) as revenue_millions,
        coalesce(revenue_percent_change, 0) as revenue_percent_change,
        coalesce(profits_m, 0) as profits_m,
        coalesce(profits_percent_change, 0) as profits_percent_change,
        coalesce(assets_m, 0) as assets_m,
        coalesce(market_cap_march_m, 0) as market_cap_march_m,
        coalesce(market_cap_updated_m, 0) as market_cap_updated_m,
        coalesce(metric_date, current_date()) as metric_date,
        source_system,
        loaded_at
    from fortune1000
),

-- Deduplicate by company_id and metric_date: prefer Fortune 1000 data and more recent
deduplicated as (
    select
        *,
        row_number() over (
            partition by company_id, metric_date
            order by
                -- Prefer Fortune 1000 data (more detailed)
                case when source_system = 'fortune1000' then 0 else 1 end,
                -- Prefer records with more financial data
                case when revenue_millions > 0 then 0 else 1 end,
                case when employee_count > 0 then 0 else 1 end,
                -- Prefer more recent updates
                loaded_at desc nulls last
        ) as rn
    from normalized
)

select
    company_id,
    company_name,
    fortune_rank,
    employee_count,
    revenue_millions,
    revenue_percent_change,
    profits_m,
    profits_percent_change,
    assets_m,
    market_cap_march_m,
    market_cap_updated_m,
    metric_date,
    source_system,
    loaded_at
from deduplicated
where rn = 1

