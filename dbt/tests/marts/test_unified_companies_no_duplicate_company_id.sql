-- Test: Check for duplicate company_id in unified_companies
-- This ensures each company appears only once in the unified view

select
    company_id,
    count(*) as duplicate_count
from {{ ref('unified_companies') }}
group by company_id
having count(*) > 1

