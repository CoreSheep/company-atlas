-- Test: Verify founder_name is never null in bronze_dim_founder
-- This ensures all founder records have a name

select
    id,
    company_name,
    founder_name
from {{ ref('bronze_dim_founder') }}
where founder_name is null

