# Company Atlas

A unified firmographic data platform with thousands of companies from open-source datasets.

🌐 **Live Website**: [https://coresheep.github.io/company-atlas/](https://coresheep.github.io/company-atlas/)

![Company Atlas Main Page](images/company-atlas-main.png)

## Overview

Company Atlas collects, cleans, and normalizes firmographic data from multiple sources, producing an analytics-ready dataset with thousands of companies worldwide. The platform features an elegant interactive website, live dashboards, and a comprehensive REST API for data access.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│   Kaggle    │     │      S3     │     │Snowflake │     │   dbt    │
│  Datasets   │────▶│  (Raw Data) │────▶│ (Staging)│────▶│(Modeling)│
│             │     │             │     │          │     │          │
│ Web Crawler │     │    CSV      │     │  Tables  │     │  Models  │
└─────────────┘     └─────────────┘     └──────────┘     └──────────┘
                                                              │
                                                              ▼
┌─────────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  Airflow    │────▶│  dbt Tests  │     │  FastAPI │     │  Website │
│(Orchestr.)  │     │  (Quality)  │     │  (REST)  │     │  (Pages) │
└─────────────┘     └─────────────┘     └──────────┘     └──────────┘
```

## Features

### 📊 Statistics Dashboard

![Statistics Dashboard](images/feature_statistics.png)

- **Total Companies**: Count of all companies in the dataset
- **Total Revenue**: Aggregate revenue across all companies
- **Industries**: Number of unique industries
- **Average Employees**: Mean employee count

### 🏢 Company Profiles

![Company Profiles](images/feature_companies.png)

- **Top Companies by Market Cap**: Display of leading companies with logos
- **Company Details**: Market cap, Fortune rank, industry, revenue, employees, founded year
- **Interactive Cards**: Elegant company profile cards with visual hierarchy

### 📈 Live Dashboards

Interactive carousel with multiple visualizations:
- **Top Industries**: Bar chart showing industry distribution
- **Revenue Distribution**: Histogram of company revenues
- **City Distribution**: Geographic distribution of company headquarters
- **Employee Count Distribution**: Workforce size analysis
- **Revenue % Change**: Year-over-year revenue growth/decline
- **Revenue Growth & Decline**: Combined visualization of top performers

### 🔍 Interactive Search

![Company Search](images/feature_company_search.png)

- Search by company name or CEO name
- Real-time filtering and results display
- Sortable table with key company metrics
- Displays: company name, ticker, CEO, founded year, domain, industry, headquarters, market cap, revenue

### 🌐 REST API

![REST API](images/feature_api.png)

FastAPI-based RESTful API with comprehensive endpoints:
- `GET /api/v1/companies` - Search and retrieve companies with filtering
- `GET /api/v1/companies/{id}` - Get specific company by ID
- `GET /api/v1/statistics` - Dataset statistics and distributions
- `GET /api/v1/industries` - List of all industries
- `GET /api/v1/countries` - List of all countries

**Interactive Documentation**: Available at `/docs` endpoint with Swagger UI

## Data Pipelines

### 1. Data Collection

**Multi-Source Ingestion:**
- **Kaggle Datasets**: Downloads Fortune 1000 2024 dataset from Kaggle
- **Web Crawler**: Enriches company data by scraping additional information (founded year, company details) from web sources
- Data is collected asynchronously using `trio` for efficient concurrent processing

### 2. Data Ingestion

**S3 Storage:**
- Raw data files (CSV format) are uploaded to AWS S3 buckets
- Files are organized by source: `fortune1000/` and `global_companies/`

**Snowflake Staging:**
- Data is loaded from S3 to Snowflake staging tables using external stages
- `COPY INTO` commands with proper file format configurations (CSV with header parsing)
- Staging tables: `STG_FORTUNE1000`, `STG_GLOBAL_COMPANIES`

### 3. Data Modeling with dbt

**Transformation Layers:**
- **Raw Layer**: Initial data cleaning and normalization
  - `raw_dim_companies`: Unified company dimension table
  - `raw_fct_company_metrics`: Company metrics and financial data
- **Bronze Layer**: Data quality validation and standardization
  - `bronze_dim_companies`: Cleaned company master data
  - `bronze_fct_company_metrics`: Validated metrics data
- **Marts Layer**: Analytics-ready unified tables
  - `unified_companies`: Final star schema with joined dimension and fact tables

**Data Quality:**
- Automatic tests using dbt:
  - Uniqueness tests on `company_name`
  - Not null constraints on key fields
  - Range validation (e.g., Fortune rank 1-1000)
  - Relationship integrity checks

### 4. Orchestration

**Apache Airflow:**
- Automated workflow scheduling for the entire pipeline
- DAGs coordinate:
  - Data collection from Kaggle and web crawler
  - S3 uploads
  - Snowflake data loading
  - dbt model execution
  - Data quality testing

### 5. Data Transformation

**dbt Models:**
- Incremental materialization for efficient updates
- Column normalization and type casting
- Deduplication across multiple sources
- Schema unification (star schema design)
- Automatic timestamp tracking (`loaded_at`, `last_updated_at`)

### 6. Data Visualization

**Interactive Website:**
- Live dashboards with Chart.js visualizations
- Real-time statistics and company profiles
- Interactive search functionality
- Responsive design for mobile and desktop

## API Documentation

Full API documentation is available on the website:

- **Website Documentation**: [https://coresheep.github.io/company-atlas/docs/api.html](https://coresheep.github.io/company-atlas/docs/api.html)
- **Interactive API Docs**: `http://localhost:8000/docs` (when running locally)
- **ReDoc**: `http://localhost:8000/redoc` (when running locally)

### Example Usage

**Python:**
```python
import requests

# Search for Apple by company name
response = requests.get(
    "http://localhost:8000/api/v1/companies",
    params={
        "company_name": "Apple",
        "page": 1,
        "page_size": 10
    }
)

companies = response.json()
print(f"Found {companies['total']} companies")
for company in companies['companies']:
    print(f"- {company['company_name']} ({company['domain']})")
    print(f"  Industry: {company['industry']}")
    print(f"  Revenue: ${company['revenue']:,.0f}")
    print(f"  Employees: {company['employee_count']:,}")
```

**cURL:**
```bash
# Get statistics
curl "http://localhost:8000/api/v1/statistics"

# Search for Apple
curl "http://localhost:8000/api/v1/companies?company_name=Apple"

# Get specific company by ID
curl "http://localhost:8000/api/v1/companies/{company_id}"
```

## Technology Stack

- **Data Collection**: Kaggle API, Web Scraping (httpx, BeautifulSoup, trio)
- **Cloud Storage**: AWS S3
- **Data Warehouse**: Snowflake
- **Data Transformation**: dbt (Data Build Tool)
- **Orchestration**: Apache Airflow
- **API**: FastAPI, Uvicorn
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **Deployment**: GitHub Pages

## Project Structure

```
company-atlas/
├── pipelines/              # Data pipeline scripts
│   ├── ingestion/         # Data ingestion (Kaggle, web crawler)
│   ├── staging/           # S3 to Snowflake loading
│   └── website/           # Logo fetching and website utilities
├── dbt/                   # dbt models and tests
│   ├── models/
│   │   ├── raw/           # Raw layer models
│   │   ├── bronze/        # Bronze layer models
│   │   └── marts/         # Analytics-ready marts
│   └── schema.yml         # Schema definitions and tests
├── api/                   # FastAPI REST API
│   ├── main.py
│   └── models/
├── website/               # GitHub Pages website
│   ├── index.html
│   ├── assets/
│   │   ├── css/
│   │   ├── js/
│   │   └── logos/
│   └── docs/
│       └── api.html
├── data/                  # Local data storage
│   ├── raw/              # Raw data files
│   └── marts/            # Processed data
├── images/                # Documentation images
└── requirements.txt       # Python dependencies
```

## Setup

### Prerequisites

- Python 3.9+
- Snowflake account
- AWS account with S3 access
- Kaggle API credentials

### Installation

1. Clone the repository:
```bash
git clone https://github.com/CoreSheep/company-atlas.git
cd company-atlas
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials (Snowflake, AWS, Kaggle)
```

4. Configure dbt:
```bash
cd dbt
dbt deps
```

5. Run data pipeline:
```bash
# Download datasets
python pipelines/ingestion/main_ingestion.py

# Upload to S3
python pipelines/staging/upload_to_s3.py

# Load to Snowflake
# Run SQL scripts in pipelines/staging/

# Run dbt models
cd dbt
dbt run
dbt test
```

## Citation

If you use Company Atlas in your research or project, please cite:

```
Li, J. (2025). Company Atlas: A Unified Firmographic Data Platform. 
https://coresheep.github.io/company-atlas/
```

**Author**: Jiufeng Li ([https://jiufengblog.web.app/](https://jiufengblog.web.app/))  
**Project Website**: [https://coresheep.github.io/company-atlas/](https://coresheep.github.io/company-atlas/)  
**Year**: 2025

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Jiufeng Li ([https://jiufengblog.web.app/](https://jiufengblog.web.app/))
