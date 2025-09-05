#!/bin/bash

# Yad2 Listings ETL - Airflow Management Script
# This script provides common management commands for the Airflow environment

set -e

# Set the Docker Compose command (handle both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

# Function to display usage
usage() {
    echo "Yad2 Listings ETL - Airflow Management Script"
    echo "=============================================="
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start         Start all Airflow services"
    echo "  stop          Stop all Airflow services"
    echo "  restart       Restart all Airflow services"
    echo "  status        Show status of all services"
    echo "  logs [service] Show logs for all services or specific service"
    echo "  shell         Open bash shell in Airflow container"
    echo "  reset         Reset the entire environment (⚠️ DESTRUCTIVE)"
    echo "  update        Pull latest images and restart"
    echo "  scale [n]     Scale workers to n instances"
    echo "  dags          List all DAGs"
    echo "  test-dag [dag_id] Test a specific DAG"
    echo "  clean         Clean up unused Docker resources"
    echo "  backup        Backup database and logs"
    echo "  restore [file] Restore from backup"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs airflow-scheduler   # Show scheduler logs"
    echo "  $0 scale 3                  # Scale to 3 workers"
    echo "  $0 test-dag yad2_listings_etl # Test the Yad2 ETL DAG"
    echo ""
}

# Function to check if services are running
check_services() {
    $DOCKER_COMPOSE_CMD ps
}

# Function to start services
start_services() {
    echo "🚀 Starting Airflow services..."
    $DOCKER_COMPOSE_CMD up -d
    echo "✅ Services started! Access Airflow at: http://localhost:8080"
}

# Function to stop services
stop_services() {
    echo "🛑 Stopping Airflow services..."
    $DOCKER_COMPOSE_CMD down
    echo "✅ Services stopped!"
}

# Function to restart services
restart_services() {
    echo "🔄 Restarting Airflow services..."
    $DOCKER_COMPOSE_CMD restart
    echo "✅ Services restarted!"
}

# Function to show logs
show_logs() {
    if [ -z "$1" ]; then
        $DOCKER_COMPOSE_CMD logs -f
    else
        $DOCKER_COMPOSE_CMD logs -f "$1"
    fi
}

# Function to open shell
open_shell() {
    echo "🔧 Opening bash shell in Airflow container..."
    $DOCKER_COMPOSE_CMD exec airflow-webserver bash
}

# Function to reset environment
reset_environment() {
    echo "⚠️  WARNING: This will destroy all data and containers!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Resetting environment..."
        $DOCKER_COMPOSE_CMD down -v --remove-orphans
        docker system prune -f
        rm -rf logs/*
        echo "✅ Environment reset complete! Run 'start' to reinitialize."
    else
        echo "❌ Reset cancelled."
    fi
}

# Function to update images
update_environment() {
    echo "🔄 Updating Docker images..."
    $DOCKER_COMPOSE_CMD pull
    $DOCKER_COMPOSE_CMD build --no-cache
    restart_services
    echo "✅ Update complete!"
}

# Function to scale workers
scale_workers() {
    if [ -z "$1" ]; then
        echo "❌ Please specify number of workers to scale to"
        exit 1
    fi
    echo "📈 Scaling workers to $1 instances..."
    $DOCKER_COMPOSE_CMD up -d --scale airflow-worker="$1"
    echo "✅ Workers scaled to $1 instances!"
}

# Function to list DAGs
list_dags() {
    echo "📋 Listing all DAGs..."
    $DOCKER_COMPOSE_CMD exec airflow-webserver airflow dags list
}

# Function to test DAG
test_dag() {
    if [ -z "$1" ]; then
        echo "❌ Please specify DAG ID to test"
        exit 1
    fi
    echo "🧪 Testing DAG: $1"
    $DOCKER_COMPOSE_CMD exec airflow-webserver airflow dags test "$1"
}

# Function to clean Docker resources
clean_resources() {
    echo "🧹 Cleaning up unused Docker resources..."
    docker system prune -f
    docker volume prune -f
    echo "✅ Cleanup complete!"
}

# Function to backup
backup_data() {
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    echo "💾 Creating backup in $BACKUP_DIR..."
    
    # Backup database
    $DOCKER_COMPOSE_CMD exec postgres pg_dump -U airflow airflow > "$BACKUP_DIR/database.sql"
    
    # Backup logs
    cp -r logs "$BACKUP_DIR/"
    
    # Backup DAGs
    cp -r dags "$BACKUP_DIR/"
    
    echo "✅ Backup created in $BACKUP_DIR"
}

# Function to restore from backup
restore_data() {
    if [ -z "$1" ]; then
        echo "❌ Please specify backup directory to restore from"
        exit 1
    fi
    
    if [ ! -d "$1" ]; then
        echo "❌ Backup directory $1 does not exist"
        exit 1
    fi
    
    echo "⚠️  WARNING: This will overwrite current data!"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Restoring from $1..."
        
        # Restore database
        if [ -f "$1/database.sql" ]; then
            $DOCKER_COMPOSE_CMD exec -T postgres psql -U airflow airflow < "$1/database.sql"
        fi
        
        # Restore logs
        if [ -d "$1/logs" ]; then
            rm -rf logs/*
            cp -r "$1/logs"/* logs/
        fi
        
        # Restore DAGs
        if [ -d "$1/dags" ]; then
            cp -r "$1/dags"/* dags/
        fi
        
        echo "✅ Restore complete!"
    else
        echo "❌ Restore cancelled."
    fi
}

# Main script logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_services
        ;;
    logs)
        show_logs "$2"
        ;;
    shell)
        open_shell
        ;;
    reset)
        reset_environment
        ;;
    update)
        update_environment
        ;;
    scale)
        scale_workers "$2"
        ;;
    dags)
        list_dags
        ;;
    test-dag)
        test_dag "$2"
        ;;
    clean)
        clean_resources
        ;;
    backup)
        backup_data
        ;;
    restore)
        restore_data "$2"
        ;;
    *)
        usage
        exit 1
        ;;
esac


