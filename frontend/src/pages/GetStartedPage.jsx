import React from "react";
import { useNavigate } from "react-router-dom";
import styles from "../styles/GetStartedPage.module.css";
import houseIllustration from "../assets/House.svg";

const GetStartedPage = () => {
    const navigate = useNavigate();

    const handleGetStarted = () => {
        console.log("Get Started button clicked, navigating to questionnaire");
        navigate("/questionnaire");
    };

    return (
        <div className={styles.pageContainer}>
            <div className={styles.backgroundCircle}></div>
                <div className={styles.contentCard}>
                    <h1 className={styles.title}>You are almost set!</h1>
                    <p className={styles.description}>
                        APT. Scanner uses questions to find your perfect neighborhood match.
                    </p>
                    <p className={styles.description}>
                        Answer 6 essential questions to begin.
                        <br />
                        Then, you’ll get the option to go deeper with personalized ones.
                    </p>
                    <img src={houseIllustration} alt="House Illustration" className={styles.illustration} />
                    <button className={styles.getStartedButton} onClick={handleGetStarted}>Get Started</button>
            </div>
        </div>  
    );
};

export default GetStartedPage;