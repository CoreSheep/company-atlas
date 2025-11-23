-- SQL Script to Create S3 Stage and Load Fortune 1000 Data into Snowflake
-- This script creates an external stage, staging tables, and loads data from S3

-- Step 1: Use the correct role and context
-- IMPORTANT: If you get permission errors, run this script as ACCOUNTADMIN
-- Or run grant_privileges.sql first as ACCOUNTADMIN to grant privileges to TRANSFORM role

-- Option 1: Use ACCOUNTADMIN (recommended for initial setup)
USE ROLE ACCOUNTADMIN;

-- Option 2: Use TRANSFORM role (if privileges are already granted)
-- USE ROLE TRANSFORM;

USE DATABASE COMPANY_ATLAS;
USE SCHEMA STAGING;

-- Verify we can access the schema
SHOW SCHEMAS IN DATABASE COMPANY_ATLAS;

-- Step 2: Create an external stage for S3 data ingestion
-- Using the company-atlas bucket with year-month format
-- NOTE: Replace AWS_KEY_ID and AWS_SECRET_KEY with your actual AWS credentials
-- These should be stored in environment variables and not committed to git
CREATE OR REPLACE STAGE company_atlas_stage
    URL = 's3://company-atlas-202511/'
    CREDENTIALS = (
        AWS_KEY_ID='YOUR_AWS_ACCESS_KEY_ID' 
        AWS_SECRET_KEY='YOUR_AWS_SECRET_ACCESS_KEY'
    )
    COMMENT='S3 stage for Company Atlas raw data';

-- Verify the stage was created
SHOW STAGES LIKE 'company_atlas_stage';

-- Step 3: Create staging table for Fortune 1000 data (from fortune1000_2024.csv)
-- This matches the actual schema of the Fortune 1000 2024 dataset
-- Using fully qualified table name to ensure it's created in the correct schema
CREATE OR REPLACE TABLE COMPANY_ATLAS.STAGING.STG_FORTUNE1000 (
    Rank INTEGER,
    Company VARCHAR(255),
    Ticker VARCHAR(20),
    Sector VARCHAR(100),
    Industry VARCHAR(255),
    Profitable VARCHAR(10),
    Founder_is_CEO VARCHAR(10),
    FemaleCEO VARCHAR(10),
    Growth_in_Jobs VARCHAR(10),
    Change_in_Rank FLOAT,
    Gained_in_Rank VARCHAR(10),
    Dropped_in_Rank VARCHAR(10),
    Newcomer_to_the_Fortune500 VARCHAR(10),
    Global500 VARCHAR(10),
    Worlds_Most_Admired_Companies VARCHAR(10),
    Best_Companies_to_Work_For VARCHAR(10),
    Number_of_employees BIGINT,
    MarketCap_March28_M FLOAT,
    Revenues_M FLOAT,
    RevenuePercentChange FLOAT,
    Profits_M FLOAT,
    ProfitsPercentChange FLOAT,
    Assets_M FLOAT,
    CEO VARCHAR(255),
    Country VARCHAR(100),
    HeadquartersCity VARCHAR(100),
    HeadquartersState VARCHAR(100),
    Website VARCHAR(500),
    CompanyType VARCHAR(50),
    Footnote VARCHAR(1000),
    MarketCap_Updated_M FLOAT,
    Updated DATE
);

-- Step 4: Create staging table for Global Companies data (from fortune1000_companies.csv)
-- This matches the actual schema of the normalized fortune1000_companies dataset
-- Using fully qualified table name to ensure it's created in the correct schema
CREATE OR REPLACE TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES (
    company_name VARCHAR(255),
    domain VARCHAR(500),
    industry VARCHAR(255),
    country VARCHAR(100),
    employee_count INTEGER,
    revenue FLOAT,
    founded_year INTEGER,
    source_system VARCHAR(100),
    last_updated_at VARCHAR(255)  -- Changed to VARCHAR to handle various timestamp formats, will convert later
);

-- Step 5: Create CSV file format
-- PARSE_HEADER = TRUE is required for MATCH_BY_COLUMN_NAME to work
-- Note: PARSE_HEADER automatically skips the header row, so SKIP_HEADER is not needed
-- Drop first to ensure it's recreated with correct settings
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

-- Step 6: Verify tables exist before copying
-- Use fully qualified names
SHOW TABLES LIKE 'STG_FORTUNE1000' IN SCHEMA COMPANY_ATLAS.STAGING;
SHOW TABLES LIKE 'STG_GLOBAL_COMPANIES' IN SCHEMA COMPANY_ATLAS.STAGING;

-- Verify we can see the tables
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE 
FROM COMPANY_ATLAS.INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'STAGING' 
  AND TABLE_NAME IN ('STG_FORTUNE1000', 'STG_GLOBAL_COMPANIES');

-- Step 7: Copy data from S3 to STG_FORTUNE1000 table
-- Loading from: s3://company-atlas-202511/raw/fortune1000/2025-11-23/fortune1000_2024.csv
-- Using fully qualified table name
-- Pattern matching searches in all subdirectories (including date folders like 2025-11-23/)
COPY INTO COMPANY_ATLAS.STAGING.STG_FORTUNE1000
FROM '@company_atlas_stage/raw/fortune1000/'
FILE_FORMAT = csv_format
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
PATTERN = '.*/.*fortune1000_2024\.csv'
ON_ERROR = 'CONTINUE'
FORCE = TRUE;

-- Step 8: Copy data from S3 to STG_GLOBAL_COMPANIES table
-- Loading from: s3://company-atlas-202511/raw/global_companies/2025-11-23/fortune1000_companies.csv
-- Using fully qualified table name
-- CSV file now has only one 'industry' column (duplicate removed)
-- Load data - MATCH_BY_COLUMN_NAME will match columns from CSV
COPY INTO COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES
FROM '@company_atlas_stage/raw/global_companies/'
FILE_FORMAT = csv_format
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
PATTERN = '.*/.*fortune1000_companies\.csv'
ON_ERROR = 'CONTINUE'
FORCE = TRUE;

-- Step 9: Verify data was loaded
-- Check row counts using fully qualified table names
SELECT 'STG_FORTUNE1000' AS table_name, COUNT(*) AS row_count FROM COMPANY_ATLAS.STAGING.STG_FORTUNE1000
UNION ALL
SELECT 'STG_GLOBAL_COMPANIES' AS table_name, COUNT(*) AS row_count FROM COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES;

-- Step 10: Show sample data using fully qualified table names
SELECT * FROM COMPANY_ATLAS.STAGING.STG_FORTUNE1000 LIMIT 5;
SELECT * FROM COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES LIMIT 5;

-- Step 11: Check for any errors in the copy
SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'STG_FORTUNE1000',
    START_TIME => DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
));

SELECT * FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'STG_GLOBAL_COMPANIES',
    START_TIME => DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
));

