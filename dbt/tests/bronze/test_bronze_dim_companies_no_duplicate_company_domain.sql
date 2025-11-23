-- Test: Check for duplicate company_name + country combinations in bronze_dim_companies
-- This ensures we don't have duplicate companies with the same name and country
-- Note: domain column was removed from bronze_dim_companies

select
    company_name,
    country,
    count(*) as duplicate_count
from {{ ref('bronze_dim_companies') }}
group by company_name, country
having count(*) > 1

