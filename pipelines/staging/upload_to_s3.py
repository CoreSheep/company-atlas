"""
Script to upload Fortune 1000 CSV files to S3.
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import boto3
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def upload_fortune1000_files(bucket_name: str = None):
    """Upload Fortune 1000 CSV files to S3.
    
    Args:
        bucket_name: S3 bucket name. If not provided, will use environment variable
                    or default to a unique name with timestamp.
    """
    
    # Get bucket name from environment variable or use default with year-month timestamp
    if bucket_name is None:
        bucket_name = os.getenv("S3_BUCKET_NAME")
        if bucket_name is None:
            # Use year-month format for bucket name (e.g., company-atlas-202411)
            timestamp = datetime.utcnow().strftime("%Y%m")
            bucket_name = f"company-atlas-{timestamp}"
            logger.info(f"No bucket name specified. Using default with year-month: {bucket_name}")
    
    logger.info(f"Using S3 bucket: {bucket_name}")
    
    # Initialize S3 client
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Verify bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket {bucket_name} exists and is accessible")
    except Exception as e:
        logger.error(f"Failed to connect to S3 or bucket doesn't exist: {e}")
        logger.error("\nPlease check:")
        logger.error("  - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set in .env")
        logger.error("  - S3_BUCKET_NAME is set or bucket name is correct")
        sys.exit(1)
    
    # File paths - using CSV files
    # Get the project root (parent of pipelines directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    file1_path = project_root / "data/raw/fortune1000/fortune1000_2024.csv"
    file2_path = project_root / "data/raw/global_companies/fortune1000_companies.csv"
    
    # Verify files exist
    if not file1_path.exists():
        logger.error(f"File not found: {file1_path}")
        logger.error(f"Current directory: {Path.cwd()}")
        logger.error(f"Looking for: {file1_path.absolute()}")
        return
    
    if not file2_path.exists():
        logger.error(f"File not found: {file2_path}")
        logger.error(f"Current directory: {Path.cwd()}")
        logger.error(f"Looking for: {file2_path.absolute()}")
        return
    
    logger.info("="*60)
    logger.info("Uploading Fortune 1000 CSV files to S3")
    logger.info("="*60)
    
    # Generate S3 keys with date partitioning
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    key1 = f"raw/fortune1000/{date_str}/fortune1000_2024.csv"
    key2 = f"raw/global_companies/{date_str}/fortune1000_companies.csv"
    
    try:
        # Upload first file
        logger.info(f"\nUploading file 1: {file1_path}")
        logger.info(f"File size: {file1_path.stat().st_size / 1024:.2f} KB")
        s3_client.upload_file(str(file1_path), bucket_name, key1)
        s3_uri1 = f"s3://{bucket_name}/{key1}"
        logger.info(f"Uploaded to: {s3_uri1}")
        
        # Upload second file
        logger.info(f"\nUploading file 2: {file2_path}")
        logger.info(f"File size: {file2_path.stat().st_size / 1024:.2f} KB")
        s3_client.upload_file(str(file2_path), bucket_name, key2)
        s3_uri2 = f"s3://{bucket_name}/{key2}"
        logger.info(f"Uploaded to: {s3_uri2}")
        
        logger.info("\n" + "="*60)
        logger.info("Upload Summary")
        logger.info("="*60)
        logger.info(f"Bucket: {bucket_name}")
        logger.info(f"File 1: {s3_uri1}")
        logger.info(f"File 2: {s3_uri2}")
        logger.info("="*60)
        logger.info("\nSuccessfully uploaded both CSV files to S3!")
        
    except Exception as e:
        logger.error(f"\nFailed to upload files: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Allow bucket name to be specified via environment variable or command line
    bucket_name = None
    if len(sys.argv) > 1:
        bucket_name = sys.argv[1]
    
    upload_fortune1000_files(bucket_name=bucket_name)

