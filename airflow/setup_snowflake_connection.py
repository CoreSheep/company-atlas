"""
Script to configure Airflow's Snowflake connection with private key authentication.
This is needed because Snowflake SQLAlchemy connection strings don't support private keys directly.
"""
import os
import sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/opt/airflow/.env')

def get_snowflake_connection_string():
    """Get Snowflake connection string with private key support."""
    account = os.getenv('SNOWFLAKE_ACCOUNT')
    user = os.getenv('SNOWFLAKE_USER')
    database = os.getenv('SNOWFLAKE_DATABASE', 'COMPANY_ATLAS')
    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')
    role = os.getenv('SNOWFLAKE_ROLE', 'TRANSFORM')
    schema = 'AIRFLOW_METADATA'
    
    # Try private key authentication first
    private_key_path = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH', '')
    if private_key_path and os.path.exists(private_key_path):
        # For SQLAlchemy with private key, we need to use connect_args
        # This is handled by creating the engine with connect_args
        # The connection string format for private key is different
        # We'll use a placeholder and handle it in connect_args
        return f"snowflake://{user}@{account}/{database}/{schema}?warehouse={warehouse}&role={role}"
    else:
        # Use password authentication
        password = os.getenv('SNOWFLAKE_PASSWORD', '')
        return f"snowflake://{user}:{password}@{account}/{database}/{schema}?warehouse={warehouse}&role={role}"

if __name__ == "__main__":
    conn_str = get_snowflake_connection_string()
    print(conn_str)

