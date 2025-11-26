FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    AIRFLOW_HOME=/opt/airflow \
    AIRFLOW__CORE__EXECUTOR=SequentialExecutor \
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow \
    AIRFLOW__CORE__FERNET_KEY='' \
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=True \
    AIRFLOW__CORE__LOAD_EXAMPLES=False

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/airflow

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install only the required Python packages for this project
# Note: Using requirements.txt but excluding packages not needed in Airflow container
RUN pip install --no-cache-dir \
    python-dotenv==1.0.0 \
    pandas==2.1.4 \
    numpy==1.26.2 \
    pyarrow==14.0.2 \
    boto3==1.34.10 \
    s3fs==2023.12.2 \
    "snowflake-connector-python>=3.7.1,<4.0.0" \
    snowflake-sqlalchemy==1.5.0 \
    cryptography==41.0.7 \
    dbt-core==1.7.7 \
    dbt-snowflake==1.7.1 \
    psycopg2-binary==2.9.9 \
    Flask-Session==0.5.0 \
    apache-airflow==2.8.1 \
    apache-airflow-providers-amazon==8.13.0 \
    apache-airflow-providers-snowflake==5.6.0 \
    apache-airflow-providers-postgres==5.8.0 \
    kaggle==1.5.16 \
    great-expectations==0.18.8 \
    requests==2.31.0 \
    pyyaml==6.0.1 \
    python-dateutil==2.8.2 \
    trio==0.23.2 \
    trio-typing==0.9.0 \
    asks==3.0.0 \
    beautifulsoup4==4.12.3 \
    lxml==5.3.0 \
    "protobuf>=4.21.0,<5.0.0" \
    "opentelemetry-proto<1.28.0" \
    graphviz==0.20.1

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
# Load environment variables from .env file if it exists\n\
if [ -f /opt/airflow/.env ]; then\n\
  set -a\n\
  source /opt/airflow/.env\n\
  set +a\n\
fi\n\
echo "Waiting for PostgreSQL to be ready..."\n\
until pg_isready -h postgres -U airflow; do\n\
  echo "PostgreSQL is unavailable - sleeping"\n\
  sleep 1\n\
done\n\
echo "PostgreSQL is ready!"\n\
echo "Initializing Airflow database..."\n\
airflow db init || true\n\
echo "Creating Airflow user..."\n\
airflow users create \\\n\
  --username airflow_company_atlas \\\n\
  --firstname Jiufeng \\\n\
  --lastname Li \\\n\
  --role Admin \\\n\
  --email lijiufeng97@gmail.com \\\n\
  --password CompanyAtlas123! || true\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

# Expose Airflow webserver port
EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (can be overridden in docker-compose)
CMD ["airflow", "webserver"]

