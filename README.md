# APT. Scanner

An AI-driven platform that helps users find the best-matched neighborhoods and apartments based on personalized questionnaires. APT. Scanner integrates machine learning, real estate data, and dynamic recommendations to provide a comprehensive solution for property seekers in Tel Aviv.

## Project Overview

APT. Scanner combines questionnaire-driven preferences with real estate data to deliver personalized apartment and neighborhood recommendations. The platform processes user inputs through customized questionnaires, analyzes various data sources, and provides tailored recommendations with an intuitive swipe-based interface.

## Tech Stack

### Frontend
- **Framework**: React.js 18+ with Vite
- **Styling**: Tailwind CSS, PostCSS, Autoprefixer
- **State Management**: React Hooks, Context API
- **Routing**: React Router DOM
- **UI Components & Interactions**:
  - Framer Motion (animations)
  - Swiper (card interactions)
  - React Leaflet (maps)
  - Lucide React (icons)
  - React Icons
  - RC Slider (range inputs)
  - @use-gesture/react (gesture handling)
- **Authentication**: Firebase SDK
- **Development**: ESLint, Vite plugins, Image optimization

### Backend
- **Framework**: FastAPI with Uvicorn
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async support)
- **Additional Storage**: MongoDB with Motor (async driver)
- **Migration Management**: Alembic
- **Authentication & Security**: 
  - Firebase Admin SDK
  - Python-JOSE with cryptography
  - Passlib with bcrypt
- **Caching**: Redis

### APIs & Data Sources
- **Yad2** (apartment listings)
- **Madlan** (neighborhood metrics)
- **Google Maps** (location services)
- **Gemini AI** (neighborhood overviews)


## Project Structure

```
APT.-Scanner/
├── ai/                     # AI/ML components and models
│   ├── models/            # Machine learning models
│   ├── preprocessing/     # Data preprocessing utilities
│   └── evaluation/        # Model evaluation and metrics
├── backend/
│   ├── src/
│   │   ├── api/            # API endpoint definitions (FastAPI routers)
│   │   │   ├── router.py   # Main API router
│   │   │   └── v1/         # API version 1 endpoints
│   │   ├── config/         # Configuration files and settings
│   │   ├── middleware/     # Custom FastAPI middleware
│   │   ├── models/         # Database models (SQLAlchemy) and Pydantic schemas
│   │   ├── services/       # Business logic services
│   │   │   ├── QuestionnaireService.py
│   │   │   ├── filters_service.py
│   │   │   └── user_service.py
│   │   ├── utils/          # Utility functions and helpers
│   │   └── main.py         # FastAPI application entry point
│   ├── data/               # Data-related files
│   │   ├── sources/        # Data files (questionnaires, neighborhood data)
│   │   ├── scrapers/       # Web scraping utilities
│   │   └── processing/     # Data processing utilities
│   ├── migrations/         # Alembic database migration scripts
│   ├── scripts/            # Standalone scripts for data fetching and processing
│   │   ├── apt_listings_fetcher.py
│   │   ├── populate_database.py
│   │   ├── get_hoods_data_google_maps.py
│   │   ├── get_hood_overview_gemini.py
│   │   └── govmap-api/     # GovMap API integration
│   ├── tests/              # Backend test suite
│   ├── logs/               # Application log files
│   ├── alembic.ini         # Alembic configuration
│   └── init_db.py          # Database initialization script
├── frontend/
│   ├── public/             # Static assets
│   ├── src/
│   │   ├── assets/         # Images, icons, and static assets
│   │   ├── components/     # Reusable React components
│   │   ├── config/         # Frontend configuration
│   │   ├── hooks/          # Custom React hooks
│   │   ├── pages/          # Page-level components
│   │   │   ├── LandingPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── GetStartedPage.jsx
│   │   │   ├── QuestionnairePage.jsx
│   │   │   ├── ApartmentSwipePage.jsx
│   │   │   ├── FavoritesPage.jsx
│   │   │   ├── FilterPage.jsx
│   │   │   ├── FavoritesApartmentDetails.jsx
│   │   │   └── RecommendationsPage.jsx
│   │   ├── services/       # API service layer
│   │   ├── styles/         # CSS modules for styling
│   │   ├── App.jsx         # Main React application and routing
│   │   ├── main.jsx        # React application entry point
│   │   └── index.css       # Global styles
│   ├── tests/              # Frontend test suite
│   ├── package.json        # Frontend dependencies
│   ├── vite.config.js      # Vite configuration
│   ├── eslint.config.js    # ESLint configuration
│   └── tailwind.config.js  # Tailwind CSS configuration
├── docs/                   # Project documentation
├── APT-Scanner-Firebase.json  # Firebase service account credentials
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

## Key Features Implemented

### Backend
- **FastAPI Application**: RESTful API with automatic documentation (OpenAPI/Swagger)
- **Dual Database Support**: PostgreSQL for relational data, MongoDB for flexible document storage
- **User Authentication**: Firebase Admin SDK integration for secure authentication
- **Dynamic Questionnaire System**: 
  - Question flow management with branching logic
  - Progress tracking and state management
  - Redis caching for user sessions
- **Data Processing Pipeline**: 
  - Apartment listings fetching from Yad2
  - Neighborhood data collection from Google Maps
  - AI-generated neighborhood overviews using Gemini
- **Comprehensive Logging**: Structured logging with file and console output

### Frontend
- **Modern React Application**: Built with Vite for fast development and optimized builds
- **Responsive Design**: Tailwind CSS for mobile-first responsive design
- **Enhanced UX**: 
  - Smooth animations with Framer Motion
  - Gesture support for swipe interactions
  - Interactive maps with React Leaflet
  - Custom sliders and form controls
- **Complete User Journey**: 
  - Landing page to apartment recommendations
  - Swipe-based apartment browsing
  - Favorites management
  - Advanced filtering options
  - Progress tracking during questionnaire
- **Authentication Flow**: Secure login and registration with Firebase
- **Performance**: Optimized builds with image compression and code splitting

### AI & Machine Learning
- **Recommendation Engine**: ML-based matching of user preferences to properties
- **Data Preprocessing**: Automated data cleaning and feature engineering
- **Model Evaluation**: Comprehensive metrics and validation frameworks
- **Predictive Analytics**: Neighborhood scoring and apartment ranking algorithms

### Data & Integration
- **Multi-Source Data Pipeline**: Integration with Yad2, Madlan, Google Maps, and Gemini AI
- **Quality Assurance**: Data validation and error handling throughout the pipeline
- **Caching Strategy**: Redis-based caching for improved performance

## Getting Started

### Prerequisites
- **Node.js** 18+ (for frontend development)
- **Python** 3.12+ (for backend development)
- **PostgreSQL** 13+ (primary database)
- **MongoDB** 6+ (document storage)
- **Redis** 6+ (caching and session management)
- **Firebase Project** with Authentication enabled

### Environment Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd APT.-Scanner
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   
   # Create and activate virtual environment
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   
   # Install dependencies
   pip install -r ../requirements.txt
   
   # Create .env file with required variables:
   cat > .env << EOF
   # Database Configuration
   DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/apt_scanner
   MONGO_URL=mongodb://localhost:27017/apt_scanner
   
   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=
   
   # Firebase Configuration
   FIREBASE_CREDENTIALS_PATH=../APT-Scanner-Firebase.json
   
   # API Keys
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   GEMINI_API_KEY=your_gemini_api_key
   
   # Application Settings
   SECRET_KEY=your_secret_key_here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # Environment
   ENVIRONMENT=development
   DEBUG=true
   EOF
   
   # Initialize database
   python init_db.py
   
   # Run migrations
   alembic upgrade head
   
   # Start the backend server
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   
   # Install dependencies
   npm install
   
   # Create .env.local file:
   cat > .env.local << EOF
   VITE_API_BASE_URL=http://localhost:8000
   VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   VITE_FIREBASE_CONFIG='{"apiKey":"...","authDomain":"...","projectId":"..."}'
   EOF
   
   # Start development server
   npm run dev
   ```

4. **Firebase Setup:**
   - Create a Firebase project with Authentication enabled
   - Enable Email/Password sign-in method
   - Download service account key and save as `APT-Scanner-Firebase.json` in the root directory
   - Configure web app and add config to frontend environment

## Development

### Running the Application
- **Backend API**: `http://localhost:8000` (docs at `/docs`)
- **Frontend**: `http://localhost:5173`
- **API Documentation**: `http://localhost:8000/redoc` (alternative docs)

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing
```bash
# Backend tests
cd backend
pytest tests/ -v --cov=src --cov-report=html

# Frontend tests
cd frontend
npm test
```

### Code Quality
```bash
# Backend code formatting and linting
cd backend
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/

# Frontend linting
cd frontend
npm run lint
```

## API Endpoints

### Core Endpoints
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

### API v1 Endpoints
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/questionnaire/` - Questionnaire management
- `POST /api/v1/questionnaire/submit` - Submit questionnaire responses
- `GET /api/v1/user/profile` - User profile management
- `GET /api/v1/apartments/recommendations` - Get personalized recommendations
- `POST /api/v1/apartments/filters` - Apply apartment filters
- `GET /api/v1/neighborhoods/` - Neighborhood information

## Data Sources & Integrations

### Real Estate Data
- **Yad2**: Primary source for apartment listings and market data
- **Madlan**: Neighborhood metrics, pricing trends, and market analysis

### Location & Mapping
- **Google Maps API**: Geocoding, neighborhood boundaries, and location services
- **Google Places**: Points of interest, amenities, and local business data

### AI & Content Generation
- **Gemini AI**: Automated neighborhood descriptions and insights
- **Custom ML Models**: Property matching and recommendation algorithms

## Monitoring & Performance

### Metrics Collection
- **Prometheus**: Application metrics and performance monitoring
- **Structured Logging**: JSON-formatted logs for analysis
- **Health Checks**: Automated service health monitoring

### Performance Optimization
- **Async Operations**: Non-blocking database and API calls
- **Caching Strategy**: Redis for session management and data caching
- **Database Optimization**: Indexed queries and connection pooling
- **Frontend Optimization**: Code splitting, image compression, and lazy loading

## Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code style guidelines
4. Add tests for new functionality
5. Run the test suite and ensure all tests pass
6. Update documentation as needed
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Style Guidelines
- **Backend**: Follow PEP 8, use Black for formatting, type hints required
- **Frontend**: Use ESLint configuration, consistent component structure
- **Testing**: Minimum 80% code coverage for new features
- **Documentation**: Update README and inline documentation for significant changes

## License

This project is proprietary software. All rights reserved.

## Support

For questions, issues, or contributions, please contact the development team or create an issue in the repository.
