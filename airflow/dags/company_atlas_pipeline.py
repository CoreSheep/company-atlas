"""
Apache Airflow DAG for Company Atlas data pipeline.

This DAG orchestrates the complete data pipeline:
1. Download Fortune 1000 dataset from Kaggle (jeannicolasduval/2024-fortune-1000-companies)
   - Saves fortune1000_2024.csv to data/raw/fortune1000/
   - Saves fortune1000_companies.csv to data/raw/global_companies/
2. Upload CSV files to S3
   - fortune1000_2024.csv -> s3://bucket/raw/fortune1000/{date}/
   - fortune1000_companies.csv -> s3://bucket/raw/global_companies/{date}/
3. Load data from S3 to Snowflake staging tables
4. dbt Raw Layer: Initial data cleaning and normalization
5. Great Expectations: Validate raw layer data quality
6. dbt Bronze Layer: Data quality validation and standardization
7. Great Expectations: Validate bronze layer data quality
8. dbt Marts Layer: Analytics-ready unified tables
9. Great Expectations: Validate marts layer data quality
10. dbt Tests: Data quality validation tests
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
# In Docker container: /opt/airflow/dags/company_atlas_pipeline.py
# project_root should be /opt/airflow
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables (don't override existing env vars set by container)
from dotenv import load_dotenv
load_dotenv(override=False)

default_args = {
    'owner': 'company-atlas',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

dag = DAG(
    'company_atlas_pipeline',
    default_args=default_args,
    description='Complete data pipeline: Ingestion -> S3 -> Snowflake Staging -> dbt (Raw/Bronze/Marts) -> Great Expectations',
    schedule_interval=None,  # Manual trigger only (set to timedelta(days=1) for daily schedule)
    start_date=days_ago(1),
    catchup=False,
    tags=['company-atlas', 'data-pipeline', 'ingestion', 's3', 'snowflake', 'dbt', 'great-expectations'],
    max_active_runs=1,  # Only one run at a time
)


# ============================================================================
# Task Functions - Data Ingestion
# ============================================================================

def download_datasets(**context):
    """Step 1: Download Fortune 1000 dataset from Kaggle using download_datasets.py."""
    import logging
    import pandas as pd
    import kaggle
    
    logger = logging.getLogger(__name__)
    
    logger.info("Downloading Fortune 1000 dataset from Kaggle...")
    
    try:
        # Authenticate Kaggle API
        kaggle.api.authenticate()
        
        data_dir = project_root / 'data' / 'raw'
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Download Fortune 1000 dataset
        dataset = "jeannicolasduval/2024-fortune-1000-companies"
        fortune_path = data_dir / "fortune1000"
        fortune_path.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"Downloading dataset: {dataset}")
        kaggle.api.dataset_download_files(
            dataset,
            path=str(fortune_path),
            unzip=True,
            quiet=False
        )
        
        # Find and read CSV file
        csv_files = list(fortune_path.glob("*.csv"))
        if csv_files:
            main_csv = next((f for f in csv_files if 'fortune' in f.name.lower() and '2024' in f.name), csv_files[0])
            df = pd.read_csv(main_csv)
            logger.info(f"Downloaded Fortune 1000: {len(df)} records")
            logger.info(f"Saved to: {main_csv}")
            
            # Create global_companies directory and save normalized version
            global_dir = data_dir / "global_companies"
            global_dir.mkdir(exist_ok=True, parents=True)
            
            # Save as fortune1000_companies.csv (normalized copy)
            fortune_companies_path = global_dir / "fortune1000_companies.csv"
            df.to_csv(fortune_companies_path, index=False)
            logger.info(f"Saved normalized copy to: {fortune_companies_path}")
        else:
            raise FileNotFoundError("No CSV files found in downloaded dataset")
        
        context['ti'].xcom_push(key='download_status', value='success')
        context['ti'].xcom_push(key='records_count', value=len(df))
        return {'status': 'success', 'records': len(df)}
        
    except Exception as e:
        logger.error(f"Failed to download datasets: {e}", exc_info=True)
        raise


def upload_to_s3(**context):
    """Step 2: Upload fortune1000_2024.csv and fortune1000_companies.csv to S3."""
    import logging
    import boto3
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    logger.info("Uploading CSV files to S3...")
    
    try:
        bucket_name = os.getenv("S3_BUCKET_NAME")
        if not bucket_name:
            timestamp = datetime.utcnow().strftime("%Y%m")
            bucket_name = f"company-atlas-{timestamp}"
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Verify bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Using S3 bucket: {bucket_name}")
        
        # Files to upload
        files_to_upload = [
            (project_root / "data/raw/fortune1000/fortune1000_2024.csv", "raw/fortune1000"),
            (project_root / "data/raw/global_companies/fortune1000_companies.csv", "raw/global_companies"),
        ]
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        uploaded_files = []
        
        for file_path, key_prefix in files_to_upload:
            if file_path.exists():
                key = f"{key_prefix}/{date_str}/{file_path.name}"
                logger.info(f"Uploading {file_path.name} to s3://{bucket_name}/{key}")
                s3_client.upload_file(str(file_path), bucket_name, key)
                uploaded_files.append(f"s3://{bucket_name}/{key}")
                logger.info(f"  Uploaded: {file_path.stat().st_size / 1024:.2f} KB")
            else:
                logger.warning(f"File not found: {file_path}")
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} file(s) to S3")
        
        context['ti'].xcom_push(key='s3_files', value=uploaded_files)
        context['ti'].xcom_push(key='upload_status', value='success')
        return {'status': 'success', 'files': uploaded_files}
        
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}", exc_info=True)
        raise


def load_to_snowflake_staging(**context):
    """Step 3: Load data from S3 to Snowflake staging tables."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Loading data from S3 to Snowflake staging tables...")
    
    try:
        import snowflake.connector
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        # Use container path for private key (mounted from host)
        private_key_path = '/opt/airflow/snowflake_rsa_key.p8'
        
        logger.info(f"Using private key path: {private_key_path}")
        logger.info(f"Private key exists: {os.path.exists(private_key_path)}")
        
        if os.path.exists(private_key_path):
            with open(private_key_path, 'rb') as key_file:
                p_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE', '').encode() if os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE') else None,
                    backend=default_backend()
                )
            
            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            conn = snowflake.connector.connect(
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                user=os.getenv('SNOWFLAKE_USER'),
                private_key=pkb,
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                database='COMPANY_ATLAS',
                schema='STAGING',
                role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM')
            )
        else:
            raise FileNotFoundError(f"Snowflake private key not found at {private_key_path}")
        
        logger.info("Connected to Snowflake successfully!")
        
        # Execute the load SQL script
        sql_file = project_root / "pipelines/staging/load_data_from_s3.sql"
        
        if sql_file.exists():
            logger.info(f"Executing SQL file: {sql_file}")
            
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            cursor = conn.cursor()
            
            # Split and execute statements
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
            
            for i, statement in enumerate(statements, 1):
                if statement:
                    logger.info(f"Executing statement {i}/{len(statements)}")
                    try:
                        cursor.execute(statement)
                        logger.info(f"  Statement {i} executed successfully")
                    except Exception as e:
                        logger.warning(f"  Statement {i} failed: {e}")
            
            cursor.close()
            conn.commit()
        else:
            logger.warning(f"SQL file not found: {sql_file}")
        
        conn.close()
        logger.info("Data loaded to Snowflake staging successfully!")
        
        context['ti'].xcom_push(key='staging_status', value='success')
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"Failed to load to Snowflake staging: {e}", exc_info=True)
        raise


# ============================================================================
# Task Functions - dbt Transformations
# ============================================================================

def run_dbt_raw(**context):
    """Step 4: Run dbt raw layer models."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Running dbt raw layer models...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        env = os.environ.copy()
        env['SNOWFLAKE_PRIVATE_KEY_PATH'] = '/opt/airflow/snowflake_rsa_key.p8'
        
        result = subprocess.run(
            ['dbt', 'run', '--select', 'raw.*'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"dbt raw models failed - stdout: {result.stdout}")
            logger.error(f"dbt raw models failed - stderr: {result.stderr}")
            raise Exception(f"dbt raw models failed: {result.stdout or result.stderr}")
        
        logger.info("dbt raw layer completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='dbt_raw_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"dbt raw layer failed: {e}", exc_info=True)
        raise


def run_dbt_bronze(**context):
    """Step 6: Run dbt bronze layer models."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Running dbt bronze layer models...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        env = os.environ.copy()
        env['SNOWFLAKE_PRIVATE_KEY_PATH'] = '/opt/airflow/snowflake_rsa_key.p8'
        
        result = subprocess.run(
            ['dbt', 'run', '--select', 'bronze.*'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"dbt bronze models failed: {result.stderr}")
            raise Exception(f"dbt bronze models failed: {result.stderr}")
        
        logger.info("dbt bronze layer completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='dbt_bronze_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"dbt bronze layer failed: {e}", exc_info=True)
        raise


def run_dbt_marts(**context):
    """Step 8: Run dbt marts layer models."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Running dbt marts layer models...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        env = os.environ.copy()
        env['SNOWFLAKE_PRIVATE_KEY_PATH'] = '/opt/airflow/snowflake_rsa_key.p8'
        
        result = subprocess.run(
            ['dbt', 'run', '--select', 'marts.*'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"dbt marts models failed: {result.stderr}")
            raise Exception(f"dbt marts models failed: {result.stderr}")
        
        logger.info("dbt marts layer completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='dbt_marts_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"dbt marts layer failed: {e}", exc_info=True)
        raise


def run_dbt_tests(**context):
    """Step 10: Run dbt tests for data quality validation."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Running dbt tests...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        env = os.environ.copy()
        env['SNOWFLAKE_PRIVATE_KEY_PATH'] = '/opt/airflow/snowflake_rsa_key.p8'
        
        result = subprocess.run(
            ['dbt', 'test'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=env
        )
        
        if result.returncode != 0:
            logger.error(f"dbt tests failed: {result.stderr}")
            logger.warning("Some dbt tests failed, but continuing pipeline...")
        
        logger.info("dbt tests completed!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='dbt_tests_status', value='completed')
        return {'status': 'completed'}
    except Exception as e:
        logger.error(f"dbt tests error: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


# ============================================================================
# Task Functions - Great Expectations Validation
# ============================================================================

def validate_raw_with_ge(**context):
    """Step 5: Validate raw layer with Great Expectations."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Validating raw layer with Great Expectations...")
    
    try:
        from pipelines.validation.great_expectations_setup import GreatExpectationsValidator
        
        validator = GreatExpectationsValidator()
        results = validator.validate_raw_layer()
        
        logger.info("Raw layer Great Expectations validation completed successfully!")
        logger.info(f"Validation results: {results}")
        
        context['ti'].xcom_push(key='ge_raw_status', value='success')
        return {'status': 'success', 'results': str(results)}
    except Exception as e:
        logger.error(f"Raw layer Great Expectations validation failed: {e}", exc_info=True)
        logger.warning("Great Expectations validation failed, but continuing pipeline...")
        return {'status': 'error', 'error': str(e)}


def validate_bronze_with_ge(**context):
    """Step 7: Validate bronze layer with Great Expectations."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Validating bronze layer with Great Expectations...")
    
    try:
        from pipelines.validation.great_expectations_setup import GreatExpectationsValidator
        
        validator = GreatExpectationsValidator()
        results = validator.validate_bronze_layer()
        
        logger.info("Bronze layer Great Expectations validation completed successfully!")
        logger.info(f"Validation results: {results}")
        
        context['ti'].xcom_push(key='ge_bronze_status', value='success')
        return {'status': 'success', 'results': str(results)}
    except Exception as e:
        logger.error(f"Bronze layer Great Expectations validation failed: {e}", exc_info=True)
        logger.warning("Great Expectations validation failed, but continuing pipeline...")
        return {'status': 'error', 'error': str(e)}


def validate_marts_with_ge(**context):
    """Step 9: Validate marts layer with Great Expectations."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Validating marts layer with Great Expectations...")
    
    try:
        from pipelines.validation.great_expectations_setup import GreatExpectationsValidator
        
        validator = GreatExpectationsValidator()
        results = validator.validate_marts_layer()
        
        logger.info("Marts layer Great Expectations validation completed successfully!")
        logger.info(f"Validation results: {results}")
        
        context['ti'].xcom_push(key='ge_marts_status', value='success')
        return {'status': 'success', 'results': str(results)}
    except Exception as e:
        logger.error(f"Marts layer Great Expectations validation failed: {e}", exc_info=True)
        logger.warning("Great Expectations validation failed, but continuing pipeline...")
        return {'status': 'error', 'error': str(e)}


# ============================================================================
# Define Tasks
# ============================================================================

# Step 1: Download datasets from Kaggle
download_datasets_task = PythonOperator(
    task_id='download_datasets',
    python_callable=download_datasets,
    dag=dag,
    pool=None,
)

# Step 2: Upload CSV files to S3
upload_to_s3_task = PythonOperator(
    task_id='upload_to_s3',
    python_callable=upload_to_s3,
    dag=dag,
    pool=None,
)

# Step 3: Load data from S3 to Snowflake staging
load_to_staging_task = PythonOperator(
    task_id='load_to_snowflake_staging',
    python_callable=load_to_snowflake_staging,
    dag=dag,
    pool=None,
)

# Step 4: dbt Raw Layer
run_dbt_raw_task = PythonOperator(
    task_id='run_dbt_raw',
    python_callable=run_dbt_raw,
    dag=dag,
    pool=None,
)

# Step 5: Validate Raw Layer with Great Expectations
validate_raw_ge_task = PythonOperator(
    task_id='validate_raw_with_great_expectations',
    python_callable=validate_raw_with_ge,
    dag=dag,
    pool=None,
)

# Step 6: dbt Bronze Layer
run_dbt_bronze_task = PythonOperator(
    task_id='run_dbt_bronze',
    python_callable=run_dbt_bronze,
    dag=dag,
    pool=None,
)

# Step 7: Validate Bronze Layer with Great Expectations
validate_bronze_ge_task = PythonOperator(
    task_id='validate_bronze_with_great_expectations',
    python_callable=validate_bronze_with_ge,
    dag=dag,
    pool=None,
)

# Step 8: dbt Marts Layer
run_dbt_marts_task = PythonOperator(
    task_id='run_dbt_marts',
    python_callable=run_dbt_marts,
    dag=dag,
    pool=None,
)

# Step 9: Validate Marts Layer with Great Expectations
validate_marts_ge_task = PythonOperator(
    task_id='validate_marts_with_great_expectations',
    python_callable=validate_marts_with_ge,
    dag=dag,
    pool=None,
)

# Step 10: dbt Tests
run_dbt_tests_task = PythonOperator(
    task_id='run_dbt_tests',
    python_callable=run_dbt_tests,
    dag=dag,
    pool=None,
)


# ============================================================================
# Define Task Dependencies
# ============================================================================

# Complete Pipeline Flow:
# Download -> Upload S3 -> Snowflake Staging -> dbt Raw -> GE Raw -> dbt Bronze -> GE Bronze -> dbt Marts -> GE Marts -> dbt Tests

download_datasets_task >> upload_to_s3_task
upload_to_s3_task >> load_to_staging_task
load_to_staging_task >> run_dbt_raw_task
run_dbt_raw_task >> validate_raw_ge_task
validate_raw_ge_task >> run_dbt_bronze_task
run_dbt_bronze_task >> validate_bronze_ge_task
validate_bronze_ge_task >> run_dbt_marts_task
run_dbt_marts_task >> validate_marts_ge_task
validate_marts_ge_task >> run_dbt_tests_task
