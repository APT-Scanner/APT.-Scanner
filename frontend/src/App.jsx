//import './App.css'
import React from "react";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

function App() {

  return (
    <Router>
      <div className="App">
        <div className="content">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path ="/login" element={<LoginPage/>}></Route>
            <Route path= "/register" element={<RegisterPage/>}></Route>
          </Routes>
        </div>
      </div>
    </Router>
  )
}

export default App
