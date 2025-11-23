# Company Atlas

A unified firmographic data pipeline that collects, cleans, and normalizes company data from multiple sources, producing an analytics-ready dataset with an elegant interactive website and REST API.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│   Kaggle    │────▶│      S3     │────▶│Snowflake │────▶│   dbt    │
│  Datasets   │     │  (Raw Data) │     │ (Staging)│     │(Modeling)│
└─────────────┘     └─────────────┘     └──────────┘     └──────────┘
                                                              │
                                                              ▼
┌─────────────┐     ┌─────────────┐     ┌──────────┐     ┌──────────┐
│  Airflow    │────▶│  Great      │     │  Neo4j   │     │  FastAPI │
│(Orchestr.)  │     │ Expectations│     │  (Graph) │     │  (REST)  │
└─────────────┘     └─────────────┘     └──────────┘     └──────────┘
                                                              │
                                                              ▼
                                                    ┌─────────────────┐
                                                    │   GitHub Pages  │
                                                    │   (Website)     │
                                                    └─────────────────┘
```

## Features

- **Multi-source Data Ingestion**: Collects data from Kaggle datasets (Techsalerator's USA and The 17M+ Company Dataset)
- **Cloud Storage**: S3 for raw data storage
- **Data Warehouse**: Snowflake for staging and analytics
- **Data Transformation**: dbt for modeling and transformation
- **Data Quality**: dbt tests and Great Expectations for validation
- **Orchestration**: Apache Airflow for workflow automation
- **Graph Database**: Neo4j for relationship visualization
- **REST API**: FastAPI-based data product for developers
- **Interactive Website**: Apple-style elegant showcase deployed on GitHub Pages

## Project Structure

```
company-atlas/
├── pipelines/              # Data pipeline scripts
│   ├── ingestion/         # Data ingestion scripts
│   ├── transformation/    # Data transformation logic
│   └── validation/        # Data quality checks
├── dbt/                   # dbt models and tests
│   ├── models/
│   ├── tests/
│   └── dbt_project.yml
├── airflow/               # Airflow DAGs
│   └── dags/
├── neo4j/                 # Neo4j models and queries
│   └── models/
├── api/                   # FastAPI REST API
│   ├── app.py
│   ├── models/
│   └── routers/
├── website/               # GitHub Pages website
│   ├── index.html
│   ├── assets/
│   └── docs/
├── config/                # Configuration files
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Data Model

The unified schema follows the requirements from the technical assignment and includes:
- `company_id`: Unique identifier (hash of name + domain)
- `company_name`: Company name (normalized, uppercase)
- `domain`: Company website domain (normalized, lowercase)
- `industry`: Industry classification
- `country`: Country location (normalized, uppercase)
- `employee_count`: Number of employees (integer)
- `revenue`: Revenue information (float)
- `founded_year`: Year company was founded (integer)
- `source_system`: Data source identifier (required field)
- `last_updated_at`: Timestamp of last update from source
- `ingested_at`: Timestamp of ingestion into pipeline
- `dbt_updated_at`: Timestamp of last dbt transformation

The final model is a clean dimension table (not a star schema) as it represents a single unified entity without fact tables.

## Setup Instructions

### Prerequisites

- Python 3.9+
- Docker & Docker Compose (for Airflow and Neo4j)
- Snowflake account
- AWS account with S3 access
- Kaggle API credentials

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd company-atlas
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Set up Kaggle API:
```bash
mkdir -p ~/.kaggle
# Place kaggle.json in ~/.kaggle/
```

5. Initialize dbt:
```bash
cd dbt
dbt deps
```

6. Start Airflow and Neo4j:
```bash
docker-compose up -d
```

### Running the Pipeline

1. Trigger Airflow DAG:
```bash
# Access Airflow UI at http://localhost:8080
# Or use CLI:
airflow dags trigger company_atlas_pipeline
```

2. Run dbt models:
```bash
cd dbt
dbt run
dbt test
```

3. Run Great Expectations validation:
```bash
python pipelines/validation/run_expectations.py
```

## Website Deployment

The website is automatically deployed to GitHub Pages. To deploy manually:

```bash
cd website
# Build and push to gh-pages branch
```

Access the website at: `https://<username>.github.io/company-atlas/`

## API Documentation

The REST API is available at `/api`. Full documentation:
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Data Sources

- **Techsalerator's USA Dataset**: Comprehensive US company data
- **The 17M+ Company Dataset**: Global company database

## Design Decisions

1. **Modular Architecture**: Separated concerns for maintainability
2. **Cloud-Native**: S3 for storage, Snowflake for analytics
3. **ELT Pattern**: Extract, Load, Transform for flexibility
4. **Graph Database**: Neo4j for relationship analysis
5. **Modern Stack**: FastAPI, dbt, Airflow for scalability

## License

See LICENSE file for details.
