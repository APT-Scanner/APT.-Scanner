import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/LandingPage.module.css";
import logo from "../assets/Logo.svg";
import house from "../assets/House.svg";
import { GoogleAuthProvider, FacebookAuthProvider, signInWithPopup } from "firebase/auth";
import { auth } from "../config/firebase";
import { useQuestionnaireStatus } from "../hooks/useQuestionnaireStatus";
import { createUserInDatabase } from "../services/userService";
import { getUserFromDatabase } from "../services/userService";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { Loader } from "lucide-react";

const LandingPage = () => {

    const navigate = useNavigate();
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { checkStatus } = useQuestionnaireStatus();

    const handleCreateAccount = () => {
        console.log("Navigate to create account page")
        navigate("/register")
    };

    const HandleLogin = (e) => {
        e.preventDefault();
        console.log("Navigate to Log In page")
        navigate("/login")
    };

    
  const handleSocialLogin = async (providerName) => {
    setError("");
    setIsLoading(true);
    let provider;

    if (providerName === "google") {
      provider = new GoogleAuthProvider();
    } else if (providerName === "facebook") {
      provider = new FacebookAuthProvider();
    } else {
      setError("Unknown Provider");
      setIsLoading(false);
      return;
    }

        try {
      const result = await signInWithPopup(auth, provider);
      console.log(`${providerName} Sign-in successful:`, result.user);
      
      // Try to get user from database, create if doesn't exist
      try {
        const existingUser = await getUserFromDatabase(result.user);
        console.log("User found in database:", existingUser);
      } catch (error) {
        // User doesn't exist, create new user
        console.log("User not found, creating new user...");
        try {
          const dbUser = await createUserInDatabase(result.user);
          console.log("User created in database:", dbUser);
        } catch (createError) {
          console.error("Failed to create user:", createError);
          // Continue anyway, user might still be able to use the app
        }
      }

      // Check questionnaire status using the Firebase user object
      const isComplete = await checkStatus(result.user);
      
      if (isComplete) {
        navigate("/apartment-swipe");
      } else {
        navigate("/get-started");
      }
      
      setIsLoading(false);
      
    } catch (error) {
      setIsLoading(false);
      console.error(`${providerName} Sign-in error:`, error.code, error.message);
      
      if (error.code === "auth/popup-closed-by-user") {
        setError("Login process cancelled.");
      } else if (error.code === "auth/account-exists-with-different-credential") {
        setError("An account already exists with the same email address but different sign-in credentials. Sign in using a provider associated with this email address.");
      } else {
        setError(`${providerName} login failed. Please try again.`);
      }
    }
  };

    return(
        <div className = {styles.pageContainer}>
            <div className={styles.backgroundCircle}></div>
            <div className = {styles.card}>
                <div className = {styles.cardContent}>
                    <img src = {logo} alt = "APT.Scanner logo" className ={styles.logo}></img>
                    <h2 className = {styles.slogen}>
                        Find your perfect match,
                        <br />
                        The apartment thats fits you.
                    </h2>
                    <img src = {house} alt = "house illustration" className ={styles.illustration}></img>
                    <button 
                        className = {styles.createAccountButton} 
                        onClick = {handleCreateAccount}
                        disabled={isLoading}
                    >
                        Create an Account
                    </button>
                    <button 
                        className = {styles.socialLoginButton} 
                        onClick = {() => handleSocialLogin("google")}
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <>
                                <Loader size={18} className={styles.loadingIcon} />
                                Signing in...
                            </>
                        ) : (
                            <>
                                <svg className={styles.googleLogo} width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                                    <path fill="#4285F4" d="M16.51 8H15V8h-6v4h5.02c-.76 2.27-2.98 4-5.52 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.17.69 4.27 1.78L15.91 2.64C14.16.89 11.69 0 9 0 4.03 0 0 4.03 0 9s4.03 9 9 9 9-4.03 9-9c0-.55-.05-1.1-.14-1.63L16.51 8z"/>
                                    <path fill="#34A853" d="M2.63 5.27L5.5 7.47C6.26 5.72 7.96 4.5 10 4.5c1.39 0 2.65.5 3.64 1.32l2.84-2.84C14.77 1.29 12.5.5 10 .5c-3.31 0-6.25 1.81-7.78 4.47l.41.3z"/>
                                    <path fill="#FBBC05" d="M10 18c2.43 0 4.66-.75 6.38-2.05l-2.78-2.42C12.69 14.25 11.39 14.75 10 14.75c-2.51 0-4.71-1.69-5.49-3.97L1.63 12.73C3.12 16.25 6.31 18 10 18z"/>
                                    <path fill="#EA4335" d="M2.63 5.27C2.24 6.11 2 7.03 2 8s.24 1.89.63 2.73l2.88-2.24C5.24 7.89 5.5 7.47 5.5 7c0-.47.24-.89.51-1.27L2.63 5.27z"/>
                                </svg>
                                Continue with Google
                            </>
                        )}
                    </button>
                    {/* <button className = {styles.socialLoginButton} onClick = {() => handleSocialLogin("facebook")}>Continue with Facebook</button> */}
                    {error && <p className={styles.errorMessage}>{error}</p>}
                    <p>Already have an account?  
                    <a herf = "/login" className = {styles.loginLink} onClick = {HandleLogin}> Log in</a></p>
                </div>
            </div>
        </div>
    );
};

export default LandingPage;