"""
Script to execute load_data_from_s3.sql in Snowflake.
"""

import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_snowflake_connection():
    """Get Snowflake connection."""
    try:
        # Try private key authentication first
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
                database='COMPANY_ATLAS',
                schema='STAGING',
                role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM')
            )
        else:
            # Fall back to password authentication
            conn = snowflake.connector.connect(
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                user=os.getenv('SNOWFLAKE_USER'),
                password=os.getenv('SNOWFLAKE_PASSWORD'),
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                database='COMPANY_ATLAS',
                schema='STAGING',
                role=os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM')
            )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
        raise


def execute_sql_file(conn, sql_file_path: Path):
    """Execute SQL file statement by statement."""
    logger.info(f"Reading SQL file: {sql_file_path}")
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    # Split by semicolon, but be careful with semicolons in strings/comments
    # Simple approach: split by semicolon and filter out empty/comment-only statements
    statements = []
    current_statement = []
    
    for line in sql_content.split('\n'):
        stripped = line.strip()
        # Skip empty lines and comment-only lines
        if not stripped or stripped.startswith('--'):
            if current_statement:
                current_statement.append(line)
            continue
        
        current_statement.append(line)
        
        # If line ends with semicolon, it's the end of a statement
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
            current_statement = []
    
    # Add any remaining statement
    if current_statement:
        statement = '\n'.join(current_statement).strip()
        if statement and not statement.startswith('--'):
            statements.append(statement)
    
    logger.info(f"Found {len(statements)} SQL statements to execute")
    
    cursor = conn.cursor()
    results = []
    
    try:
        for i, statement in enumerate(statements, 1):
            # Skip empty statements
            if not statement or statement.strip() == ';':
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Executing statement {i}/{len(statements)}")
            logger.info(f"{'='*60}")
            logger.debug(f"SQL: {statement[:200]}...")
            
            try:
                cursor.execute(statement)
                
                # Try to fetch results if it's a SELECT statement
                if statement.strip().upper().startswith('SELECT') or statement.strip().upper().startswith('SHOW') or statement.strip().upper().startswith('LIST') or statement.strip().upper().startswith('DESCRIBE'):
                    rows = cursor.fetchall()
                    if rows:
                        logger.info(f"Result ({len(rows)} rows):")
                        # Print column names if available
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            logger.info(f"Columns: {', '.join(columns)}")
                        # Print first few rows
                        for row in rows[:10]:
                            logger.info(f"  {row}")
                        if len(rows) > 10:
                            logger.info(f"  ... and {len(rows) - 10} more rows")
                        results.append((statement, rows))
                    else:
                        logger.info("No rows returned")
                else:
                    logger.info("Statement executed successfully")
                    results.append((statement, None))
                    
            except Exception as e:
                logger.error(f"Error executing statement {i}: {e}")
                logger.error(f"Statement: {statement[:500]}")
                # Continue with next statement
                results.append((statement, f"ERROR: {e}"))
        
        conn.commit()
        logger.info("\n" + "="*60)
        logger.info("All statements executed")
        logger.info("="*60)
        
    finally:
        cursor.close()
    
    return results


def main():
    """Main function."""
    logger.info("="*60)
    logger.info("Loading Data from S3 to Snowflake")
    logger.info("="*60)
    
    # Get SQL file path
    script_dir = Path(__file__).parent
    sql_file = script_dir / "load_data_from_s3.sql"
    
    if not sql_file.exists():
        logger.error(f"SQL file not found: {sql_file}")
        sys.exit(1)
    
    try:
        # Connect to Snowflake
        logger.info("Connecting to Snowflake...")
        conn = get_snowflake_connection()
        logger.info("Connected successfully!")
        
        # Execute SQL file
        results = execute_sql_file(conn, sql_file)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("Execution Summary")
        logger.info("="*60)
        logger.info(f"Total statements: {len(results)}")
        logger.info(f"Successful: {sum(1 for r in results if r[1] is not None and not isinstance(r[1], str))}")
        logger.info(f"Errors: {sum(1 for r in results if isinstance(r[1], str))}")
        
        conn.close()
        logger.info("\n✅ Script execution completed!")
        
    except Exception as e:
        logger.error(f"\n❌ Failed to execute script: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

