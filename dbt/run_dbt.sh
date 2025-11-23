#!/bin/bash
# Script to run dbt with proper environment variable loading from ~/.env

# Load environment variables from ~/.env file
if [ -f ~/.env ]; then
    set -a
    source ~/.env
    set +as
fi

# Change to dbt directory
cd "$(dirname "$0")"

# Export Snowflake variables explicitly
export SNOWFLAKE_ACCOUNT="${SNOWFLAKE_ACCOUNT:-NRKZBJU-LI37118}"
export SNOWFLAKE_USER="${SNOWFLAKE_USER:-DBT_COMPANY_ATLAS}"
export SNOWFLAKE_PASSWORD="${SNOWFLAKE_PASSWORD:-dbtCompanyAtlas123!}"
export SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-COMPUTE_WH}"
export SNOWFLAKE_ROLE="${SNOWFLAKE_ROLE:-TRANSFORM}"

echo "Running dbt with:"
echo "  Account: $SNOWFLAKE_ACCOUNT"
echo "  User: $SNOWFLAKE_USER"
echo "  Warehouse: $SNOWFLAKE_WAREHOUSE"
echo "  Role: $SNOWFLAKE_ROLE"
echo ""

# Run dbt command with all arguments
dbt "$@"
