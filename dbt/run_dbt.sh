#!/bin/bash
# Script to run dbt with proper environment variable loading from ~/.env

set -e

# Load environment variables from ~/.env file
if [ -f ~/.env ]; then
    export $(grep -v '^#' ~/.env | xargs)
else
    echo "Error: ~/.env file not found. Please create it with the required Snowflake credentials."
    echo "Required variables: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_PRIVATE_KEY_PATH, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_ROLE"
    exit 1
fi

# Validate required environment variables
required_vars=("SNOWFLAKE_ACCOUNT" "SNOWFLAKE_USER" "SNOWFLAKE_WAREHOUSE")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Required environment variable $var is not set in ~/.env"
        exit 1
    fi
done

# Change to dbt directory
cd "$(dirname "$0")"

echo "Running dbt..."

# Run dbt command with all arguments
dbt "$@"
