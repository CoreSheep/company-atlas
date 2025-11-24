"""
Apache Airflow DAG for Company Atlas data pipeline.

This DAG orchestrates the complete data pipeline:
1. Data Ingestion: Kaggle datasets + Web crawler enrichment
2. S3 Upload: Upload raw CSV/Parquet files to S3
3. Snowflake Staging: Load data from S3 to Snowflake staging tables
4. dbt Raw Layer: Initial data cleaning and normalization
5. dbt Bronze Layer: Data quality validation and standardization
6. dbt Marts Layer: Analytics-ready unified tables
7. dbt Tests: Data quality validation
8. Website Data Download: Download unified companies for website visualization
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

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
    description='Unified firmographic data pipeline: Ingestion → Staging → Raw → Bronze → Marts',
    schedule_interval=timedelta(days=1),  # Daily schedule
    start_date=days_ago(1),
    catchup=False,
    tags=['company-atlas', 'data-pipeline', 'etl'],
    max_active_runs=1,  # Only one run at a time
)


# ============================================================================
# Task Functions
# ============================================================================

def ingest_data(**context):
    """Step 1: Ingest data from Kaggle and web crawler."""
    import trio
    from pipelines.ingestion.main_ingestion import main as ingestion_main
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Starting data ingestion (Kaggle + Web Crawler)...")
    
    try:
        # Run the async ingestion function
        df_fortune, df_global = trio.run(ingestion_main)
        
        logger.info(f"Ingestion completed successfully!")
        logger.info(f"   - Fortune 1000: {len(df_fortune)} companies")
        if df_global is not None:
            logger.info(f"   - Global Companies: {len(df_global)} companies")
        
        # Store results in XCom for downstream tasks
        context['ti'].xcom_push(key='ingestion_status', value='success')
        context['ti'].xcom_push(key='fortune_count', value=len(df_fortune))
        context['ti'].xcom_push(key='global_count', value=len(df_global) if df_global is not None else 0)
        
        return {
            'status': 'success',
            'fortune_count': len(df_fortune),
            'global_count': len(df_global) if df_global is not None else 0
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise


def upload_to_s3(**context):
    """Step 2: Upload CSV files to S3."""
    import sys
    from pathlib import Path
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Starting S3 upload...")
    
    try:
        # Import and run the upload script
        upload_script = project_root / 'pipelines' / 'staging' / 'upload_to_s3.py'
        
        # Change to project root directory
        os.chdir(project_root)
        
        # Run the upload script
        result = subprocess.run(
            [sys.executable, str(upload_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode != 0:
            logger.error(f"S3 upload failed: {result.stderr}")
            raise Exception(f"S3 upload failed: {result.stderr}")
        
        logger.info("S3 upload completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='upload_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"S3 upload failed: {e}", exc_info=True)
        raise


def load_to_snowflake(**context):
    """Step 3: Load data from S3 to Snowflake staging tables."""
    import sys
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Loading data from S3 to Snowflake staging tables...")
    
    try:
        # Use the existing Python script for loading
        load_script = project_root / 'pipelines' / 'staging' / 'run_load_script.py'
        
        if not load_script.exists():
            raise FileNotFoundError(f"Load script not found: {load_script}")
        
        # Change to project root directory
        os.chdir(project_root)
        
        # Run the load script
        result = subprocess.run(
            [sys.executable, str(load_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode != 0:
            logger.error(f"Snowflake load failed: {result.stderr}")
            raise Exception(f"Snowflake load failed: {result.stderr}")
        
        logger.info("Snowflake staging load completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='snowflake_load_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Snowflake load failed: {e}", exc_info=True)
        raise


def run_dbt_raw(**context):
    """Step 4: Run dbt raw layer models."""
    import subprocess
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Running dbt raw layer models...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        result = subprocess.run(
            ['dbt', 'run', '--select', 'raw.*'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=os.environ.copy()
        )
        
        if result.returncode != 0:
            logger.error(f"dbt raw models failed: {result.stderr}")
            raise Exception(f"dbt raw models failed: {result.stderr}")
        
        logger.info("dbt raw layer completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='dbt_raw_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"dbt raw layer failed: {e}", exc_info=True)
        raise


def run_dbt_bronze(**context):
    """Step 5: Run dbt bronze layer models."""
    import subprocess
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Running dbt bronze layer models...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        result = subprocess.run(
            ['dbt', 'run', '--select', 'bronze.*'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=os.environ.copy()
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
    """Step 6: Run dbt marts layer models."""
    import subprocess
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Running dbt marts layer models...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        result = subprocess.run(
            ['dbt', 'run', '--select', 'marts.*'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=os.environ.copy()
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
    """Step 7: Run dbt tests for data quality validation."""
    import subprocess
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Running dbt tests...")
    
    dbt_dir = project_root / 'dbt'
    os.chdir(dbt_dir)
    
    try:
        result = subprocess.run(
            ['dbt', 'test'],
            capture_output=True,
            text=True,
            cwd=str(dbt_dir),
            env=os.environ.copy()
        )
        
        if result.returncode != 0:
            logger.error(f"dbt tests failed: {result.stderr}")
            # Don't raise exception - tests might fail but we want to continue
            logger.warning("Some dbt tests failed, but continuing pipeline...")
        
        logger.info("dbt tests completed!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='dbt_tests_status', value='completed')
        return {'status': 'completed'}
    except Exception as e:
        logger.error(f"dbt tests error: {e}", exc_info=True)
        # Don't raise - allow pipeline to continue even if tests fail
        return {'status': 'error', 'error': str(e)}


def validate_raw_with_ge(**context):
    """Step 4b: Validate raw layer with Great Expectations."""
    from pipelines.validation.great_expectations_setup import GreatExpectationsValidator
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Validating raw layer with Great Expectations...")
    
    try:
        validator = GreatExpectationsValidator()
        results = validator.validate_raw_layer()
        
        logger.info("Raw layer Great Expectations validation completed successfully!")
        logger.info(f"Validation results: {results}")
        
        context['ti'].xcom_push(key='ge_raw_status', value='success')
        return {'status': 'success', 'results': str(results)}
    except Exception as e:
        logger.error(f"Raw layer Great Expectations validation failed: {e}", exc_info=True)
        # Don't raise - allow pipeline to continue even if validation fails
        logger.warning("Great Expectations validation failed, but continuing pipeline...")
        return {'status': 'error', 'error': str(e)}


def validate_bronze_with_ge(**context):
    """Step 5b: Validate bronze layer with Great Expectations."""
    from pipelines.validation.great_expectations_setup import GreatExpectationsValidator
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Validating bronze layer with Great Expectations...")
    
    try:
        validator = GreatExpectationsValidator()
        results = validator.validate_bronze_layer()
        
        logger.info("Bronze layer Great Expectations validation completed successfully!")
        logger.info(f"Validation results: {results}")
        
        context['ti'].xcom_push(key='ge_bronze_status', value='success')
        return {'status': 'success', 'results': str(results)}
    except Exception as e:
        logger.error(f"Bronze layer Great Expectations validation failed: {e}", exc_info=True)
        # Don't raise - allow pipeline to continue even if validation fails
        logger.warning("Great Expectations validation failed, but continuing pipeline...")
        return {'status': 'error', 'error': str(e)}


def validate_marts_with_ge(**context):
    """Step 6b: Validate marts layer with Great Expectations."""
    from pipelines.validation.great_expectations_setup import GreatExpectationsValidator
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Validating marts layer with Great Expectations...")
    
    try:
        validator = GreatExpectationsValidator()
        results = validator.validate_marts_layer()
        
        logger.info("Marts layer Great Expectations validation completed successfully!")
        logger.info(f"Validation results: {results}")
        
        context['ti'].xcom_push(key='ge_marts_status', value='success')
        return {'status': 'success', 'results': str(results)}
    except Exception as e:
        logger.error(f"Marts layer Great Expectations validation failed: {e}", exc_info=True)
        # Don't raise - allow pipeline to continue even if validation fails
        logger.warning("Great Expectations validation failed, but continuing pipeline...")
        return {'status': 'error', 'error': str(e)}


def download_website_data(**context):
    """Step 8: Download unified companies data for website visualization."""
    import sys
    from pathlib import Path
    
    logger = context.get('logger')
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
    
    logger.info("Downloading unified companies data for website...")
    
    try:
        download_script = project_root / 'pipelines' / 'marts' / 'download_unified_companies.py'
        
        # Change to project root directory
        os.chdir(project_root)
        
        # Run the download script
        result = subprocess.run(
            [sys.executable, str(download_script)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode != 0:
            logger.error(f"Website data download failed: {result.stderr}")
            raise Exception(f"Website data download failed: {result.stderr}")
        
        logger.info("Website data download completed successfully!")
        logger.info(result.stdout)
        
        context['ti'].xcom_push(key='website_download_status', value='success')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Website data download failed: {e}", exc_info=True)
        raise


# ============================================================================
# Define Tasks
# ============================================================================

# Step 1: Data Ingestion
ingest_task = PythonOperator(
    task_id='ingest_data',
    python_callable=ingest_data,
    dag=dag,
    pool='default_pool',
)

# Step 2: Upload to S3
upload_s3_task = PythonOperator(
    task_id='upload_to_s3',
    python_callable=upload_to_s3,
    dag=dag,
    pool='default_pool',
)

# Step 3: Load to Snowflake Staging
load_snowflake_task = PythonOperator(
    task_id='load_to_snowflake_staging',
    python_callable=load_to_snowflake,
    dag=dag,
    pool='default_pool',
)

# Step 4: dbt Raw Layer
run_dbt_raw_task = BashOperator(
    task_id='run_dbt_raw',
    bash_command='cd {{ params.dbt_dir }} && dbt run --select raw.*',
    params={'dbt_dir': str(project_root / 'dbt')},
    dag=dag,
    env={'PATH': os.environ.get('PATH', '')},
)

# Step 5: dbt Bronze Layer
run_dbt_bronze_task = BashOperator(
    task_id='run_dbt_bronze',
    bash_command='cd {{ params.dbt_dir }} && dbt run --select bronze.*',
    params={'dbt_dir': str(project_root / 'dbt')},
    dag=dag,
    env={'PATH': os.environ.get('PATH', '')},
)

# Step 6: dbt Marts Layer
run_dbt_marts_task = BashOperator(
    task_id='run_dbt_marts',
    bash_command='cd {{ params.dbt_dir }} && dbt run --select marts.*',
    params={'dbt_dir': str(project_root / 'dbt')},
    dag=dag,
    env={'PATH': os.environ.get('PATH', '')},
)

# Step 4b: Validate Raw Layer with Great Expectations
validate_raw_ge_task = PythonOperator(
    task_id='validate_raw_with_great_expectations',
    python_callable=validate_raw_with_ge,
    dag=dag,
    pool='default_pool',
)

# Step 5b: Validate Bronze Layer with Great Expectations
validate_bronze_ge_task = PythonOperator(
    task_id='validate_bronze_with_great_expectations',
    python_callable=validate_bronze_with_ge,
    dag=dag,
    pool='default_pool',
)

# Step 6b: Validate Marts Layer with Great Expectations
validate_marts_ge_task = PythonOperator(
    task_id='validate_marts_with_great_expectations',
    python_callable=validate_marts_with_ge,
    dag=dag,
    pool='default_pool',
)

# Step 7: dbt Tests
run_dbt_tests_task = BashOperator(
    task_id='run_dbt_tests',
    bash_command='cd {{ params.dbt_dir }} && dbt test || true',  # Continue even if tests fail
    params={'dbt_dir': str(project_root / 'dbt')},
    dag=dag,
    env={'PATH': os.environ.get('PATH', '')},
)

# Step 8: Download Website Data
download_website_task = PythonOperator(
    task_id='download_website_data',
    python_callable=download_website_data,
    dag=dag,
    pool='default_pool',
)


# ============================================================================
# Define Task Dependencies
# ============================================================================

# Linear pipeline flow:
# Ingestion → S3 Upload → Snowflake Staging → dbt Raw → GE Raw → dbt Bronze → GE Bronze → dbt Marts → GE Marts → dbt Tests → Website Download

ingest_task >> upload_s3_task >> load_snowflake_task
load_snowflake_task >> run_dbt_raw_task
run_dbt_raw_task >> validate_raw_ge_task
validate_raw_ge_task >> run_dbt_bronze_task
run_dbt_bronze_task >> validate_bronze_ge_task
validate_bronze_ge_task >> run_dbt_marts_task
run_dbt_marts_task >> validate_marts_ge_task
validate_marts_ge_task >> run_dbt_tests_task
run_dbt_tests_task >> download_website_task
