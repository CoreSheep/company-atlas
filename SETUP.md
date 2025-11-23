# Setup Guide

## Prerequisites

Before setting up Company Atlas, ensure you have:

- Python 3.9 or higher
- Docker and Docker Compose
- Git
- AWS Account with S3 access
- Snowflake Account
- Kaggle Account with API credentials
- GitHub Account (for website deployment)

## Step 1: Clone Repository

```bash
git clone <repository-url>
cd company-atlas
```

## Step 2: Python Environment Setup

### Option A: Using Conda (Recommended)

Create a conda environment from the environment.yml file:

```bash
conda env create -f environment.yml
```

Activate the environment:

```bash
conda activate company-atlas
```

The environment.yml file includes all dependencies and will create an environment with Python 3.11 and all required packages.

### Option B: Using Python venv

Alternatively, you can create a virtual environment using venv:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

**Note**: If using conda, the environment is already set up with all dependencies from environment.yml. No need to run `pip install -r requirements.txt`.

## Step 3: Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=company-atlas-raw-data

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=COMPANY_ATLAS
SNOWFLAKE_SCHEMA=RAW

# Kaggle API
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_key

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
```

## Step 4: Set Up Kaggle API

**Important**: Make sure your conda environment is activated before proceeding:

```bash
conda activate company-atlas
```

The Kaggle package is already installed in the conda environment. Configure Kaggle credentials:

```bash
mkdir -p ~/.kaggle
# Place your kaggle.json in ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

Get your Kaggle API credentials from: https://www.kaggle.com/settings

Download your `kaggle.json` API token from the Kaggle account settings and place it in `~/.kaggle/kaggle.json`.

## Step 5: Set Up AWS S3

### Step 5a: Create AWS Access Keys

1. **Log in to AWS Console**
   - Go to https://console.aws.amazon.com/
   - Sign in with your AWS account

2. **Navigate to IAM (Identity and Access Management)**
   - In the AWS Console, search for "IAM" in the search bar
   - Click on "IAM" service

3. **Create Access Keys**
   - Click on your username in the top-right corner
   - Select "Security credentials" from the dropdown menu
   - Scroll down to "Access keys" section
   - Click "Create access key"

4. **Choose Use Case**
   - Select "Command Line Interface (CLI)" or "Application running outside AWS"
   - Check the confirmation box
   - Click "Next"

5. **Add Description (Optional)**
   - Add a description like "Company Atlas S3 Access"
   - Click "Create access key"

6. **Save Your Keys**
   - **IMPORTANT**: Download or copy both:
     - `AWS_ACCESS_KEY_ID` (starts with "AKIA...")
     - `AWS_SECRET_ACCESS_KEY` (long alphanumeric string)
   - ⚠️ **Warning**: The secret key is shown only once. Save it immediately!
   - Click "Done"

7. **Configure in Your Environment**
   - Add the keys to your `.env` file:
     ```bash
     AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
     AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
     AWS_REGION=us-east-1
     ```
   - Or use AWS CLI to configure:
     ```bash
     aws configure
     ```
     This will prompt you for:
     - AWS Access Key ID
     - AWS Secret Access Key
     - Default region name (e.g., `us-east-1`)
     - Default output format (e.g., `json`)

### Step 5b: Create S3 Bucket

**Option 1: Using AWS CLI** (if configured):
```bash
aws s3 mb s3://company-atlas-raw-data --region us-east-1
```

**Option 2: Using AWS Console**:
1. Go to S3 service in AWS Console
2. Click "Create bucket"
3. Enter bucket name (e.g., `company-atlas-202511` using year-month format)
4. Select region (e.g., `us-east-1`)
5. Configure settings as needed
6. Click "Create bucket"

**Note**: S3 bucket names must be globally unique across all AWS accounts. The upload script will automatically create a bucket with year-month format (e.g., `company-atlas-202511`) if it doesn't exist.

## Step 6: Set Up Snowflake

1. Log into your Snowflake account
2. Create a warehouse (or use existing):
   ```sql
   CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
   WITH WAREHOUSE_SIZE = 'X-SMALL';
   ```
3. The database and schema will be created automatically by the pipeline

## Step 7: Initialize dbt

Navigate to dbt directory:

```bash
cd dbt
dbt deps  # Install dbt packages
```

Verify dbt configuration:

```bash
dbt debug
```

## Step 8: Set Up Airflow and Neo4j

Start Docker services:

```bash
docker-compose up -d
```

Wait for services to initialize (check logs):

```bash
docker-compose logs -f
```

Access Airflow UI:
- URL: http://localhost:8080
- Username: `airflow`
- Password: `airflow` (change in production)

Access Neo4j Browser:
- URL: http://localhost:7474
- Username: `neo4j`
- Password: `password` (change in production)

## Step 9: Initialize Great Expectations

Create Great Expectations context:

```bash
python pipelines/validation/great_expectations_setup.py
```

## Step 10: Run Initial Pipeline

**Important**: Make sure your conda environment is activated:

```bash
conda activate company-atlas
```

Trigger the Airflow DAG manually:

1. Open Airflow UI at http://localhost:8080
2. Find `company_atlas_pipeline` DAG
3. Toggle it ON
4. Click "Trigger DAG"

Or run components manually:

```bash
# Test ingestion
python -m pipelines.ingestion.kaggle_ingestion

# Test S3 upload
python -m pipelines.storage.s3_storage

# Test Snowflake
python -m pipelines.storage.snowflake_staging

# Run dbt models
cd dbt
dbt run
dbt test
```

## Step 11: Start REST API

**Important**: Make sure your conda environment is activated:

```bash
conda activate company-atlas
```

Start the FastAPI server:

```bash
python api/main.py
```

Or use the script:

```bash
./api/run_api.sh
```

Access API documentation:
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Step 12: Deploy Website

### Local Development

Serve website locally:

```bash
cd website
python -m http.server 8001
```

Access at: http://localhost:8001

### GitHub Pages Deployment

1. Push code to GitHub repository
2. Enable GitHub Pages in repository settings
3. Select source branch (typically `main` or `gh-pages`)
4. The website will be available at: `https://<username>.github.io/company-atlas/`

Or use GitHub Actions workflow (already configured):

The workflow in `.github/workflows/pages.yml` will automatically deploy on push to main branch.

## Verification

### Check Pipeline Execution

1. Airflow UI: Verify DAG runs successfully
2. Snowflake: Query unified_companies table
3. S3: Check for uploaded Parquet files

### Check API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/statistics
```

### Check Website

- Verify all sections load correctly
- Check interactive charts
- Test API links

## Troubleshooting

### Common Issues

1. **Kaggle API errors**: Verify credentials in `~/.kaggle/kaggle.json`
2. **S3 upload failures**: Check AWS credentials and bucket permissions
3. **Snowflake connection errors**: Verify account, user, and password
4. **dbt errors**: Check profiles.yml and database connection
5. **Airflow task failures**: Check logs in Airflow UI
6. **Neo4j connection**: Verify Docker container is running

### Getting Help

- Check logs: `docker-compose logs <service-name>`
- Airflow logs: Access via Airflow UI
- dbt logs: Check `dbt/logs/` directory
- API logs: Check console output

## Next Steps

1. Customize data sources and mappings
2. Add additional validation rules
3. Configure monitoring and alerts
4. Set up production deployment
5. Add authentication to API
6. Implement caching strategies

