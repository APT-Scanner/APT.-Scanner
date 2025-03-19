# APT. Scanner

An AI-driven platform that helps users find the best-matched neighborhoods based on personalized questionnaires. APT. Scanner integrates machine learning, web scraping, and dynamic property recommendations to provide a comprehensive solution for property seekers.

## Project Overview

APT. Scanner combines advanced AI algorithms with real estate data to deliver personalized neighborhood recommendations based on user preferences and needs. The platform processes user inputs through customized questionnaires, analyzes various data sources, and provides tailored recommendations for ideal living locations.

## Tech Stack

- **Frontend**: React.js
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **AI/ML**: Scikit-learn, TensorFlow/PyTorch
- **APIs & Data Sources**: 
  - Yad2 web scraping
  - Gov.il API
  - Google Maps API
  - Wikipedia API
- **Authentication**: Firebase
- **Hosting & Deployment**: AWS or Google Cloud
- **Real-time interactions**: WebSockets

## Project Structure

The project follows a monorepo architecture with the following main directories:

```
APT.-Scanner/
├── backend/
│   ├── src/
│   │   ├── config/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── styles/
│   │   └── App.jsx
└── .env
```

### Backend
- **`backend/src/config/`**: Contains configuration files, such as `settings.py`, which manage environment variables and application settings.
- **`backend/src/models/`**: Defines the database models and schemas for the application.
- **`backend/src/routes/`**: Contains route definitions for the API endpoints.
- **`backend/src/services/`**: Implements the business logic and services used by the application.
- **`backend/src/utils/`**: Utility functions and helpers used across the backend.
- **`backend/src/main.py`**: The entry point for the backend application.

### Frontend
- **`frontend/public/`**: Static assets such as images, icons, and the `index.html` file.
- **`frontend/src/components/`**: Reusable React components used throughout the application.
- **`frontend/src/pages/`**: Page-level components representing different views in the application.
- **`frontend/src/services/`**: Handles API calls and interactions with the backend.
- **`frontend/src/styles/`**: Contains global and component-specific styles.
- **`frontend/src/App.jsx`**: The main React component that initializes the application.

### `.env`
- Stores environment-specific variables such as database connection strings, API keys, and secret keys.


## Getting Started

### Prerequisites
- Node.js 16+
- Python 3.8+
- PostgreSQL 13+
- Docker (optional)

### Installation

Detailed installation instructions coming soon.

## Development

Detailed development guidelines coming soon.

## License

[Insert License Information]
