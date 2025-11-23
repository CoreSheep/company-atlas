-- SQL Script to Load Data from S3 to Snowflake Staging Tables
-- This script loads Parquet files from S3 into staging tables
-- Run this AFTER uploading Parquet files to S3

-- Step 1: Use the correct role and context
-- Use TRANSFORM role (or your assigned role) instead of ACCOUNTADMIN
USE ROLE TRANSFORM;
USE DATABASE COMPANY_ATLAS;
USE SCHEMA STAGING;

-- Step 2: Verify stage exists and create file format if needed
SHOW STAGES LIKE 'company_atlas_stage';

-- Drop and recreate CSV file format to ensure PARSE_HEADER is set
-- PARSE_HEADER = TRUE is required for MATCH_BY_COLUMN_NAME to work
-- Note: PARSE_HEADER automatically skips the header row, so SKIP_HEADER is not needed
DROP FILE FORMAT IF EXISTS csv_format;

CREATE FILE FORMAT csv_format
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    RECORD_DELIMITER = '\n'
    PARSE_HEADER = TRUE
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
    ESCAPE = 'NONE'
    ESCAPE_UNENCLOSED_FIELD = '\\'
    DATE_FORMAT = 'AUTO'
    TIMESTAMP_FORMAT = 'AUTO'
    NULL_IF = ('NULL', 'null', '\\N');

-- Step 2.5: Ensure table schema matches Parquet file structure
-- Add "industry.1" column to STG_GLOBAL_COMPANIES if it doesn't exist (to match Parquet file)
-- Note: This may require ACCOUNTADMIN or table owner privileges
-- If you get permission errors, ask your admin to run this:
-- ALTER TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES 
-- ADD COLUMN IF NOT EXISTS "industry.1" VARCHAR(255);

-- Step 3: List files in the stage to verify they exist
-- Note: If you get "stage does not exist" error, the stage needs to be created first by ACCOUNTADMIN
-- Run create_stage_and_load.sql as ACCOUNTADMIN to create the stage, or ask your admin
-- LIST commands may fail due to permissions, but COPY INTO will still work if stage exists
-- LIST '@company_atlas_stage/raw/fortune1000/';
-- LIST '@company_atlas_stage/raw/global_companies/';

-- Step 4: Truncate tables before loading (optional - remove if you want to append)
-- Uncomment the following lines if you want to truncate existing data:
-- TRUNCATE TABLE COMPANY_ATLAS.STAGING.STG_FORTUNE1000;
-- TRUNCATE TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES;

-- Step 5: Load STG_FORTUNE1000 from CSV
-- Files are in date-partitioned folders (e.g., 2025-11-23/)
-- Pattern matching will search in all subdirectories
COPY INTO COMPANY_ATLAS.STAGING.STG_FORTUNE1000
FROM '@company_atlas_stage/raw/fortune1000/'
FILE_FORMAT = csv_format
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
PATTERN = '.*/.*fortune1000_2024\.csv'
ON_ERROR = 'CONTINUE'
FORCE = TRUE;

-- Step 6: Load STG_GLOBAL_COMPANIES from CSV
-- Files are in date-partitioned folders (e.g., 2025-11-23/)
-- Pattern matching will search in all subdirectories
-- CSV file now has only one 'industry' column (duplicate removed)
-- Load data - MATCH_BY_COLUMN_NAME will match columns from CSV
COPY INTO COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES
FROM '@company_atlas_stage/raw/global_companies/'
FILE_FORMAT = csv_format
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
PATTERN = '.*/.*fortune1000_companies\.csv'
ON_ERROR = 'CONTINUE'
FORCE = TRUE;

-- Step 7: Verify data was loaded
SELECT 'STG_FORTUNE1000' AS table_name, COUNT(*) AS row_count 
FROM COMPANY_ATLAS.STAGING.STG_FORTUNE1000
UNION ALL
SELECT 'STG_GLOBAL_COMPANIES' AS table_name, COUNT(*) AS row_count 
FROM COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES;

-- Step 8: Show sample data
SELECT * FROM COMPANY_ATLAS.STAGING.STG_FORTUNE1000 LIMIT 5;
SELECT * FROM COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES LIMIT 5;

-- Step 9: Check for any errors in the copy
-- Note: COPY_HISTORY may have different column names depending on Snowflake version
-- If this fails, you can check manually in Snowsight under Data > Databases > COMPANY_ATLAS > STAGING > Tables > [Table Name] > Load History
SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'STG_FORTUNE1000',
    START_TIME => DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
))
ORDER BY LAST_LOAD_TIME DESC
LIMIT 5;

SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'STG_GLOBAL_COMPANIES',
    START_TIME => DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
))
ORDER BY LAST_LOAD_TIME DESC
LIMIT 5;

