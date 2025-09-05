# Yad2 Listings ETL - Apache Airflow Environment

A containerized Apache Airflow environment for running the Yad2 real estate listings ETL pipeline using the latest 2025 best practices.

## 🏗️ Architecture

This setup includes:
- **Apache Airflow 3.0.3** (Latest 2025 version)
- **PostgreSQL 15** for metadata storage
- **Redis 7** for task queuing
- **LocalExecutor** for task execution
- **Custom Docker image** with project dependencies

## 📋 Prerequisites

- **Docker Engine** 19.03.0 or newer
- **Docker Compose** 2.14.0 or newer
- **4GB+ RAM** allocated to Docker
- **2+ CPU cores** recommended

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy and configure environment variables
cp env.example .env

# Edit the .env file with your actual values:
# - SCRAPEOWL_API_KEY: Your ScrapeOwl API key
# - Database passwords
# - Admin credentials
nano .env
```

### 2. Start Airflow

```bash
# Start the entire Airflow environment
./start-airflow.sh
```

This script will:
- Initialize the Airflow database
- Create admin user
- Start all services
- Check system resources

### 3. Access Airflow

- **Web UI**: http://localhost:8080
- **Username**: `admin`
- **Password**: `admin` (change in production!)

## 🛠️ Management Commands

Use the management script for common operations:

```bash
# Show all available commands
./manage-airflow.sh

# Start services
./manage-airflow.sh start

# Stop services
./manage-airflow.sh stop

# View logs
./manage-airflow.sh logs
./manage-airflow.sh logs airflow-scheduler

# Open shell in container
./manage-airflow.sh shell

# Scale workers
./manage-airflow.sh scale 3

# Test your DAG
./manage-airflow.sh test-dag yad2_listings_etl

# Clean up resources
./manage-airflow.sh clean

# Backup data
./manage-airflow.sh backup

# Reset everything (⚠️ DESTRUCTIVE)
./manage-airflow.sh reset
```

## 📁 Project Structure

```
airflow_project/
├── dags/                      # Airflow DAGs
│   └── yad2_listings_dag.py   # Main ETL DAG
├── backend/                   # Backend code
│   ├── data/
│   │   ├── processing/
│   │   ├── scrapers/
│   │   └── sources/
│   └── src/
├── logs/                      # Airflow logs
├── plugins/                   # Custom Airflow plugins
├── config/                    # Configuration files
├── docker-compose.yaml        # Docker Compose configuration
├── Dockerfile                 # Custom Airflow image
├── requirements.txt           # Python dependencies
├── start-airflow.sh          # Startup script
├── manage-airflow.sh         # Management script
└── .env                      # Environment variables
```

## 🔧 Configuration

### Environment Variables (.env)

Key variables to configure:

```bash
# Airflow User (Linux only)
AIRFLOW_UID=50000

# API Keys
SCRAPEOWL_API_KEY=your-api-key

# Database
POSTGRES_PASSWORD=airflow

# Admin User
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=admin

# Security (Generate new keys for production!)
AIRFLOW_FERNET_KEY=your-fernet-key
AIRFLOW_WEBSERVER_SECRET_KEY=your-secret-key
```

### Custom Airflow Configuration

Edit `config/airflow.cfg` for advanced settings:
- DAG processing intervals
- Task parallelism
- Timezone settings
- Email notifications

## 📊 DAG Details

### Yad2 Listings ETL DAG

- **DAG ID**: `yad2_listings_etl`
- **Schedule**: Daily (`@daily`)
- **Tasks**: Dynamic parallel processing per neighborhood
- **Features**:
  - Neighborhood-based task generation
  - Independent error handling per area
  - Rate limiting (3 seconds between requests)
  - Comprehensive logging and monitoring

### Task Flow

1. **get_neighborhood_ids**: Read neighborhood mapping
2. **fetch_and_process_single_hood_X**: Parallel ETL per neighborhood
   - Extract: Scrape listings from Yad2
   - Transform: Parse and enrich data
   - Load: Save to database
3. **generate_summary_report**: Aggregate results

## 🔒 Production Considerations

### Security
- Change default passwords and secrets
- Use environment-specific API keys
- Configure proper network security
- Enable SSL/TLS for web interface

### Scaling
- Increase worker instances: `./manage-airflow.sh scale 5`
- Monitor resource usage
- Configure auto-scaling based on load

### Monitoring
- Set up log aggregation
- Configure email alerts
- Monitor database performance
- Track DAG success/failure rates

### Backup Strategy
- Regular database backups: `./manage-airflow.sh backup`
- Version control DAG files
- Monitor disk usage for logs

## 🐛 Troubleshooting

### Common Issues

1. **Permission Errors** (Linux)
   ```bash
   # Set correct AIRFLOW_UID in .env
   echo "AIRFLOW_UID=$(id -u)" >> .env
   ./manage-airflow.sh restart
   ```

2. **Memory Issues**
   - Increase Docker memory allocation to 4GB+
   - Monitor with `docker stats`

3. **Database Connection Errors**
   - Check PostgreSQL service: `./manage-airflow.sh status`
   - Verify database credentials in .env

4. **DAG Import Errors**
   - Check DAG syntax: `./manage-airflow.sh shell`
   - View logs: `./manage-airflow.sh logs airflow-scheduler`

### Debugging

```bash
# View all service statuses
./manage-airflow.sh status

# Check specific service logs
./manage-airflow.sh logs airflow-webserver
./manage-airflow.sh logs airflow-scheduler
./manage-airflow.sh logs postgres

# Open interactive shell
./manage-airflow.sh shell
```

## 📚 Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [TaskFlow API Guide](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

This project follows the same license as Apache Airflow (Apache License 2.0).


