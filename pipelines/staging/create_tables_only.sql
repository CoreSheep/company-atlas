-- SQL Script to Create Only the Staging Tables
-- Run this FIRST as ACCOUNTADMIN to create the tables
-- This ensures tables exist before trying to load data

-- Step 1: Use admin role
USE ROLE ACCOUNTADMIN;

-- Step 2: Set context
USE DATABASE COMPANY_ATLAS;
USE SCHEMA STAGING;

-- Step 3: Verify schema exists
SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA 
WHERE SCHEMA_NAME = 'STAGING' AND CATALOG_NAME = 'COMPANY_ATLAS';

-- Step 4: Create staging table for Fortune 1000 data
-- This matches the actual schema of the Fortune 1000 2024 dataset
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

-- Step 5: Create staging table for Global Companies data
-- This matches the actual schema of the normalized fortune1000_companies dataset
CREATE OR REPLACE TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES (
    company_name VARCHAR(255),
    domain VARCHAR(500),
    industry VARCHAR(255),
    industry_alt VARCHAR(255),  -- Second industry column
    country VARCHAR(100),
    employee_count INTEGER,
    revenue FLOAT,
    founded_year INTEGER,
    source_system VARCHAR(100),
    last_updated_at VARCHAR(255)  -- Changed to VARCHAR to handle various timestamp formats
);

-- Step 6: Verify tables were created successfully
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE 
FROM COMPANY_ATLAS.INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = 'STAGING' 
  AND TABLE_NAME IN ('STG_FORTUNE1000', 'STG_GLOBAL_COMPANIES')
ORDER BY TABLE_NAME;

-- Step 7: Show table details
DESCRIBE TABLE COMPANY_ATLAS.STAGING.STG_FORTUNE1000;
DESCRIBE TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES;

-- Step 8: Grant privileges to TRANSFORM role
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLE COMPANY_ATLAS.STAGING.STG_FORTUNE1000 TO ROLE TRANSFORM;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES TO ROLE TRANSFORM;

-- Note: If you want to convert last_updated_at to TIMESTAMP later, you can run:
-- ALTER TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES 
-- MODIFY COLUMN last_updated_at TIMESTAMP_NTZ;
-- Then update: UPDATE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES 
-- SET last_updated_at = CAST(last_updated_at AS TIMESTAMP_NTZ) WHERE last_updated_at IS NOT NULL;

-- Verify grants
SHOW GRANTS ON TABLE COMPANY_ATLAS.STAGING.STG_FORTUNE1000;
SHOW GRANTS ON TABLE COMPANY_ATLAS.STAGING.STG_GLOBAL_COMPANIES;

