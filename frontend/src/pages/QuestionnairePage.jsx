import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { IoMdArrowBack } from 'react-icons/io';
import { useQuestionnaire } from '../hooks/useQuestionnaire';
import styles from '../styles/QuestionnairePage.module.css';
import { LoadingSpinner } from '../components/loadingSpinner';
import ContinuationPrompt from '../components/ContinuationPrompt';

const QuestionnairePage = () => {
  const navigate = useNavigate();
  const [submissionLoading, setSubmissionLoading] = useState(false);
  const [submissionError, setSubmissionError] = useState(null);
  
  const { 
    currentQuestion, 
    loading, 
    error, 
    isComplete, 
    isSubmitted,
    progress, // Overall percentage
    currentStageTotalQuestions, // New: Total for current stage (e.g., 5 for dynamic batch)
    currentStageAnsweredQuestions, // New: Answered in current stage
    isOffline,
    answerQuestion, 
    submitQuestionnaire,
    retry,
    getNumberOfBasicQuestions 
  } = useQuestionnaire();
  
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [sliderValue, setSliderValue] = useState(50);
  
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  useEffect(() => {
    if (currentStageTotalQuestions > 0) {
      setTotalQuestions(currentStageTotalQuestions);
      setCurrentQuestionIndex(Math.max(0, Math.min(currentStageAnsweredQuestions, currentStageTotalQuestions -1)));
    } else if (getNumberOfBasicQuestions) { 
      const fetchInitialTotal = async () => {
        try {
          const count = await getNumberOfBasicQuestions();
          setTotalQuestions(count);
          if (count > 0) {
             const initialCalculatedIndex = Math.min(Math.floor(progress / (100/count)), count -1 ) ;
             setCurrentQuestionIndex(Math.max(0, initialCalculatedIndex));
          }
        } catch (err) {
          console.error("Failed to fetch total questions (fallback):", err);
          setTotalQuestions(7); 
        }
      };
      fetchInitialTotal();
    }
  }, [currentStageTotalQuestions, currentStageAnsweredQuestions, getNumberOfBasicQuestions, progress]);
  
  useEffect(() => {
    if (currentQuestion) {
      if (currentQuestion.type === 'multiple-choice') {
        setSelectedOptions([]);
      } else if (currentQuestion.type === 'slider' && currentQuestion.config) {
        setSliderValue(currentQuestion.config.initial || currentQuestion.config.min || 0);
      }
      setSubmissionError(null);
    }
  }, [currentQuestion]);
  
  useEffect(() => {
    if (isSubmitted) {
      navigate('/dashboard');
    }
  }, [isSubmitted, navigate]);
  
  const handleBack = () => {
    navigate('/get-started'); 
  };
  
  const handleSingleChoiceAnswer = (option) => {
    if (currentQuestion) {
      setSelectedOptions([option]);
      answerQuestion(currentQuestion.id, option);
    }
  };
  
  const handleMultipleChoiceSelect = (option) => {
    setSelectedOptions(prev => {
      const newSelection = prev.includes(option) 
        ? prev.filter(item => item !== option) 
        : [...prev, option];
      return newSelection;
    });
  };
  
  const handleMultipleChoiceSubmit = () => {
    if (currentQuestion && selectedOptions.length > 0) {
      const serializedAnswer = JSON.stringify(selectedOptions);
      answerQuestion(currentQuestion.id, serializedAnswer);
      setSubmissionError(null);
    } else if (selectedOptions.length === 0) {
         setSubmissionError("Please select at least one option.");
    }
  };
  
  const handleSliderChange = (e) => {
    setSliderValue(parseInt(e.target.value, 10));
  };
  
  const handleSubmit = () => {
    submitQuestionnaire();
    navigate('/apartment-swipe');
  };
  
  const goToNextQuestion = (skip = false) => {
    setSubmissionError(null); 

    if (skip && currentQuestion) {
      answerQuestion(currentQuestion.id, null); 
      return;
    }
    
    if (!currentQuestion) return;
    
    switch (currentQuestion.type) {
      case 'single-choice':
        if (!selectedOptions.length) {
          setSubmissionError("Please select an option to continue.");
          return;
        }
        if (selectedOptions.length > 0) {
            answerQuestion(currentQuestion.id, selectedOptions[0]);
        }
        break;
      case 'multiple-choice':
        if (selectedOptions.length === 0) {
          setSubmissionError("Please select at least one option.");
          return;
        }
        const serializedAnswer = JSON.stringify(selectedOptions);
        answerQuestion(currentQuestion.id, serializedAnswer);
        break;
      case 'slider':
        answerQuestion(currentQuestion.id, sliderValue);
        break;
      default:
        console.warn("Unsupported question type for goToNextQuestion:", currentQuestion.type);
        return;
    }
  };
  
  const handleContinuationPrompt = (answer) => {
    let selectedOptionText = "";
    if (answer === "yes") {
      selectedOptionText = "Continue with more questions";
    } else {
      selectedOptionText = "Submit my responses now";
    }
    answerQuestion(currentQuestion.id, selectedOptionText);
  };
  
  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2>Oops! Something went wrong</h2>
        <p>{error}</p>
        {isOffline && <p className={styles.offlineMessage}>You appear to be offline. Your answers will be saved locally.</p>}
        <button className={styles.retryButton} onClick={retry}>
          Retry
        </button>
        <button className={styles.backButton} onClick={handleBack}>
          Back to Start
        </button>
      </div>
    );
  }
  
  if (loading || (totalQuestions === 0 && !currentQuestion) ) {
    return (
      <LoadingSpinner />
    );
  }
  
  if (isComplete) {
    return (
      <div className={styles.completionContainer}>
        <h2>Questionnaire Complete!</h2>
        <p>Thank you for answering all the questions. We'll use your preferences to find the best apartments for you.</p>
        <button 
          className={styles.submitButton} 
          onClick={handleSubmit}
          disabled={submissionLoading}
        >
          {submissionLoading ? 'Submitting...' : 'Submit Answers'}
        </button>
      </div>
    );
  }
  
  if (!currentQuestion) {
    return (
      <div className={styles.noQuestionsContainer}>
        <h2>No questions available</h2>
        <p>We couldn't find any questions for you right now. This might be because the questionnaire is complete or there was an issue loading.</p>
        <button className={styles.backButton} onClick={handleBack}>
          Back to Start
        </button>
      </div>
    );
  }
  
  if (currentQuestion.display_type === 'continuation_page') {
    return (
      <ContinuationPrompt
        text={currentQuestion.text}
        options={currentQuestion.options}
        onAnswer={handleContinuationPrompt}
      />
    );
  }
  
  const currentSelections = Array.isArray(selectedOptions) ? selectedOptions : [];
  const sliderConfig = currentQuestion.config || { min: 0, max: 100, step: 1, unit: '' };

  let showNextButton = false;
  let nextButtonEnabled = false;

  if (currentQuestion.type === 'multiple-choice' || currentQuestion.type === 'slider') {
      showNextButton = true;
      if (currentQuestion.type === 'multiple-choice' && selectedOptions.length > 0) {
          nextButtonEnabled = true;
      } else if (currentQuestion.type === 'slider') {
          nextButtonEnabled = true; 
      }
  }

  return (
    <div className={styles.pageContainer}>
      <div className={styles.header}>
        <button onClick={handleBack} className={styles.backButton} aria-label="Go back">
          <IoMdArrowBack size={24} />
        </button>
        {totalQuestions > 0 && (
          <div 
            className={styles.progressBarContainer} 
            aria-label={`Question ${currentQuestionIndex + 1} of ${totalQuestions}`}
            key={`progress-bar-${currentQuestionIndex}-${totalQuestions}-${currentStageAnsweredQuestions}`} 
          >
            {Array.from({ length: totalQuestions }).map((_, index) => (
              <div
                key={`dot-${index}-${index <= currentQuestionIndex}`}
                className={`${styles.progressDot} ${index <= currentQuestionIndex ? styles.active : ''}`}
                title={`Question ${index + 1} ${index <= currentQuestionIndex ? '(completed)' : ''}`}
              />
            ))}
          </div>
        )}
        <span className={styles.progressText} aria-hidden="true">
          {totalQuestions > 0 ? `${currentQuestionIndex + 1} of ${totalQuestions}` : 'Loading...'}
        </span>
      </div>
        
      <div className={styles.questionCard}>
        <p id="question-text" className={styles.questionText}>{currentQuestion.text}</p>
      </div>

      <div className={styles.optionsContainer} role="group" aria-labelledby="question-text">
        {currentQuestion.type === 'single-choice' && currentQuestion.options.map((option, index) => (
          <button
            key={option + index}
            role="radio"
            aria-checked={selectedOptions.includes(option)}
            className={`${styles.optionButton} ${selectedOptions.includes(option) ? styles.selected : ''}`}
            onClick={() => handleSingleChoiceAnswer(option)} 
          >
            <span className={styles.radioCircle} aria-hidden="true"></span>
            {option}
          </button>
        ))}
          
        {currentQuestion.type === 'multiple-choice' && currentQuestion.options.map((option, index) => (
          <button
            key={option + index}
            role="checkbox"
            aria-checked={currentSelections.includes(option)}
            className={`${styles.optionButton} ${currentSelections.includes(option) ? styles.selected : ''} ${styles.checkbox}`}
            onClick={() => handleMultipleChoiceSelect(option)} 
          >
            <span className={styles.checkboxSquare} aria-hidden="true">
              {currentSelections.includes(option) && <span className={styles.checkmark}>✓</span>}
            </span>
            <span className={styles.checkboxText}>{option}</span>
          </button>
        ))}
          
        {currentQuestion.type === 'slider' && (
          <div className={styles.sliderContainer}>
            <input 
              type="range"
              min={sliderConfig.min} 
              max={sliderConfig.max} 
              step={sliderConfig.step} 
              value={sliderValue}
              onChange={handleSliderChange}
              className={styles.sliderInput}
            />
            <div className={styles.sliderValueDisplay}>
              {sliderValue} {sliderConfig.unit} 
            </div>
          </div>
        )}
      </div>
        
      {showNextButton && ( 
        <button
          className={styles.nextButton}
          onClick={() => goToNextQuestion()}
          disabled={!nextButtonEnabled || submissionLoading}
        >
          {submissionLoading ? 'Submitting...' : (currentQuestionIndex < totalQuestions - 1 ? 'Next Question' : 'Finish')}
        </button>
      )}
      
      {!(currentQuestionIndex >= totalQuestions - 1 && totalQuestions > 0) && (
          <button className={styles.skipLink} onClick={() => goToNextQuestion(true)}>
              SKIP TO NEXT QUESTION &gt;
          </button>
      )}

      {submissionError && <p className={`${styles.message} ${styles.error}`}>{submissionError}</p>}
      
      {isOffline && (
        <div className={styles.offlineBanner}>
          You are currently offline. Your answers are being saved locally.
        </div>
      )}
    </div>
  );
};

export default QuestionnairePage;

