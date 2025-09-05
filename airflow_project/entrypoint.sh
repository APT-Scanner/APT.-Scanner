#!/bin/bash
set -e

# Custom entrypoint script for Yad2 Airflow ETL

echo "Starting Yad2 Airflow ETL Environment..."

# Set up Python path
export PYTHONPATH="${PYTHONPATH}:/opt/airflow:/opt/airflow/backend"

# Create necessary directories if they don't exist
mkdir -p /opt/airflow/logs
mkdir -p /opt/airflow/dags
mkdir -p /opt/airflow/plugins

# Set proper permissions
chmod -R 755 /opt/airflow/backend

# Log environment information
echo "Python Path: $PYTHONPATH"
echo "Current User: $(whoami)"
echo "Working Directory: $(pwd)"

# Check if required files exist
if [ ! -f "/opt/airflow/backend/data/scrapers/yad2_scraper.py" ]; then
    echo "Warning: yad2_scraper.py not found in expected location"
fi

if [ ! -f "/opt/airflow/populate_database.py" ]; then
    echo "Warning: populate_database.py not found in expected location"
fi

# Validate DAG files syntax (optional)
if [ "$1" = "webserver" ] || [ "$1" = "scheduler" ]; then
    echo "Validating DAG files..."
    if [ -d "/opt/airflow/dags" ]; then
        python -m py_compile /opt/airflow/dags/*.py 2>/dev/null || echo "Some DAG files may have syntax issues"
    fi
fi

# Execute the original command
exec "$@"


