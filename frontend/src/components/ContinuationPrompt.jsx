import React from 'react';
import styles from '../styles/ContinuationPrompt.module.css';

/**
 * Component for displaying a special prompt page
 * This is used for both:
 * 1. Continuation prompts (after first 10 questions and then every 5 questions)
 * 2. Completion prompts (when the questionnaire is complete)
 * 
 * Props:
 * @param {string} text - The main message to display
 * @param {Array} options - Array of button text options (usually 2 options)
 * @param {Function} onAnswer - Callback for when an option is selected
 * @param {boolean} isCompletion - Whether this is a completion prompt (for styling)
 */
const ContinuationPrompt = ({ text, options, onAnswer, isCompletion = false }) => {
  // Handle option click with consistent "yes"/"no" values
  const handleOptionClick = (option, index) => {
    // First option (index 0) is always "yes", second is always "no"
    const value = index === 0 ? "yes" : "no";
    console.log(`Selected ${option} with value ${value}`);
    onAnswer(value);
  };
  
  return (
    <div className={styles.container}>
      <div className={`${styles.promptBox} ${isCompletion ? styles.completionBox : ''}`}>
        <div className={styles.promptContent}>
          <h2 className={styles.title}>{isCompletion ? 'Congratulations!' : 'Your Progress'}</h2>
          <div className={`${styles.checkmark} ${isCompletion ? styles.completionCheckmark : ''}`}>✓</div>
          <p className={styles.promptText}>{text}</p>
          
          <div className={styles.options}>
            {options.map((option, index) => (
              <button 
                key={`option-${index}`}
                className={
                  isCompletion 
                    ? (index === 0 ? styles.primaryButton : styles.secondaryButton)
                    : (index === 0 ? styles.continueButton : styles.submitButton)
                }
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