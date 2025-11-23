-- Test: Check for duplicate company_id + metric_date combinations in raw_fct_company_metrics
-- This ensures we don't have duplicate metrics for the same company on the same date

select
    company_id,
    metric_date,
    count(*) as duplicate_count
from {{ ref('raw_fct_company_metrics') }}
group by company_id, metric_date
having count(*) > 1

