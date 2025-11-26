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

# Install Python packages from requirements.txt
# This ensures a single source of truth and avoids duplication
RUN pip install --no-cache-dir -r /tmp/requirements.txt

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

