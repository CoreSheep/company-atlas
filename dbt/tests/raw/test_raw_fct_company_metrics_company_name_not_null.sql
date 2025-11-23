-- Test: Verify company_name is never null in raw_fct_company_metrics
-- This ensures all fact records have a company name

select
    company_id,
    company_name
from {{ ref('raw_fct_company_metrics') }}
where company_name is null

