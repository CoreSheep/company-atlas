-- Test: Verify fortune_rank is within valid range (1-1000)
-- This ensures all fortune ranks are within the expected Fortune 1000 range

select
    company_id,
    company_name,
    fortune_rank
from {{ ref('bronze_fct_company_metrics') }}
where fortune_rank is not null
    and (fortune_rank < 1 or fortune_rank > 1000)

