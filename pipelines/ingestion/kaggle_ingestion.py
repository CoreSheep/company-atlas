"""
Kaggle dataset ingestion module.
Downloads and processes company data from Kaggle datasets.
"""

import os
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import kaggle
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KaggleIngestion:
    """Handles ingestion of company data from Kaggle datasets."""
    
    def __init__(self, output_dir: str = "data/raw"):
        """
        Initialize Kaggle ingestion.
        
        Args:
            output_dir: Directory to save downloaded data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure Kaggle API
        kaggle.api.authenticate()
        
    def download_techsalerator_usa(self) -> pd.DataFrame:
        """
        Download Techsalerator's USA company dataset.
        Falls back to alternative publicly available USA company datasets if the original is not accessible.
        
        Returns:
            DataFrame with company data
        """
        logger.info("Downloading Techsalerator's USA dataset...")
        
        # Try multiple dataset options
        dataset_options = [
            "techsalerator/techsalerator-companies-dataset",
            "jeannicolasduval/2024-fortune-1000-companies",  # Fallback: Fortune 1000 companies
            "rm1000/fortune-500-companies",  # Fallback: Fortune 500 companies
        ]
        
        local_path = self.output_dir / "techsalerator_usa"
        local_path.mkdir(exist_ok=True)
        
        for dataset in dataset_options:
            try:
                logger.info(f"Trying dataset: {dataset}")
                kaggle.api.dataset_download_files(
                    dataset,
                    path=str(local_path),
                    unzip=True,
                    quiet=False
                )
                
                # Find CSV or Parquet files
                csv_files = list(local_path.glob("*.csv"))
                parquet_files = list(local_path.glob("*.parquet"))
                
                if csv_files or parquet_files:
                    logger.info(f"Successfully downloaded dataset: {dataset}")
                    
                    # Read files (prioritize CSV, fall back to parquet)
                    if csv_files:
                        if len(csv_files) == 1:
                            df = pd.read_csv(csv_files[0])
                        else:
                            # Combine multiple CSV files
                            dfs = [pd.read_csv(f) for f in csv_files]
                            df = pd.concat(dfs, ignore_index=True)
                    elif parquet_files:
                        if len(parquet_files) == 1:
                            df = pd.read_parquet(parquet_files[0])
                        else:
                            # Combine multiple parquet files
                            dfs = [pd.read_parquet(f) for f in parquet_files]
                            df = pd.concat(dfs, ignore_index=True)
                    
                    logger.info(f"Downloaded {len(df)} records from {dataset}")
                    return df
                else:
                    logger.warning(f"No CSV files found in {dataset}, trying next option...")
                    # Clean up and try next
                    import shutil
                    if local_path.exists():
                        shutil.rmtree(local_path)
                    local_path.mkdir(exist_ok=True)
                    
            except Exception as e:
                logger.warning(f"Failed to download {dataset}: {e}")
                # Clean up and try next
                import shutil
                if local_path.exists():
                    shutil.rmtree(local_path)
                local_path.mkdir(exist_ok=True)
                continue
        
        # If all datasets failed, raise error
        raise Exception("Failed to download any USA company dataset. Please check your Kaggle API credentials and ensure you have accepted the dataset terms on Kaggle website.")
    
    def download_17m_company_dataset(self) -> pd.DataFrame:
        """
        Download The 17M+ Company Dataset.
        Falls back to alternative publicly available global company datasets if the original is not accessible.
        
        Returns:
            DataFrame with company data
        """
        logger.info("Downloading The 17M+ Company Dataset...")
        
        # Try multiple dataset options for global company data
        dataset_options = [
            "justinas/companies-dataset",
            "bhavikjikadara/top-worlds-companies",  # Fallback: Top world's companies
            "joebeachcapital/top-2000-companies-globally",  # Fallback: Top 2000 companies globally
            "mysarahmadbhat/inc-5000-companies",  # Fallback: Inc 5000 companies
        ]
        
        local_path = self.output_dir / "17m_companies"
        local_path.mkdir(exist_ok=True)
        
        for dataset in dataset_options:
            try:
                logger.info(f"Trying dataset: {dataset}")
                kaggle.api.dataset_download_files(
                    dataset,
                    path=str(local_path),
                    unzip=True,
                    quiet=False
                )
                
                # Find CSV or Parquet files
                csv_files = list(local_path.glob("*.csv"))
                parquet_files = list(local_path.glob("*.parquet"))
                
                if csv_files or parquet_files:
                    logger.info(f"Successfully downloaded dataset: {dataset}")
                    
                    # Read files (prioritize CSV, fall back to parquet)
                    if csv_files:
                        if len(csv_files) == 1:
                            df = pd.read_csv(csv_files[0])
                        else:
                            # Combine multiple CSV files
                            dfs = []
                            for csv_file in csv_files:
                                df_chunk = pd.read_csv(csv_file)
                                dfs.append(df_chunk)
                            df = pd.concat(dfs, ignore_index=True)
                    elif parquet_files:
                        if len(parquet_files) == 1:
                            df = pd.read_parquet(parquet_files[0])
                        else:
                            # Combine multiple parquet files
                            dfs = []
                            for parquet_file in parquet_files:
                                df_chunk = pd.read_parquet(parquet_file)
                                dfs.append(df_chunk)
                            df = pd.concat(dfs, ignore_index=True)
                    
                    logger.info(f"Downloaded {len(df)} records from {dataset}")
                    return df
                else:
                    logger.warning(f"No CSV files found in {dataset}, trying next option...")
                    # Clean up and try next
                    import shutil
                    if local_path.exists():
                        shutil.rmtree(local_path)
                    local_path.mkdir(exist_ok=True)
                    
            except Exception as e:
                logger.warning(f"Failed to download {dataset}: {e}")
                # Clean up and try next
                import shutil
                if local_path.exists():
                    shutil.rmtree(local_path)
                local_path.mkdir(exist_ok=True)
                continue
        
        # If all datasets failed, raise error
        raise Exception("Failed to download any global company dataset. Please check your Kaggle API credentials and ensure you have accepted the dataset terms on Kaggle website.")
    
    def normalize_schema(
        self, 
        df: pd.DataFrame, 
        source_system: str,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Normalize dataset to unified schema.
        
        Args:
            df: Input DataFrame
            source_system: Source system identifier
            column_mapping: Optional mapping from source columns to target columns
            
        Returns:
            Normalized DataFrame with unified schema
        """
        logger.info(f"Normalizing schema for {source_system}...")
        
        # Default column mappings (adjust based on actual dataset structure)
        default_mapping = {
            "name": "company_name",
            "company": "company_name",
            "company_name": "company_name",
            "domain": "domain",
            "website": "domain",
            "url": "domain",
            "industry": "industry",
            "industry_type": "industry",
            "sector": "industry",
            "country": "country",
            "country_code": "country",
            "employees": "employee_count",
            "employee_count": "employee_count",
            "num_employees": "employee_count",
            "revenue": "revenue",
            "annual_revenue": "revenue",
            "founded": "founded_year",
            "founded_year": "founded_year",
            "year_founded": "founded_year",
        }
        
        if column_mapping:
            default_mapping.update(column_mapping)
        
        # Rename columns
        df_normalized = df.copy()
        rename_dict = {}
        for source_col in df.columns:
            source_col_lower = source_col.lower().strip()
            if source_col_lower in default_mapping:
                rename_dict[source_col] = default_mapping[source_col_lower]
        
        df_normalized = df_normalized.rename(columns=rename_dict)
        
        # Ensure required columns exist (create empty if missing)
        required_columns = [
            "company_name",
            "domain",
            "industry",
            "country",
            "employee_count",
            "revenue",
            "founded_year"
        ]
        
        for col in required_columns:
            if col not in df_normalized.columns:
                df_normalized[col] = None
        
        # Add metadata columns
        df_normalized["source_system"] = source_system
        df_normalized["last_updated_at"] = datetime.utcnow().isoformat()
        
        # Select and order columns
        final_columns = required_columns + ["source_system", "last_updated_at"]
        df_normalized = df_normalized[final_columns]
        
        logger.info(f"Normalized {len(df_normalized)} records")
        return df_normalized
    
    def ingest_all(self) -> List[pd.DataFrame]:
        """
        Ingest all configured datasets.
        
        Returns:
            List of normalized DataFrames
        """
        results = []
        
        # Ingest Techsalerator USA
        try:
            df_tech = self.download_techsalerator_usa()
            df_tech_normalized = self.normalize_schema(df_tech, "techsalerator_usa")
            results.append(df_tech_normalized)
        except Exception as e:
            logger.error(f"Failed to ingest Techsalerator USA: {e}")
        
        # Ingest 17M+ Company Dataset
        try:
            df_17m = self.download_17m_company_dataset()
            df_17m_normalized = self.normalize_schema(df_17m, "17m_companies")
            results.append(df_17m_normalized)
        except Exception as e:
            logger.error(f"Failed to ingest 17M+ Company Dataset: {e}")
        
        return results


if __name__ == "__main__":
    ingester = KaggleIngestion()
    datasets = ingester.ingest_all()
    print(f"Ingested {len(datasets)} datasets")

