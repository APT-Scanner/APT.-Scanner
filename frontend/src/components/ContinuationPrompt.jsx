import React from 'react';
import styles from '../styles/ContinuationPrompt.module.css';

/**
 * Component for displaying a special continuation prompt page
 * This is shown after completing basic questions or after every 5 additional questions
 */
const ContinuationPrompt = ({ text, options, onAnswer }) => {
  // Handle option click with consistent "yes"/"no" values
  const handleOptionClick = (option, index) => {
    // First option (index 0) is always "yes", second is always "no"
    const value = index === 0 ? "yes" : "no";
    console.log(`Selected ${option} with value ${value}`);
    onAnswer(value);
  };
  
  return (
    <div className={styles.container}>
      <div className={styles.promptBox}>
        <div className={styles.promptContent}>
          <h2 className={styles.title}>Your Progress</h2>
          <div className={styles.checkmark}>✓</div>
          <p className={styles.promptText}>{text}</p>
          
          <div className={styles.options}>
            {options.map((option, index) => (
              <button 
                key={`option-${index}`}
                className={index === 0 ? styles.continueButton : styles.submitButton}
                onClick={() => handleOptionClick(option, index)}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContinuationPrompt; 