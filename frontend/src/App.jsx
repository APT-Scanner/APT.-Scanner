import React from "react";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import GetStartedPage from "./pages/GetStartedPage";
import QuestionnairePage from "./pages/QuestionnairePage";

function App() {

  return (
    <Router>
      <div className="App">
        <div className="content">
          <Routes>
            <Route path = "/" element={<LandingPage />}></Route>
            <Route path = "/login" element={<LoginPage/>}></Route>
            <Route path = "/register" element={<RegisterPage/>}></Route>
            <Route path = "/get-started" element={<GetStartedPage/>}></Route>
            <Route path = "/questionnaire" element = {<QuestionnairePage/>}></Route>
          </Routes>
        </div>
      </div>
    </Router>
  )
}

export default App
