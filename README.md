# APT. Scanner

An AI-driven platform that helps users find the best-matched neighborhoods based on personalized questionnaires. APT. Scanner integrates machine learning, web scraping, and dynamic property recommendations to provide a comprehensive solution for property seekers.

## Project Overview

APT. Scanner combines advanced AI algorithms with real estate data to deliver personalized neighborhood recommendations based on user preferences and needs. The platform processes user inputs through customized questionnaires, analyzes various data sources, and provides tailored recommendations for ideal living locations.

## Tech Stack

- **Frontend**: React.js, Vite
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (with Alembic for migrations)
- **AI/ML**: (Potentially Scikit-learn, TensorFlow/PyTorch)
- **APIs & Data Sources**:
  - GovMap API
  - Yad2
  - Google Maps
- **Authentication**: Firebase
- **Caching**: Redis (used in backend services)
- **Hosting & Deployment**: (To be determined - e.g., AWS, Google Cloud)
- **Real-time interactions**: (Potentially WebSockets - to be confirmed)

## Project Structure

The project follows a monorepo architecture with the following main directories:

```
APT.-Scanner/
├── backend/
│   ├── src/
│   │   ├── api/            # API endpoint definitions (FastAPI routers)
│   │   ├── config/         # Configuration files (e.g., settings, constants)
│   │   ├── middleware/     # Custom FastAPI middleware (e.g., authentication)
│   │   ├── models/         # Database models (SQLAlchemy) and Pydantic schemas
│   │   ├── services/       # Business logic and core services (e.g., QuestionnaireService)
│   │   ├── utils/          # Utility functions and helpers (e.g., cache clients)
│   │   └── main.py         # Entry point for the backend FastAPI application
│   ├── data/               # Data-related files (e.g., JSON for questionnaires)
│   │   ├── sources/        # Raw data files (e.g., basic_information_questions.json)
│   ├── migrations/         # Alembic database migration scripts
│   ├── scripts/            # Standalone scripts (e.g., govmap-api interaction)
│   ├── tests/              # Unit and integration tests for the backend
│   └── logs/               # Log files
├── frontend/
│   ├── public/             # Static assets (e.g., images, icons, index.html)
│   ├── src/
│   │   ├── assets/         # Static assets like images, icons
│   │   ├── components/     # Reusable React components (e.g., LoadingSpinner, ContinuationPrompt)
│   │   ├── config/         # Frontend configuration (e.g., constants, API URLs)
│   │   ├── hooks/          # Custom React hooks (e.g., useAuth, useQuestionnaire)
│   │   ├── pages/          # Page-level components (e.g., QuestionnairePage, LoginPage)
│   │   ├── services/       # (Likely for API calls, though useQuestionnaire handles some)
│   │   ├── styles/         # Global and component-specific styles (CSS Modules)
│   │   ├── App.jsx         # Main React application component, routing setup
│   │   └── main.jsx        # Entry point for the React application
│   ├── tests/              # (Placeholder for frontend tests)
├── shared/                 # (Currently seems unused or content integrated elsewhere)
│   ├── constants/
│   └── utils/
├── docs/                   # Documentation files
├── ai/                     # AI/ML-related files (structure to be detailed if used)
│   ├── evaluation/
│   ├── models/
│   └── preprocessing/
├── logs/                   # General project log files
├── .venv/                  # Python virtual environment
├── .gitignore
├── APT-Scanner-Firebase.json # Firebase service account key
└── requirements.txt        # Python dependencies
```

## Key Features Implemented

- **User Authentication**: Firebase integration for user sign-up, login, and session management.
- **Dynamic Questionnaire**:
    - Backend service (`QuestionnaireService`) to manage question flow, user state, and answers.
    - Questions loaded from JSON files (`basic_information_questions.json`, `dynamic_questionnaire.json`).
    - Question branching logic based on user answers.
    - Batching of questions (initial 10, then in sets of 5).
    - Continuation prompts between batches and a final completion prompt.
    - Progress tracking and display.
- **Google Places Autocomplete**: Integrated into text input fields for location-based questions.
- **Caching**: Redis used for caching questionnaire state in the backend.
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic for database migrations.
- **API**: FastAPI backend providing RESTful endpoints for questionnaire management.
- **Responsive Frontend**: React components with CSS Modules for styling.
- **Offline Support (Basic)**: Frontend attempts to cache answers locally if the user goes offline.

## Getting Started

### Prerequisites
- Node.js (Version as per `package.json` or project needs, e.g., 16+)
- Python (Version as per `requirements.txt` or project needs, e.g., 3.11+)
- PostgreSQL (e.g., 13+)
- Redis (for caching)
- Firebase project setup for authentication.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd APT.-Scanner
    ```

2.  **Backend Setup:**
    ```bash
    cd backend
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r ../requirements.txt
    # Set up .env file with database credentials, Firebase config, etc.
    # Example .env content:
    # DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
    # REDIS_HOST=localhost
    # REDIS_PORT=6379
    # FIREBASE_CREDENTIALS_PATH=../APT-Scanner-Firebase.json
    # Run Alembic migrations
    alembic upgrade head
    # Start the backend server
    uvicorn src.main:app --reload
    ```

3.  **Frontend Setup:**
    ```bash
    cd ../frontend
    npm install
    # Set up .env file or environment variables for VITE_GOOGLE_MAPS_API_KEY
    # Example .env.local content:
    # VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
    npm run dev
    ```

4.  **Firebase Setup:**
    - Place your Firebase service account JSON key file (e.g., `APT-Scanner-Firebase.json`) in the root directory or update `FIREBASE_CREDENTIALS_PATH` in the backend environment.
    - Ensure your Firebase project has Authentication enabled with the necessary sign-in methods.

## Development

- Run backend and frontend servers concurrently as described in the setup.
- Backend API documentation (Swagger UI) is typically available at `/docs` (e.g., `http://localhost:8000/docs`).

## License

(To be added)
