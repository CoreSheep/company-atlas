# Company Atlas Architecture

## Overview

Company Atlas is a unified firmographic data pipeline that collects, cleans, and normalizes company data from multiple sources. The architecture follows a modern ELT (Extract, Load, Transform) pattern with cloud-native components.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│  Kaggle Datasets:                                               │
│  • Techsalerator's USA Company Dataset                          │
│  • The 17M+ Company Dataset                                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  Python Scripts:                                                │
│  • Kaggle API Integration                                       │
│  • Schema Normalization                                         │
│  • Data Validation (Initial)                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│  AWS S3 (Raw Data Storage)                                      │
│  • Parquet format for efficiency                                │
│  • Partitioned by source and date                               │
│  • s3://bucket/raw/{source}/{date}/data.parquet                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STAGING LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│  Snowflake Data Warehouse                                       │
│  • Database: COMPANY_ATLAS                                      │
│  • Schema: RAW (staging tables)                                 │
│  • Tables:                                                      │
│    - STG_TECHSALERATOR_USA                                      │
│    - STG_COMPANIES_17M                                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TRANSFORMATION LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  dbt (Data Build Tool)                                          │
│  • Models:                                                      │
│    - Staging: stg_techsalerator_usa, stg_companies_17m         │
│    - Intermediate: int_unified_companies                        │
│    - Marts: unified_companies                                   │
│  • Tests: Data quality checks                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  VALIDATION LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  • dbt Tests: Schema and data quality                           │
│  • Great Expectations: Comprehensive validation                 │
│  • Data quality metrics and reporting                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION                                │
├─────────────────────────────────────────────────────────────────┤
│  Apache Airflow                                                 │
│  • DAG: company_atlas_pipeline                                  │
│  • Tasks:                                                       │
│    1. Ingest Kaggle data                                        │
│    2. Upload to S3                                              │
│    3. Load to Snowflake                                         │
│    4. Run dbt models                                            │
│    5. Run dbt tests                                             │
│    6. Run Great Expectations                                    │
│    7. Sync to Neo4j                                             │
│  • Schedule: Daily                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│   DATA PRODUCT   │   │   GRAPH DB       │
├──────────────────┤   ├──────────────────┤
│  FastAPI REST    │   │  Neo4j           │
│  API             │   │  • Company nodes │
│  • /companies    │   │  • Industry      │
│  • /statistics   │   │    relationships │
│  • /industries   │   │  • Country       │
│  • /countries    │   │    relationships │
│                  │   │  • Similarity    │
│  Snowflake       │   │    networks      │
│  MARTS schema    │   └──────────────────┘
│  unified_companies│
└──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  GitHub Pages Website                                           │
│  • Apple-style elegant design                                   │
│  • Interactive statistics                                       │
│  • Dataset distributions                                        │
│  • API documentation                                            │
│  • Example usage                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Ingestion (`pipelines/ingestion/`)

- **Kaggle Integration**: Downloads datasets using Kaggle API
- **Schema Normalization**: Maps source schemas to unified format
- **Initial Validation**: Basic data quality checks

Key Files:
- `kaggle_ingestion.py`: Main ingestion class

### 2. Storage Layer (`pipelines/storage/`)

- **S3 Storage**: Raw data in Parquet format
- **Snowflake Staging**: Loading raw data into warehouse

Key Files:
- `s3_storage.py`: S3 operations
- `snowflake_staging.py`: Snowflake connection and loading

### 3. Transformation (`dbt/`)

- **Staging Models**: Clean and normalize raw data
- **Intermediate Models**: Combine and deduplicate
- **Marts**: Final unified schema

Key Files:
- `models/staging/`: Raw data staging
- `models/intermediate/`: Data combination
- `models/marts/`: Final unified table

### 4. Validation (`pipelines/validation/`)

- **dbt Tests**: Schema and data quality tests
- **Great Expectations**: Comprehensive validation suite

Key Files:
- `dbt/models/*/schema.yml`: Test definitions
- `great_expectations_setup.py`: GE validation

### 5. Orchestration (`airflow/`)

- **Airflow DAG**: Complete pipeline workflow
- **Task Dependencies**: Sequential and parallel execution
- **Error Handling**: Retry logic and alerts

Key Files:
- `dags/company_atlas_pipeline.py`: Main DAG definition

### 6. Graph Database (`pipelines/graph/`)

- **Neo4j Integration**: Relationship modeling
- **Company Networks**: Industry and country relationships
- **Similarity Analysis**: Company connections

Key Files:
- `neo4j_sync.py`: Graph database operations

### 7. REST API (`api/`)

- **FastAPI**: Modern Python web framework
- **OpenAPI**: Auto-generated documentation
- **Filtering**: Advanced query capabilities

Key Files:
- `main.py`: API endpoints and logic

### 8. Website (`website/`)

- **Static Site**: HTML, CSS, JavaScript
- **Interactive Charts**: Chart.js visualizations
- **API Integration**: Live data display

Key Files:
- `index.html`: Main page
- `assets/css/style.css`: Apple-style design
- `assets/js/main.js`: Interactive features

## Data Flow

1. **Extract**: Kaggle datasets downloaded via API
2. **Normalize**: Source schemas mapped to unified format
3. **Load Raw**: Data uploaded to S3 in Parquet format
4. **Stage**: Data loaded into Snowflake RAW schema
5. **Transform**: dbt models clean, combine, and deduplicate
6. **Validate**: dbt tests and Great Expectations ensure quality
7. **Publish**: Final unified table in MARTS schema
8. **Expose**: REST API and Neo4j provide access
9. **Visualize**: Website displays statistics and examples

## Technology Stack

- **Orchestration**: Apache Airflow 2.8+
- **Storage**: AWS S3, Snowflake
- **Transformation**: dbt (Data Build Tool)
- **Validation**: dbt tests, Great Expectations
- **Graph Database**: Neo4j
- **API**: FastAPI
- **Website**: HTML/CSS/JavaScript, GitHub Pages
- **Language**: Python 3.9+

## Scalability Considerations

- **Parallel Processing**: Airflow supports parallel task execution
- **Incremental Loading**: dbt supports incremental models
- **Partitioning**: S3 and Snowflake use date-based partitioning
- **Caching**: API responses can be cached for performance
- **CDN**: GitHub Pages provides global CDN for website

## Security

- **Environment Variables**: Sensitive credentials stored in .env
- **Access Control**: Snowflake role-based access
- **API Security**: CORS configuration, rate limiting (production)
- **Data Privacy**: No PII in public datasets

## Monitoring & Observability

- **Airflow UI**: Pipeline execution monitoring
- **dbt Logs**: Transformation logging
- **Great Expectations**: Data quality reports
- **API Logging**: Request/response logging
- **Error Alerts**: Airflow failure notifications

## Future Enhancements

- Real-time streaming data ingestion
- Machine learning models for data enrichment
- Advanced graph analytics
- Data quality dashboards
- API rate limiting and authentication
- Multi-region deployment

