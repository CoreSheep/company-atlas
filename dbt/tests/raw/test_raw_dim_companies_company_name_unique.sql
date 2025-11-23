-- Test: Verify company_name is unique in raw_dim_companies
-- This ensures we don't have duplicate company names

select
    company_name,
    count(*) as duplicate_count
from {{ ref('raw_dim_companies') }}
group by company_name
having count(*) > 1

