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
│   │   ├── config/         # Configuration files (e.g., settings.py)
│   │   ├── models/         # Database models and schemas
│   │   ├── routes/         # API endpoint route definitions
│   │   ├── services/       # Business logic and services
│   │   ├── utils/          # Utility functions and helpers
│   │   └── main.py         # Entry point for the backend application
│   ├── scripts/            # Standalone scripts (e.g., data fetching, seeding)
│   ├── tests/              # Unit and integration tests for the backend
├── frontend/
│   ├── public/             # Static assets (e.g., images, icons, index.html)
│   ├── src/
│   │   ├── components/     # Reusable React components
│   │   ├── pages/          # Page-level components
│   │   ├── services/       # API calls and backend interactions
│   │   ├── styles/         # Global and component-specific styles
│   │   └── App.jsx         # Main React component
│   ├── tests/              # Unit and integration tests for the frontend
├── shared/
│   ├── constants/          # Shared constants used across the project
│   └── utils/              # Shared utility functions used by both frontend and backend   
├── docs/                   # Documentation files (e.g., API docs, diagrams)
├── data/                   # Data-related files and scripts
│   ├── processing/         # Scripts for processing raw data
│   ├── scrapers/           # Web scraping scripts for data collection
│   └── sources/            # Raw data files or external data sources
├── ai/                     # AI/ML-related files
│   ├── evaluation/         # Scripts and tools for evaluating AI models
│   ├── models/             # Trained models and model definitions
│   └── preprocessing/      # Scripts for preprocessing data for AI/ML tasks
└── .env                    # Environment-specific variables (e.g., API keys)
```

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
