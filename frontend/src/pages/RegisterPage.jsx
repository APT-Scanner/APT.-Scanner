import React, { use, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/RegisterPage.module.css";
import { getAuth, createUserWithEmailAndPassword } from "firebase/auth";
import { FaCheckCircle, FaRegCircle, FaEye, FaEyeSlash } from "react-icons/fa";
import { IoMdArrowBack } from "react-icons/io";
import { auth } from "../config/firebase";

const validatePassword = (password) => {
  const requirements = {
    length: password.length >= 8,
    number: /\d/.test(password),
    symbol: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
  const isValid =
    requirements.length && requirements.number && requirements.symbol;
  return { isValid, requirements };
};

const RegisterPage = () => {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    number: false,
    symbol: false,
  });
  const [isPasswordValid, setIsPasswordValid] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (step === 2) {
      const validation = validatePassword(password);
      setPasswordRequirements(validation.requirements);
      setIsPasswordValid(validation.isValid);
    }
  }, [password, step]);

  const handleNavigateBack = () => {
    if (step === 2) {
      setStep(1);
      setError("");
    } else {
      navigate(-1);
    }
  };

  const handleContinueToPassword = (e) => {
    e.preventDefault();
    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    setError("");
    setStep(2);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!isPasswordValid) {
      setError("Password does not meet all requirements.");
      return;
    }
    setError("");
    setIsLoading(true);

    try {
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email,
        password
      );
      const user = userCredential.user;
      console.log("Registration successful:", userCredential.user);
      if (user) {
        const idToken = await user.getIdToken(); // Get the token
        try {
          const backendUrl = 'http://localhost:8000/api/v1/users/sync-profile';
          const response = await fetch(backendUrl, {
            method: "POST",
            headers: {
              Authorization: `Bearer ${idToken}`,
              "Content-Type": "application/json",
            },
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(
              errorData.detail || `Backend sync failed: ${response.statusText}`
            );
          }

          const backendUser = await response.json();
          console.log("Backend sync successful:", backendUser);

          setIsLoading(false);
          navigate("/getstarted");
        } catch (backendError) {
          console.error("Backend sync error:", backendError);
          setError(
            `Registration succeeded but profile sync failed: ${backendError.message}. Please try logging in.`
          );
          setIsLoading(false);
        }
      } else {
        throw new Error(
          "User object not received after Firebase registration."
        );
      }
    } catch (firebaseError) {
      setIsLoading(false);
      console.error(
        "Firebase registration error:",
        firebaseError.code,
        firebaseError.message
      );
      if (firebaseError.code === "auth/email-already-in-use") {
        setError("This email address is already registered. Try logging in.");
      } else if (firebaseError.code === "auth/weak-password") {
        setError("Password is too weak. Please choose a stronger one.");
      } else {
        setError("Registration failed. Please try again.");
      }
    }
  };

  const renderStepIndicator = () => (
    <div className={styles.stepIndicator}>
      <div
        className={`${styles.stepDot} ${step >= 1 ? styles.active : ""}`}
      ></div>
      <div
        className={`${styles.stepDot} ${step >= 2 ? styles.active : ""}`}
      ></div>
    </div>
  );

  const renderEmailStep = () => (
    <form onSubmit={handleContinueToPassword} className={styles.form}>
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
      {error && <p className={styles.errorMessage}>{error}</p>}
      <button type="submit" className={styles.continueButton}>
        Continue
      </button>
    </form>
  );

  const renderPasswordStep = () => (
    <form onSubmit={handleRegister} className={styles.form}>
      <div className={styles.inputGroup}>
        <label htmlFor="password" className={styles.label}>
          Password
        </label>
        <div className={styles.passwordWrapper}>
          <input
            type={showPassword ? "text" : "password"}
            id="password"
            className={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            placeholder="Enter password"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className={styles.showPasswordButton}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <FaEyeSlash /> : <FaEye />}
          </button>
        </div>
      </div>

      <div className={styles.requirements}>
        <div
          className={`${styles.requirementItem} ${
            passwordRequirements.length ? styles.met : ""
          }`}
        >
          {passwordRequirements.length ? <FaCheckCircle /> : <FaRegCircle />} 8
          characters minimum
        </div>
        <div
          className={`${styles.requirementItem} ${
            passwordRequirements.number ? styles.met : ""
          }`}
        >
          {passwordRequirements.number ? <FaCheckCircle /> : <FaRegCircle />} a
          number
        </div>
        <div
          className={`${styles.requirementItem} ${
            passwordRequirements.symbol ? styles.met : ""
          }`}
        >
          {passwordRequirements.symbol ? <FaCheckCircle /> : <FaRegCircle />} a
          symbol
        </div>
      </div>

      {error && <p className={styles.errorMessage}>{error}</p>}

      <button
        type="submit"
        className={styles.createButton}
        disabled={isLoading || !isPasswordValid}
      >
        {isLoading ? "Creating Account..." : "Create an Account"}
      </button>
    </form>
  );

  return (
    <div className={styles.pageBackground}>
      <div className={styles.registerContainer}>
        <button onClick={handleNavigateBack} className={styles.backButton}>
          <IoMdArrowBack size={24} />
        </button>

        <h1 className={styles.title}>
          {step === 1 ? "Add your email" : "Create your password"}
        </h1>

        {renderStepIndicator()}

        {step === 1 ? renderEmailStep() : renderPasswordStep()}

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

export default RegisterPage;
