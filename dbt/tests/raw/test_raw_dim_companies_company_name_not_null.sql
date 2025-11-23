-- Test: Verify company_name is never null in raw_dim_companies
-- This ensures all companies have a name

select
    company_id,
    company_name
from {{ ref('raw_dim_companies') }}
where company_name is null

