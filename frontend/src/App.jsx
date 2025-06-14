import React, { Suspense } from "react";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LoadingSpinner } from './components/LoadingSpinner';
import GetStartedPage from "./pages/GetStartedPage";
import FilterPage from './pages/FilterPage';
import FavoritesApartmentDetails from './pages/FavoritesApartmentDetails';
import RecommendationsPage from './pages/RecommendationsPage';

// Lazy load pages
const LandingPage = React.lazy(() => import("./pages/LandingPage"));
const LoginPage = React.lazy(() => import("./pages/LoginPage"));
const RegisterPage = React.lazy(() => import("./pages/RegisterPage"));
const QuestionnairePage = React.lazy(() => import("./pages/QuestionnairePage"));
const ApartmentSwipePage = React.lazy(() => import("./pages/ApartmentSwipePage"));
const FavoritesPage = React.lazy(() => import('./pages/FavoritesPage'));

function App() {
  return (
    <Router>
      <Suspense fallback={<LoadingSpinner />}>
        <div className="App">
          <div className="content">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/get-started" element={<GetStartedPage />} />
              <Route path="/questionnaire" element={<QuestionnairePage />} />
              <Route path="/apartment-swipe" element={<ApartmentSwipePage />} />
              <Route path="/favorites" element={<FavoritesPage />} />
              <Route path="/filter" element={<FilterPage />} />
              <Route path="/favorites/:token" element={<FavoritesApartmentDetails />} />
              <Route path="/recommendations" element={<RecommendationsPage />} />
            </Routes>
          </div>
        </div>
      </Suspense>
    </Router>
  );
}

export default App;
