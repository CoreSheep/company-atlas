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

