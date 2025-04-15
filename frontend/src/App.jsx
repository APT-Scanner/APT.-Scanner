//import './App.css'
import React from "react";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from "./pages/LandingPage";

function App() {

  return (
    <Router>
      <div className="App">
        <div className="content">
          <Routes>
            <Route path="/" element={<LandingPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  )
}

export default App
