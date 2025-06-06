# APT. Scanner

An AI-driven platform that helps users find the best-matched neighborhoods and apartments based on personalized questionnaires. APT. Scanner integrates machine learning, real estate data, and dynamic recommendations to provide a comprehensive solution for property seekers in Tel Aviv.

## Project Overview

APT. Scanner combines questionnaire-driven preferences with real estate data to deliver personalized apartment and neighborhood recommendations. The platform processes user inputs through customized questionnaires, analyzes various data sources, and provides tailored recommendations with an intuitive swipe-based interface.

## Tech Stack

- **Frontend**: React.js with Vite, Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (with Alembic for migrations)
- **Data Processing**: Pandas, NumPy, Scikit-learn
- **APIs & Data Sources**:
  - Yad2 (apartment listings)
  - Madlan (neighborhood metrics)
  - Google Maps (location services)
  - Gemini AI (neighborhood overviews)
- **Authentication**: Firebase Admin SDK
- **Caching**: Redis
- **Additional Libraries**:
  - React Router DOM for navigation
  - Framer Motion for animations
  - React Leaflet for maps
  - Swiper for card interactions
  - Lucide React for icons

## Project Structure

```
APT.-Scanner/
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
│   │   ├── styles/         # CSS modules for styling
│   │   ├── App.jsx         # Main React application and routing
│   │   ├── main.jsx        # React application entry point
│   │   └── index.css       # Global styles
│   ├── package.json        # Frontend dependencies
│   ├── vite.config.js      # Vite configuration
│   └── tailwind.config.js  # Tailwind CSS configuration
├── APT-Scanner-Firebase.json  # Firebase service account credentials
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

## Key Features Implemented

### Backend
- **FastAPI Application**: RESTful API with automatic documentation
- **User Authentication**: Firebase Admin SDK integration for secure authentication
- **Dynamic Questionnaire System**: 
  - Question flow management with branching logic
  - Progress tracking and state management
  - Redis caching for user sessions
- **Database Integration**: PostgreSQL with SQLAlchemy ORM
- **Data Processing Scripts**: 
  - Apartment listings fetching from Yad2
  - Neighborhood data collection from Google Maps
  - AI-generated neighborhood overviews using Gemini
- **Comprehensive Logging**: Structured logging with file and console output

### Frontend
- **Modern React Application**: Built with Vite for fast development
- **Responsive Design**: Tailwind CSS for mobile-first responsive design
- **User Journey**: Complete flow from landing page to apartment recommendations
- **Interactive Features**:
  - Swipe-based apartment browsing
  - Favorites management
  - Advanced filtering options
  - Progress tracking during questionnaire
- **Authentication Flow**: Login and registration with Firebase
- **Map Integration**: Interactive maps using React Leaflet
- **Smooth Animations**: Framer Motion for enhanced user experience

### Data & AI
- **Questionnaire Data**: JSON-based question definitions with dynamic branching
- **Neighborhood Analytics**: Integration of quality-of-life metrics and local data
- **Recommendation Engine**: ML-based matching of user preferences to properties
- **Real Estate Data**: Automated fetching and processing of apartment listings

## Getting Started

### Prerequisites
- Node.js (18+)
- Python (3.12+)
- PostgreSQL (13+)
- Redis (for caching)
- Firebase project with Authentication enabled

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd APT.-Scanner
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   
   pip install -r ../requirements.txt
   
   # Configure environment variables
   # Create .env file with:
   # DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
   # REDIS_HOST=localhost
   # REDIS_PORT=6379
   # FIREBASE_CREDENTIALS_PATH=../APT-Scanner-Firebase.json
   
   # Run database migrations
   alembic upgrade head
   
   # Start the backend server
   uvicorn src.main:app --reload
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   
   # Configure environment variables
   # Create .env.local file with:
   # VITE_API_BASE_URL=http://localhost:8000
   # VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key
   
   npm run dev
   ```

4. **Firebase Setup:**
   - Place your Firebase service account JSON key file as `APT-Scanner-Firebase.json` in the root directory
   - Ensure Firebase Authentication is enabled with email/password sign-in

## Development

- **Backend API**: Available at `http://localhost:8000` with docs at `/docs`
- **Frontend Dev Server**: Available at `http://localhost:5173`
- **Database Migrations**: Use `alembic revision --autogenerate -m "description"` for new migrations

## API Endpoints

- `/health` - Health check endpoint
- `/api/v1/questionnaire/` - Questionnaire management endpoints
- `/api/v1/user/` - User management endpoints
- `/api/v1/filters/` - Property filtering endpoints

## Data Sources

The application integrates with multiple data sources:
- **Yad2**: Real estate listings
- **Madlan**: Neighborhood metrics and pricing data
- **Google Maps**: Location services and neighborhood information
- **Gemini AI**: AI-generated neighborhood descriptions and insights
