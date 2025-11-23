"""
Apache Airflow DAG for Company Atlas data pipeline.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from pipelines.ingestion.kaggle_ingestion import KaggleIngestion
from pipelines.storage.s3_storage import S3Storage
from pipelines.storage.snowflake_staging import SnowflakeStaging
from pipelines.validation.great_expectations_setup import GreatExpectationsValidator

default_args = {
    'owner': 'company-atlas',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'company_atlas_pipeline',
    default_args=default_args,
    description='Unified firmographic data pipeline',
    schedule_interval=timedelta(days=1),
    start_date=days_ago(1),
    catchup=False,
    tags=['company-atlas', 'data-pipeline'],
)


def ingest_kaggle_data(**context):
    """Ingest data from Kaggle datasets."""
    ingester = KaggleIngestion()
    datasets = ingester.ingest_all()
    context['ti'].xcom_push(key='datasets', value=datasets)
    return datasets


def upload_to_s3(**context):
    """Upload ingested data to S3."""
    datasets = context['ti'].xcom_pull(key='datasets', task_ids='ingest_kaggle_data')
    s3_storage = S3Storage()
    
    uploaded_files = []
    for df, source_system in zip(datasets, ['techsalerator_usa', '17m_companies']):
        key = s3_storage.generate_key(source_system, format='parquet')
        s3_uri = s3_storage.upload_dataframe(df, key, format='parquet')
        uploaded_files.append((s3_uri, source_system))
    
    context['ti'].xcom_push(key='uploaded_files', value=uploaded_files)
    return uploaded_files


def load_to_snowflake(**context):
    """Load data from S3 to Snowflake staging."""
    uploaded_files = context['ti'].xcom_pull(key='uploaded_files', task_ids='upload_to_s3')
    staging = SnowflakeStaging()
    
    for s3_uri, source_system in uploaded_files:
        table_name = f"STG_{source_system.upper()}"
        staging.load_from_s3(s3_uri, table_name, file_format='parquet')
    
    staging.close()


def run_dbt_models(**context):
    """Run dbt models for transformation."""
    dbt_dir = project_root / 'dbt'
    return f"cd {dbt_dir} && dbt run"


def run_dbt_tests(**context):
    """Run dbt tests."""
    dbt_dir = project_root / 'dbt'
    return f"cd {dbt_dir} && dbt test"


def validate_with_great_expectations(**context):
    """Run Great Expectations validation."""
    # This would typically read from Snowflake unified table
    # For now, it's a placeholder
    validator = GreatExpectationsValidator()
    # validator.validate_unified_companies(unified_df)
    return "Validation completed"


def sync_to_neo4j(**context):
    """Sync unified data to Neo4j for graph visualization."""
    # Import Neo4j sync function
    from pipelines.graph.neo4j_sync import Neo4jSync
    neo4j_sync = Neo4jSync()
    neo4j_sync.sync_unified_companies()
    return "Neo4j sync completed"


# Define tasks
ingest_task = PythonOperator(
    task_id='ingest_kaggle_data',
    python_callable=ingest_kaggle_data,
    dag=dag,
)

upload_s3_task = PythonOperator(
    task_id='upload_to_s3',
    python_callable=upload_to_s3,
    dag=dag,
)

load_snowflake_task = PythonOperator(
    task_id='load_to_snowflake',
    python_callable=load_to_snowflake,
    dag=dag,
)

run_dbt_task = BashOperator(
    task_id='run_dbt_models',
    bash_command=run_dbt_models,
    dag=dag,
)

run_dbt_tests_task = BashOperator(
    task_id='run_dbt_tests',
    bash_command=run_dbt_tests,
    dag=dag,
)

validate_ge_task = PythonOperator(
    task_id='validate_with_great_expectations',
    python_callable=validate_with_great_expectations,
    dag=dag,
)

sync_neo4j_task = PythonOperator(
    task_id='sync_to_neo4j',
    python_callable=sync_to_neo4j,
    dag=dag,
)

# Define task dependencies
ingest_task >> upload_s3_task >> load_snowflake_task >> run_dbt_task
run_dbt_task >> run_dbt_tests_task >> validate_ge_task
validate_ge_task >> sync_neo4j_task

