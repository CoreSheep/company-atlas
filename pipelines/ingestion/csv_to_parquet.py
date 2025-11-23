"""
Convert CSV files to Parquet format.
Transforms fortune1000_companies.csv and global_companies.csv to Parquet files.
"""

import logging
import pandas as pd
from pathlib import Path
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def csv_to_parquet(csv_path: Path, parquet_path: Path = None, optimize: bool = True) -> Path:
    """
    Convert CSV file to Parquet format.
    
    Args:
        csv_path: Path to input CSV file
        parquet_path: Path to output Parquet file (defaults to same name with .parquet extension)
        optimize: Whether to optimize data types for Parquet
        
    Returns:
        Path to created Parquet file
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    if parquet_path is None:
        parquet_path = csv_path.with_suffix('.parquet')
    
    logger.info(f"Converting {csv_path.name} to Parquet...")
    logger.info(f"Input: {csv_path}")
    logger.info(f"Output: {parquet_path}")
    
    try:
        # Read CSV file
        logger.info("Reading CSV file...")
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
        
        # Optimize data types for Parquet
        if optimize:
            logger.info("Optimizing data types...")
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Try to convert to category for string columns with low cardinality
                    if df[col].nunique() < len(df) * 0.5:
                        df[col] = df[col].astype('category')
                elif df[col].dtype in ['int64']:
                    # Downcast integers if possible
                    df[col] = pd.to_numeric(df[col], downcast='integer', errors='ignore')
                elif df[col].dtype in ['float64']:
                    # Downcast floats if possible
                    df[col] = pd.to_numeric(df[col], downcast='float', errors='ignore')
        
        # Convert date columns if present
        for col in df.columns:
            if 'date' in col.lower() or 'updated_at' in col.lower() or 'created_at' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except:
                    pass
        
        # Write to Parquet
        logger.info("Writing Parquet file...")
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(
            parquet_path,
            index=False,
            engine='pyarrow',
            compression='snappy',  # Good balance of speed and compression
            write_statistics=True
        )
        
        # Get file sizes
        csv_size = csv_path.stat().st_size / (1024 * 1024)  # MB
        parquet_size = parquet_path.stat().st_size / (1024 * 1024)  # MB
        compression_ratio = (1 - parquet_size / csv_size) * 100 if csv_size > 0 else 0
        
        logger.info(f"Successfully converted to Parquet!")
        logger.info(f"   CSV size: {csv_size:.2f} MB")
        logger.info(f"   Parquet size: {parquet_size:.2f} MB")
        logger.info(f"   Compression ratio: {compression_ratio:.1f}%")
        logger.info(f"   Records: {len(df)}")
        logger.info(f"   Columns: {list(df.columns)}")
        
        return parquet_path
        
    except Exception as e:
        logger.error(f"Error converting CSV to Parquet: {e}", exc_info=True)
        raise


def convert_all_csv_files(data_dir: Path):
    """
    Convert all CSV files in data directory to Parquet format.
    
    Args:
        data_dir: Directory containing CSV files
    """
    logger.info("="*60)
    logger.info("Converting CSV files to Parquet format")
    logger.info("="*60)
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    # Find CSV files
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return
    
    logger.info(f"Found {len(csv_files)} CSV file(s) to convert:\n")
    
    converted_files = []
    
    for csv_file in csv_files:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Converting: {csv_file.name}")
            logger.info(f"{'='*60}")
            
            parquet_path = csv_to_parquet(csv_file, optimize=True)
            converted_files.append((csv_file, parquet_path))
            
        except Exception as e:
            logger.error(f"Failed to convert {csv_file.name}: {e}")
            continue
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Conversion Summary")
    logger.info("="*60)
    
    for csv_file, parquet_file in converted_files:
        csv_size = csv_file.stat().st_size / (1024 * 1024)
        parquet_size = parquet_file.stat().st_size / (1024 * 1024)
        compression = (1 - parquet_size / csv_size) * 100 if csv_size > 0 else 0
        
        logger.info(f"\n{csv_file.name}:")
        logger.info(f"  CSV: {csv_size:.2f} MB")
        logger.info(f"  Parquet: {parquet_size:.2f} MB")
        logger.info(f"  Compression: {compression:.1f}%")
        logger.info(f"  Output: {parquet_file}")
    
    logger.info(f"\nSuccessfully converted {len(converted_files)} file(s)!")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert CSV files to Parquet format')
    parser.add_argument(
        '--input',
        type=str,
        default='company-atlas/data/raw/fortune1000_companies.csv',
        help='Input CSV file path (default: company-atlas/data/raw/fortune1000_companies.csv)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output Parquet file path (default: same as input with .parquet extension)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='company-atlas/data/raw',
        help='Convert all CSV files in this directory (optional)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Convert all CSV files in data directory'
    )
    parser.add_argument(
        '--no-optimize',
        action='store_true',
        help='Disable data type optimization'
    )
    
    args = parser.parse_args()
    
    try:
        if args.all:
            # Convert all CSV files in directory
            data_dir = Path(args.data_dir)
            convert_all_csv_files(data_dir)
        else:
            # Convert single file
            csv_path = Path(args.input)
            parquet_path = Path(args.output) if args.output else None
            
            parquet_file = csv_to_parquet(
                csv_path,
                parquet_path=parquet_path,
                optimize=not args.no_optimize
            )
            
            logger.info(f"\nConversion complete: {parquet_file}")
            
    except Exception as e:
        logger.error(f"\nConversion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

