"""
Great Expectations validation setup for Company Atlas pipeline.
"""

import os
import logging
from pathlib import Path
import great_expectations as ge
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.data_context import BaseDataContext
from great_expectations.data_context.types.base import DataContextConfig, FilesystemStoreBackendDefaults
from dotenv import load_dotenv
import snowflake.connector
import pandas as pd

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GreatExpectationsValidator:
    """Great Expectations validator for data quality checks."""
    
    def __init__(self, context_root_dir: str = "great_expectations"):
        """
        Initialize Great Expectations context.
        
        Args:
            context_root_dir: Root directory for Great Expectations context
        """
        self.context_root_dir = Path(context_root_dir)
        self.context = self._initialize_context()
    
    def _initialize_context(self):
        """Initialize Great Expectations data context."""
        try:
            if self.context_root_dir.exists():
                context = ge.data_context.DataContext(str(self.context_root_dir))
            else:
                context = ge.data_context.DataContext()
                logger.info(f"Created new Great Expectations context at {context.root_directory}")
            
            return context
        except Exception as e:
            logger.error(f"Error initializing Great Expectations context: {e}")
            raise
    
    def _get_snowflake_connection(self):
        """Get Snowflake connection."""
        try:
            private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH', '')
            if private_key_path and os.path.exists(private_key_path):
                from cryptography.hazmat.primitives import serialization
                from cryptography.hazmat.backends import default_backend
                
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
                    role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM'),
                    database=os.getenv('SNOWFLAKE_DATABASE', 'COMPANY_ATLAS'),
                )
            else:
                conn = snowflake.connector.connect(
                    account=os.getenv('SNOWFLAKE_ACCOUNT'),
                    user=os.getenv('SNOWFLAKE_USER'),
                    password=os.getenv('SNOWFLAKE_PASSWORD'),
                    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                    role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM'),
                    database=os.getenv('SNOWFLAKE_DATABASE', 'COMPANY_ATLAS'),
                )
            return conn
        except Exception as e:
            logger.error(f"Error connecting to Snowflake: {e}")
            raise
    
    def _validate_dataframe(self, df, suite_name, expectations_func):
        """Generic validation function for DataFrames."""
        try:
            if suite_name not in self.context.list_expectation_suite_names():
                suite = self.context.create_expectation_suite(suite_name)
            else:
                suite = self.context.get_expectation_suite(suite_name)
            
            validator = self.context.get_validator(
                batch_request=RuntimeBatchRequest(
                    datasource_name="pandas_datasource",
                    data_asset_name=suite_name.replace("_suite", ""),
                    runtime_parameters={"batch_data": df},
                    batch_identifiers={"default_identifier_name": "default_identifier"},
                ),
                expectation_suite_name=suite_name
            )
            
            # Apply expectations
            expectations_func(validator)
            
            # Save expectations
            validator.save_expectation_suite(discard_failed_expectations=False)
            
            # Run validation
            checkpoint_name = f"{suite_name.replace('_suite', '')}_checkpoint"
            checkpoint_result = self.context.run_checkpoint(
                checkpoint_name=checkpoint_name,
                validations=[
                    {
                        "batch_request": RuntimeBatchRequest(
                            datasource_name="pandas_datasource",
                            data_asset_name=suite_name.replace("_suite", ""),
                            runtime_parameters={"batch_data": df},
                            batch_identifiers={"default_identifier_name": "default_identifier"},
                        ),
                        "expectation_suite_name": suite_name
                    }
                ]
            )
            
            logger.info(f"Great Expectations validation completed for {suite_name}")
            return checkpoint_result
        except Exception as e:
            logger.error(f"Error running Great Expectations validation: {e}")
            raise
    
    def validate_unified_companies(self, df):
        """
        Validate unified companies dataset.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Validation result
        """
        try:
            # Create expectation suite
            suite_name = "unified_companies_suite"
            if suite_name not in self.context.list_expectation_suite_names():
                suite = self.context.create_expectation_suite(suite_name)
            else:
                suite = self.context.get_expectation_suite(suite_name)
            
            # Add expectations
            validator = self.context.get_validator(
                batch_request=RuntimeBatchRequest(
                    datasource_name="pandas_datasource",
                    data_asset_name="unified_companies",
                    runtime_parameters={"batch_data": df},
                    batch_identifiers={"default_identifier_name": "default_identifier"},
                ),
                expectation_suite_name=suite_name
            )
            
            # Column expectations
            validator.expect_column_to_exist("company_name")
            validator.expect_column_values_to_not_be_null("company_name")
            validator.expect_column_to_exist("domain")
            validator.expect_column_to_exist("source_system")
            validator.expect_column_values_to_not_be_null("source_system")
            
            # Data quality expectations
            validator.expect_column_values_to_be_unique("company_id", mostly=0.99)
            validator.expect_column_values_to_be_of_type("employee_count", "int64", mostly=0.95)
            validator.expect_column_values_to_be_of_type("founded_year", "int64", mostly=0.95)
            
            # Range checks
            validator.expect_column_values_to_be_between(
                "founded_year",
                min_value=1800,
                max_value=2030,
                mostly=0.95
            )
            
            validator.expect_column_values_to_be_between(
                "employee_count",
                min_value=0,
                mostly=0.95
            )
            
            # Save expectations
            validator.save_expectation_suite(discard_failed_expectations=False)
            
            # Run validation
            checkpoint_name = "unified_companies_checkpoint"
            checkpoint_result = self.context.run_checkpoint(
                checkpoint_name=checkpoint_name,
                validations=[
                    {
                        "batch_request": RuntimeBatchRequest(
                            datasource_name="pandas_datasource",
                            data_asset_name="unified_companies",
                            runtime_parameters={"batch_data": df},
                            batch_identifiers={"default_identifier_name": "default_identifier"},
                        ),
                        "expectation_suite_name": suite_name
                    }
                ]
            )
            
            logger.info("Great Expectations validation completed")
            return checkpoint_result
            
        except Exception as e:
            logger.error(f"Error running Great Expectations validation: {e}")
            raise
    
    def validate_raw_layer(self):
        """Validate raw layer tables from Snowflake."""
        logger.info("Validating raw layer tables...")
        conn = self._get_snowflake_connection()
        
        try:
            # Validate raw_dim_companies
            logger.info("Validating raw_dim_companies...")
            df_dim = pd.read_sql(
                "SELECT * FROM COMPANY_ATLAS.RAW.RAW_DIM_COMPANIES LIMIT 10000",
                conn
            )
            
            def raw_dim_expectations(validator):
                validator.expect_column_to_exist("company_id")
                validator.expect_column_values_to_not_be_null("company_id", mostly=0.99)
                validator.expect_column_to_exist("company_name")
                validator.expect_column_values_to_not_be_null("company_name", mostly=0.99)
                validator.expect_column_to_exist("source_system")
                validator.expect_column_values_to_not_be_null("source_system", mostly=0.95)
                if "founded_year" in df_dim.columns:
                    validator.expect_column_values_to_be_between(
                        "founded_year",
                        min_value=1800,
                        max_value=2030,
                        mostly=0.90
                    )
            
            result_dim = self._validate_dataframe(df_dim, "raw_dim_companies_suite", raw_dim_expectations)
            
            # Validate raw_fct_company_metrics
            logger.info("Validating raw_fct_company_metrics...")
            df_fct = pd.read_sql(
                "SELECT * FROM COMPANY_ATLAS.RAW.RAW_FCT_COMPANY_METRICS LIMIT 10000",
                conn
            )
            
            def raw_fct_expectations(validator):
                validator.expect_column_to_exist("company_id")
                validator.expect_column_values_to_not_be_null("company_id", mostly=0.99)
                validator.expect_column_to_exist("company_name")
                validator.expect_column_values_to_not_be_null("company_name", mostly=0.99)
                validator.expect_column_to_exist("metric_date")
                validator.expect_column_values_to_not_be_null("metric_date", mostly=0.95)
                validator.expect_column_to_exist("source_system")
                validator.expect_column_values_to_not_be_null("source_system", mostly=0.95)
                if "fortune_rank" in df_fct.columns:
                    validator.expect_column_values_to_be_between(
                        "fortune_rank",
                        min_value=1,
                        max_value=1000,
                        mostly=0.90
                    )
            
            result_fct = self._validate_dataframe(df_fct, "raw_fct_company_metrics_suite", raw_fct_expectations)
            
            conn.close()
            logger.info("Raw layer validation completed")
            return {"raw_dim_companies": result_dim, "raw_fct_company_metrics": result_fct}
        except Exception as e:
            logger.error(f"Error validating raw layer: {e}")
            if conn:
                conn.close()
            raise
    
    def validate_bronze_layer(self):
        """Validate bronze layer tables from Snowflake."""
        logger.info("Validating bronze layer tables...")
        conn = self._get_snowflake_connection()
        
        try:
            # Validate bronze_dim_companies
            logger.info("Validating bronze_dim_companies...")
            df_dim = pd.read_sql(
                "SELECT * FROM COMPANY_ATLAS.BRONZE.BRONZE_DIM_COMPANIES LIMIT 10000",
                conn
            )
            
            def bronze_dim_expectations(validator):
                validator.expect_column_to_exist("company_id")
                validator.expect_column_values_to_not_be_null("company_id", mostly=0.99)
                validator.expect_column_values_to_be_unique("company_id", mostly=0.99)
                validator.expect_column_to_exist("company_name")
                validator.expect_column_values_to_not_be_null("company_name", mostly=0.99)
                validator.expect_column_values_to_be_unique("company_name", mostly=0.99)
                validator.expect_column_to_exist("source_system")
                validator.expect_column_values_to_not_be_null("source_system", mostly=0.95)
                if "founded_year" in df_dim.columns:
                    validator.expect_column_values_to_be_between(
                        "founded_year",
                        min_value=1800,
                        max_value=2030,
                        mostly=0.90
                    )
            
            result_dim = self._validate_dataframe(df_dim, "bronze_dim_companies_suite", bronze_dim_expectations)
            
            # Validate bronze_fct_company_metrics
            logger.info("Validating bronze_fct_company_metrics...")
            df_fct = pd.read_sql(
                "SELECT * FROM COMPANY_ATLAS.BRONZE.BRONZE_FCT_COMPANY_METRICS LIMIT 10000",
                conn
            )
            
            def bronze_fct_expectations(validator):
                validator.expect_column_to_exist("company_id")
                validator.expect_column_values_to_not_be_null("company_id", mostly=0.99)
                validator.expect_column_to_exist("company_name")
                validator.expect_column_values_to_not_be_null("company_name", mostly=0.99)
                validator.expect_column_to_exist("metric_date")
                validator.expect_column_values_to_not_be_null("metric_date", mostly=0.95)
                validator.expect_column_to_exist("source_system")
                validator.expect_column_values_to_not_be_null("source_system", mostly=0.95)
                if "fortune_rank" in df_fct.columns:
                    validator.expect_column_values_to_be_between(
                        "fortune_rank",
                        min_value=1,
                        max_value=1000,
                        mostly=0.90
                    )
                if "employee_count" in df_fct.columns:
                    validator.expect_column_values_to_be_between(
                        "employee_count",
                        min_value=0,
                        mostly=0.90
                    )
            
            result_fct = self._validate_dataframe(df_fct, "bronze_fct_company_metrics_suite", bronze_fct_expectations)
            
            conn.close()
            logger.info("Bronze layer validation completed")
            return {"bronze_dim_companies": result_dim, "bronze_fct_company_metrics": result_fct}
        except Exception as e:
            logger.error(f"Error validating bronze layer: {e}")
            if conn:
                conn.close()
            raise
    
    def validate_marts_layer(self):
        """Validate marts layer tables from Snowflake."""
        logger.info("Validating marts layer tables...")
        conn = self._get_snowflake_connection()
        
        try:
            # Validate unified_companies
            logger.info("Validating unified_companies...")
            df = pd.read_sql(
                "SELECT * FROM COMPANY_ATLAS.MARTS.UNIFIED_COMPANIES LIMIT 10000",
                conn
            )
            
            def marts_expectations(validator):
                validator.expect_column_to_exist("company_id")
                validator.expect_column_values_to_not_be_null("company_id", mostly=0.99)
                validator.expect_column_values_to_be_unique("company_id", mostly=0.99)
                validator.expect_column_to_exist("company_name")
                validator.expect_column_values_to_not_be_null("company_name", mostly=0.99)
                validator.expect_column_values_to_be_unique("company_name", mostly=0.99)
                validator.expect_column_to_exist("source_system")
                validator.expect_column_values_to_not_be_null("source_system", mostly=0.95)
                if "country" in df.columns:
                    validator.expect_column_values_to_not_be_null("country", mostly=0.90)
                if "founded_year" in df.columns:
                    validator.expect_column_values_to_be_between(
                        "founded_year",
                        min_value=1800,
                        max_value=2030,
                        mostly=0.90
                    )
                if "fortune_rank" in df.columns:
                    validator.expect_column_values_to_be_between(
                        "fortune_rank",
                        min_value=1,
                        max_value=1000,
                        mostly=0.90
                    )
                if "employee_count" in df.columns:
                    validator.expect_column_values_to_be_between(
                        "employee_count",
                        min_value=0,
                        mostly=0.90
                    )
            
            result = self._validate_dataframe(df, "unified_companies_suite", marts_expectations)
            
            conn.close()
            logger.info("Marts layer validation completed")
            return {"unified_companies": result}
        except Exception as e:
            logger.error(f"Error validating marts layer: {e}")
            if conn:
                conn.close()
            raise


if __name__ == "__main__":
    import pandas as pd
    
    # Test validator
    validator = GreatExpectationsValidator()
    test_df = pd.DataFrame({
        "company_id": ["1", "2"],
        "company_name": ["Test Corp", "Another Corp"],
        "domain": ["test.com", "another.com"],
        "source_system": ["test", "test"],
        "employee_count": [100, 200],
        "founded_year": [2020, 2021]
    })
    result = validator.validate_unified_companies(test_df)

