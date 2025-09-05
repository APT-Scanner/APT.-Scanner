# Use the official Apache Airflow image as base
# Using stable version 2.10.4 for better compatibility
FROM apache/airflow:2.10.4

# Switch to root user to install system packages
USER root

# Install system dependencies required for your project
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user
USER airflow

# 1. Copy requirements file FIRST to leverage Docker layer caching.
# If requirements.txt doesn't change, this layer will be cached.
COPY --chown=airflow:root requirements.txt /tmp/requirements.txt

# 2. Install Python dependencies in a separate layer.
# This step will only re-run if requirements.txt changes.
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 3. Backend code is mounted as volume in docker-compose.yaml
# No need to copy files during build - they're mounted at runtime
# Set Python path to include backend directory (mounted via volume)
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow"

# The HEALTHCHECK is better defined in the docker-compose.yaml, so it's removed from here.
# The CMD is also defined in docker-compose.yaml, so this is just a fallback.
CMD ["airflow", "webserver"]