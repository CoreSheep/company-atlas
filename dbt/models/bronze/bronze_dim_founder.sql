{{ config(
    materialized='view',
    schema='bronze',
    alias='bronze_dim_founder'
) }}

-- Bronze Dimension Table: Founder information extracted from staging data
-- Creates founder dimension with id, company_name, and founder_name

with fortune1000_founders as (
    select
        md5(concat(
            coalesce(upper(trim(company)), ''),
            '|',
            coalesce(upper(trim(ticker)), ''),
            '|',
            coalesce(upper(trim(country)), '')
        )) as id,
        trim(upper(company)) as company_name,
        case 
            when founder_is_ceo = 'YES' and ceo is not null and trim(ceo) != ''
            then trim(ceo)
            else null
        end as founder_name
    from {{ source('staging', 'stg_fortune1000') }}
    where founder_is_ceo = 'YES'
        and ceo is not null
        and trim(ceo) != ''
        and company is not null
        and trim(company) != ''
),

global_companies_founders as (
    -- For global companies, we don't have founder info in the data
    -- This is a placeholder for future enrichment
    select
        md5(concat(
            coalesce(upper(trim(company_name)), ''),
            '|',
            coalesce(lower(trim(domain)), ''),
            '|',
            coalesce(upper(trim(country)), '')
        )) as id,
        trim(upper(company_name)) as company_name,
        null as founder_name
    from {{ source('staging', 'stg_global_companies') }}
    where 1 = 0  -- Exclude for now as we don't have founder data
),

unioned as (
    select * from fortune1000_founders
    union all
    select * from global_companies_founders
),

deduplicated as (
    select
        id,
        company_name,
        founder_name,
        row_number() over (
            partition by id
            order by 
                case when founder_name is not null then 0 else 1 end,
                company_name
        ) as rn
    from unioned
)

select
    id,
    company_name,
    founder_name,
    current_timestamp() as bronze_processed_at
from deduplicated
where rn = 1
    and founder_name is not null

