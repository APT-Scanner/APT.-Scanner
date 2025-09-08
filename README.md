# APT. Scanner

You open the listings, see a hundred options... and still have no idea where to begin.
Searching for an apartment can feel overwhelming.
We’re here to change that!

APT. Scanner is An AI-driven platform that helps users find the best-matched neighborhoods and apartments based on personalized questionnaires. APT. Scanner integrates machine learning, real estate data, and dynamic recommendations to provide a comprehensive solution for property seekers in Tel Aviv.

**🌐 Live Application**: [https://aptscanner.vercel.app/](https://aptscanner.vercel.app/)

## Project Overview

APT. Scanner combines questionnaire-driven preferences with real estate data to deliver personalized apartment and neighborhood recommendations. The platform processes user inputs through customized questionnaires, analyzes various data sources, and provides tailored recommendations with an intuitive swipe-based interface.

## Architecture

The system consists of four main components:

1. **Frontend** - React.js web application
2. **Backend API** - FastAPI REST API with dual database support
3. **Data Pipeline** - Apache Airflow ETL processes for real estate data
4. **Databases** - PostgreSQL (primary) + MongoDB (documents) + Redis (caching)

## Tech Stack

### Frontend
- **Framework**: React 18+ with Vite 6.0
- **Language**: JavaScript (ES2022)
- **Styling**: Tailwind CSS 3.4
- **State Management**: React Hooks, Context API
- **Routing**: React Router DOM 6.28
- **UI Components & Interactions**:
  - Framer Motion 12.10 (animations)
  - Swiper 11.1 (card interactions)  
  - React Leaflet 4.2 (maps)
  - Lucide React 0.488 (icons)
  - RC Slider 11.1 (range inputs)
  - @use-gesture/react 10.3 (gesture handling)
- **Authentication**: Firebase SDK 11.0
- **Development**: ESLint, Autoprefixer, PostCSS

### Backend API
- **Framework**: FastAPI 0.103 with Uvicorn 0.23
- **Language**: Python 3.12+
- **Database ORM**: SQLAlchemy 2.0 (async support)
- **Migration Management**: Alembic 1.12
- **Authentication & Security**: 
  - Firebase Admin SDK 6.2
  - Python-JOSE with cryptography
  - Passlib with bcrypt
- **Additional Storage**: MongoDB with Motor 3.3 (async driver)
- **Caching**: Redis 5.0
- **Data Processing**: Pandas 2.0, NumPy 1.24, scikit-learn 1.3
- **HTTP Clients**: HTTPX 0.27, aiohttp 3.8, requests 2.31
- **Web Scraping**: Beautiful Soup 4.12, Selenium 4.12

### Data Pipeline (Airflow)
- **Framework**: Apache Airflow 3.0.3 (2025 latest)
- **Orchestration**: Docker Compose with PostgreSQL 15 + Redis 7
- **Executor**: LocalExecutor with custom Docker image
- **Scheduling**: Daily ETL processes for real estate data
- **Source Integration**: Yad2, Madlan, Google Maps, ScrapeOwl API

### APIs & Data Sources
- **Yad2**: Primary source for apartment listings
- **Madlan**: Neighborhood metrics and market analysis  
- **Google Maps API**: Geocoding, places, and location services
- **Google Places**: Points of interest and amenities
- **Gemini AI**: Automated neighborhood descriptions

## Project Structure

```
APT.-Scanner/
├── frontend/                   # React web application
│   ├── src/
│   │   ├── components/        # Reusable React components
│   │   ├── pages/             # Page-level components (13 pages)
│   │   ├── hooks/             # Custom React hooks (10 hooks)
│   │   ├── services/          # API service layer
│   │   ├── config/            # Configuration (API base, Firebase, constants)
│   │   ├── styles/            # CSS modules (15 stylesheets)
│   │   └── assets/            # Static assets (images, icons)
│   ├── package.json           # Dependencies & scripts
│   ├── vite.config.js         # Vite configuration
│   └── tailwind.config.js     # Tailwind configuration
├── backend/                    # FastAPI application
│   ├── src/
│   │   ├── main.py            # Application entry point
│   │   ├── api/               # API routers and endpoints
│   │   │   ├── router.py      # Main API router
│   │   │   └── v1/endpoints/  # API v1 endpoints (7 modules)
│   │   ├── config/            # Settings and constants
│   │   ├── database/          # Database models, schemas, connections
│   │   ├── middleware/        # Authentication middleware
│   │   ├── services/          # Business logic services (4 services)
│   │   └── utils/             # Utility functions and cache
│   └── data/                  # Data processing and scraping
│       ├── scrapers/          # Web scrapers (Yad2, Madlan)
│       ├── processing/        # Data processing utilities
│       └── sources/           # Static data files
├── airflow_project/           # Apache Airflow ETL pipeline
│   ├── dags/                  # Airflow DAGs
│   ├── docker-compose.yaml    # Airflow containerized environment
│   ├── start-airflow.sh       # Startup script
│   ├── manage-airflow.sh      # Management utilities
│   └── README.md              # Airflow-specific documentation
├── migrations/                # Database migration files (Alembic)
├── requirements.txt           # Python dependencies
├── alembic.ini               # Database migration configuration
├── app.zip                   # Elastic Beanstalk deployment package
└── README.md                 # This file
```

## API Endpoints

The backend API serves all endpoints under `/api/v1/`:

### Core Application
- `GET /` - Health check endpoint (Elastic Beanstalk compatible)
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

### API v1 Endpoints

**User Management**
- `GET /api/v1/users/me` - Get current user profile
- `POST /api/v1/users/me` - Create/update user profile

**Listings & Properties**
- `GET /api/v1/listings/` - Get apartment listings with filters
- `GET /api/v1/listings/{id}` - Get specific apartment details
- `POST /api/v1/listings/views` - Record apartment view
- `GET /api/v1/listings/views` - Get user's view history
- `DELETE /api/v1/listings/views` - Clear view history

**User Preferences & Filters**
- `GET /api/v1/filters/` - Get user's current filters
- `PUT /api/v1/filters/` - Update user filters
- `GET /api/v1/filters/cities` - Get available cities
- `GET /api/v1/filters/neighborhoods` - Get neighborhoods by city

**Questionnaire System**
- `GET /api/v1/questionnaire/current` - Get current question
- `POST /api/v1/questionnaire/answers` - Submit question answers
- `GET /api/v1/questionnaire/status` - Check completion status
- `GET /api/v1/questionnaire/responses` - Get all user responses
- `POST /api/v1/questionnaire/current/previous` - Navigate to previous question
- `GET /api/v1/questionnaire/basic-questions-count` - Get question count
- `PUT /api/v1/questionnaire/` - Submit complete questionnaire

**Favorites Management**
- `GET /api/v1/favorites/` - Get user's favorite listings
- `POST /api/v1/favorites/{listing_id}` - Add listing to favorites
- `DELETE /api/v1/favorites/{listing_id}` - Remove from favorites

**Neighborhood Recommendations**
- `GET /api/v1/recommendations/neighborhoods` - Get personalized recommendations
- `POST /api/v1/recommendations/refresh` - Refresh recommendation cache
- `POST /api/v1/recommendations/neighborhoods/{id}/select` - Select neighborhood

**Maps & Location Services**
- `GET /api/v1/maps/places/autocomplete` - Google Places autocomplete
- `GET /api/v1/maps/places/details` - Get place details by ID
- `POST /api/v1/maps/distance-matrix` - Calculate travel times/distances

## Key Features

### Backend Features
- **FastAPI Application**: High-performance async API with automatic documentation
- **Dual Database Architecture**: PostgreSQL for relational data, MongoDB for flexible documents
- **Firebase Authentication**: Secure user authentication with Firebase Admin SDK
- **Dynamic Questionnaire System**: 
  - Adaptive question flow with branching logic
  - Real-time progress tracking
  - Redis-based session caching
- **Recommendation Engine**: ML-based neighborhood matching algorithm
- **Real Estate Data Pipeline**: Automated data collection and processing
- **Comprehensive Logging**: Structured logging for monitoring and debugging
- **Production Ready**: Elastic Beanstalk deployment configuration

### Frontend Features
- **Modern React Architecture**: Built with Vite for optimal performance
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Rich User Experience**: 
  - Smooth animations with Framer Motion
  - Touch/swipe gesture support
  - Interactive maps integration
  - Custom form controls and sliders
- **Complete User Journey**: 
  - Landing → Registration → Questionnaire → Recommendations → Apartment Browsing
  - Favorites management and advanced filtering
  - User preference editing and questionnaire review
- **Performance Optimized**: Code splitting, lazy loading, and build optimization

### Data Pipeline Features
- **Apache Airflow ETL**: Containerized data processing pipeline
- **Multi-Source Integration**: Automated data collection from Yad2, Madlan, and Google Maps
- **Scalable Architecture**: Docker-based with monitoring and management utilities
- **Error Handling**: Robust error recovery and logging
- **Scheduling**: Daily automated runs with manual trigger support

## Getting Started

### Prerequisites
- **Node.js** 18+ (for frontend development)
- **Python** 3.12+ (for backend development)  
- **PostgreSQL** 13+ (primary database)
- **MongoDB** 6+ (document storage)
- **Redis** 6+ (caching)
- **Docker** & **Docker Compose** (for Airflow pipeline)
- **Firebase Project** with Authentication enabled

### Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd APT.-Scanner
   ```

2. **Backend Setup:**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Configure environment variables
   cp backend/.env.example backend/.env
   # Edit .env file with your database and API credentials
   
   # Run database migrations
   alembic upgrade head
   
   # Start backend server
   cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   
   # Install dependencies  
   npm install
   
   # Configure API endpoint (already set to production)
   # API_BASE = "https://aptscanner.duckdns.org" in src/config/api.js
   
   # Start development server
   npm run dev
   ```

4. **Data Pipeline Setup (Optional):**
   ```bash
   cd airflow_project
   
   # Configure environment
   cp env.example .env
   # Edit .env with your ScrapeOwl API key and credentials
   
   # Start Airflow environment
   ./start-airflow.sh
   
   # Access Airflow UI at http://localhost:8080
   ```

### Environment Configuration

**Backend (.env)**
```bash
# Database URLs
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/apt_scanner
MONGO_URL=mongodb://localhost:27017/apt_scanner

# Redis Configuration  
REDIS_HOST=localhost
REDIS_PORT=6379

# Firebase Configuration
FIREBASE_CREDENTIALS=<base64_encoded_service_account_json>

# API Keys
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
GEMINI_API_KEY=your_gemini_api_key

# Security
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=["http://localhost:5173", "https://aptscanner.duckdns.org"]
```

**Frontend (automatic)**
- API base URL is configured to production: `https://aptscanner.duckdns.org`
- Firebase config should be added to `src/config/firebase.js`

## Development

### Local Development URLs
- **Frontend**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Airflow UI**: `http://localhost:8080` (if running)

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration  
alembic downgrade -1
```

### Code Quality & Testing
```bash
# Backend formatting
black backend/src/
isort backend/src/

# Frontend linting
cd frontend && npm run lint

# Build for production
cd frontend && npm run build
```

## Deployment

### Production Deployment (Elastic Beanstalk)

The application is deployed on AWS Elastic Beanstalk:

1. **Create deployment package:**
   ```bash
   zip -r app.zip backend/ requirements.txt alembic.ini migrations/ -x "**/__pycache__/*" "**/*.pyc" "*/.*"
   ```

2. **Deploy to Elastic Beanstalk:**
   - Upload `app.zip` to your Elastic Beanstalk environment
   - Configure environment variables in EB console
   - The application will be available at your EB environment URL

3. **Frontend Deployment:**
   - Build: `cd frontend && npm run build`
   - Deploy `dist/` folder to your web hosting service
   - Configure to point to your API backend

### Production URLs
- **Frontend**: [https://aptscanner.duckdns.org](https://aptscanner.duckdns.org)
- **API Backend**: Configured in frontend as API_BASE

## Data Pipeline Management

The Airflow data pipeline runs independently and provides ETL capabilities:

### Airflow Management
```bash
cd airflow_project

# Start services
./manage-airflow.sh start

# View logs
./manage-airflow.sh logs

# Test DAG
./manage-airflow.sh test-dag yad2_listings_etl

# Scale workers
./manage-airflow.sh scale 3

# Reset environment
./manage-airflow.sh reset
```

### Data Sources
- **Yad2**: Real estate listings scraping
- **Madlan**: Neighborhood analytics and metrics
- **Google Maps**: Location data and geocoding
- **ScrapeOwl**: Proxy service for web scraping

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following code style guidelines
4. Test thoroughly (both frontend and backend)
5. Update documentation as needed
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Style Guidelines
- **Backend**: Follow PEP 8, use Black for formatting, type hints required
- **Frontend**: Use ESLint configuration, consistent component structure
- **Documentation**: Update README for significant changes

## Monitoring & Performance

### Application Health
- Health check endpoint: `GET /` (returns `{"status": "ok", "message": "APT. Scanner API is healthy"}`)
- API documentation: `/docs` and `/redoc`
- Structured logging with FastAPI

### Caching Strategy
- Redis for user sessions and questionnaire state
- API response caching for static data
- Database query optimization with indexes

### Error Handling
- Global exception handlers for API errors
- Comprehensive logging throughout the application
- Graceful degradation for external service failures

## License

This project is proprietary software. All rights reserved.

## Support

For questions, issues, or contributions, please contact the development team or create an issue in the repository.
