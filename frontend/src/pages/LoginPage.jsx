import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  signInWithEmailAndPassword,
} from "firebase/auth";
import styles from "../styles/LoginPage.module.css";
import { auth } from "../config/firebase";
import { IoMdArrowBack } from "react-icons/io";
import { useQuestionnaireStatus } from "../hooks/useQuestionnaireStatus";
import { LoadingSpinner } from "../components/LoadingSpinner";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { checkStatus } = useQuestionnaireStatus(false);


  const handleNavigateBack = () => {
    navigate(-1);
  };

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const userCredentials = await signInWithEmailAndPassword(auth, email, password);
      
      // Check questionnaire status using hook
      const isComplete = await checkStatus(userCredentials.user);
      
      if (isComplete) {
        navigate("/apartment-swipe");
      } else {
        navigate("/get-started");
      }
      
    } catch (firebaseError) {
      setIsLoading(false);
      console.error("Firebase email login error:", firebaseError.code, firebaseError.message);
      
      if (
        firebaseError.code === "auth/invalid-credential" ||
        firebaseError.code === "auth/user-not-found" ||
        firebaseError.code === "auth/wrong-password"
      ) {
        setError("Invalid email or password.");
      } else if (firebaseError.code === "auth/invalid-email") {
        setError("Please enter a valid email address.");
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };


  const renderLoginForm = () => (
    <form onSubmit={handleEmailLogin} className={styles.loginForm}>
      <div className={styles.inputGroup}>
        <label htmlFor="email" className={styles.label}>
          Email
        </label>
        <input
          type="email"
          id="email"
          className={styles.input}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="example@example.com"
        />
      </div>

      <div className={styles.inputGroup}>
        <label htmlFor="password" className={styles.label}>
          Password
        </label>
        <input
          type="password"
          id="password"
          className={styles.input}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          placeholder="Enter password"
        />
      </div>

      <div className={styles.optionsContainer}>
        <a href="/forgot-password" className={styles.forgotPasswordLink}>
          Forgot password?
        </a>
      </div>

      {error && <p className={styles.errorMessage}>{error}</p>}

      <button type="submit" className={styles.loginButton} disabled={isLoading}>
        {isLoading ? "Logging in..." : "Log in"}
      </button>
    </form>
  );

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className={styles.pageBackground}>
      <div className={styles.loginContainer}>
        <button onClick={handleNavigateBack} className={styles.backButton}>
          <IoMdArrowBack size={24}/>
        </button>
        <h1 className={styles.title}>Log in to your account</h1>
        {renderLoginForm()}
        <p className={styles.disclaimer}>
          By using APT. Scanner, you agree to the
          <br />
          <a href="/terms" target="_blank" rel="noopener noreferrer">
            Terms
          </a>{" "}
          and{" "}
          <a href="/privacy" target="_blank" rel="noopener noreferrer">
            Privacy Policy
          </a>
          .
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
