#!/bin/bash

# Yad2 Listings ETL - Airflow Startup Script
# This script initializes and starts the Apache Airflow environment

set -e

echo "🚀 Starting Yad2 Listings ETL - Apache Airflow Environment"
echo "============================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed."
    exit 1
fi

# Set the Docker Compose command (handle both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit the .env file with your actual configuration values:"
    echo "   - SCRAPEOWL_API_KEY"
    echo "   - Database passwords"
    echo "   - Admin credentials"
fi

# Check system resources
echo "🔍 Checking system resources..."
# Check available memory (Linux vs macOS)
if command -v free >/dev/null 2>&1; then
    # Linux system
    AVAILABLE_MEMORY=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}' 2>/dev/null || echo "Unknown")
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS system
    TOTAL_MEMORY=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    if [ "$TOTAL_MEMORY" != "0" ]; then
        AVAILABLE_MEMORY=$((TOTAL_MEMORY / 1024 / 1024 / 1024))
    else
        AVAILABLE_MEMORY="Unknown"
    fi
else
    AVAILABLE_MEMORY="Unknown"
fi

if [ "$AVAILABLE_MEMORY" != "Unknown" ] && [ "$AVAILABLE_MEMORY" -lt 4 ]; then
    echo "⚠️  Warning: Less than 4GB RAM available ($AVAILABLE_MEMORY GB). Airflow may run slowly."
elif [ "$AVAILABLE_MEMORY" != "Unknown" ]; then
    echo "✅ System Memory: ${AVAILABLE_MEMORY}GB"
fi

# Create necessary directories with proper permissions
echo "📁 Setting up directories and permissions..."
mkdir -p logs plugins dags config backend
chmod 755 logs plugins dags config backend

# Set AIRFLOW_UID in .env if not already set (for Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ! grep -q "AIRFLOW_UID=" .env; then
        echo "AIRFLOW_UID=$(id -u)" >> .env
    fi
fi

# Initialize Airflow database
echo "🔧 Initializing Airflow database..."
$DOCKER_COMPOSE_CMD up airflow-init

if [ $? -eq 0 ]; then
    echo "✅ Database initialization completed successfully!"
else
    echo "❌ Database initialization failed!"
    exit 1
fi

# Start all Airflow services
echo "🎯 Starting Airflow services..."
$DOCKER_COMPOSE_CMD up -d

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Airflow is starting up! This may take a few minutes..."
    echo ""
    echo "📊 Access points:"
    echo "   • Airflow Web UI: http://localhost:8080"
    echo "   • Username: admin"
    echo "   • Password: admin"
    echo ""
    echo "🔧 Useful commands:"
    echo "   • View logs: $DOCKER_COMPOSE_CMD logs -f [service]"
    echo "   • Stop services: $DOCKER_COMPOSE_CMD down"
    echo "   • Restart: $DOCKER_COMPOSE_CMD restart"
    echo "   • Scale workers: $DOCKER_COMPOSE_CMD up -d --scale airflow-worker=3"
    echo ""
    echo "⏳ Wait 2-3 minutes for all services to be ready, then visit http://localhost:8080"
else
    echo "❌ Failed to start Airflow services!"
    exit 1
fi
