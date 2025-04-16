import React from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/LandingPage.module.css";
import logo from "../assets/Logo.svg";
import house from "../assets/House.svg";

const LandingPage = () => {

    const navigate = useNavigate();

    const handleCreateAccount = () => {
        console.log("Navigate to create account page")
        navigate("/register")
    };

    const HandleLogin = (e) => {
        e.preventDefault();
        console.log("Navigate to Log In page")
        navigate("/login")
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
                    <button className = {styles.createAccountButton} onClick = {handleCreateAccount}>Create an Account</button>
                    <p>Already have an account?  
                    <a herf = "/login" className = {styles.loginLink} onClick = {HandleLogin}> Log in</a></p>
                </div>
            </div>
        </div>
    );
};

export default LandingPage;