import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { IoMdArrowBack } from 'react-icons/io';
import { useQuestionnaire } from '../hooks/useQuestionnaire';
import styles from '../styles/QuestionnairePage.module.css';
import { LoadingSpinner } from '../components/LoadingSpinner';
import ContinuationPrompt from '../components/ContinuationPrompt';
import RangeSlider from '../components/rangeSlider';
import { fetchPlaceSuggestions } from '../services/mapsApi';

// Add debugging to track state changes
const DEBUG = true;

const QuestionnairePage = () => {
  const navigate = useNavigate();
  const [submissionLoading, setSubmissionLoading] = useState(false);
  const [submissionError, setSubmissionError] = useState(null);
  
  const { 
    currentQuestion, 
    answers,
    loading, 
    error, 
    isComplete, 
    isSubmitted,
    progress, 
    currentStageTotalQuestions, 
    currentStageAnsweredQuestions,
    isOffline,
    answerQuestion: originalAnswerQuestion,
    submitQuestionnaire,
    retry,
    getNumberOfBasicQuestions,
    goToPreviousQuestion,
    canGoBack
  } = useQuestionnaire();
  
  // Wrap answerQuestion to add logging
  const answerQuestion = useCallback((questionId, answer) => {
    if (DEBUG) console.log(`ANSWERING QUESTION ${questionId} with:`, answer);
    originalAnswerQuestion(questionId, answer);
  }, [originalAnswerQuestion]);
  
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [listInputValues, setListInputValues] = useState(['']);
  const [placeSuggestions, setPlaceSuggestions] = useState({});
  const [showSuggestions, setShowSuggestions] = useState({});
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [priceMin, setPriceMin] = useState(2000);
  const [priceMax, setPriceMax] = useState(20000);
  const [textInputValue, setTextInputValue] = useState('');
  const [textSuggestions, setTextSuggestions] = useState([]);
  const [showTextSuggestions, setShowTextSuggestions] = useState(false);
  // Track question changes
  const previousQuestionRef = useRef(null);
  
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Handle place suggestions for autocomplete
  const handlePlaceInput = useCallback(async (value, index = null, isTextInput = false) => {
    if (!value || value.length < 2) {
      if (isTextInput) {
        setTextSuggestions([]);
        setShowTextSuggestions(false);
      } else {
        setPlaceSuggestions(prev => ({...prev, [index]: []}));
        setShowSuggestions(prev => ({...prev, [index]: false}));
      }
      return;
    }

    setLoadingSuggestions(true);
    try {
      const suggestions = await fetchPlaceSuggestions(value);
      if (isTextInput) {
        setTextSuggestions(suggestions);
        setShowTextSuggestions(true);
      } else {
        setPlaceSuggestions(prev => ({...prev, [index]: suggestions}));
        setShowSuggestions(prev => ({...prev, [index]: true}));
      }
    } catch (error) {
      console.error('Error fetching place suggestions:', error);
      if (isTextInput) {
        setTextSuggestions([]);
        setShowTextSuggestions(false);
      } else {
        setPlaceSuggestions(prev => ({...prev, [index]: []}));
        setShowSuggestions(prev => ({...prev, [index]: false}));
      }
    } finally {
      setLoadingSuggestions(false);
    }
  }, []);

  // Monitor question changes for debugging
  useEffect(() => {
    if (currentQuestion && DEBUG) {
      console.log(`Question change detected:`, {
        from: previousQuestionRef.current?.id,
        to: currentQuestion.id,
        type: currentQuestion.type
      });
      previousQuestionRef.current = currentQuestion;
    }
  }, [currentQuestion?.id]);
  
  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion, index = null, isTextInput = false) => {
    if (isTextInput) {
      setTextInputValue(suggestion.description);
      setShowTextSuggestions(false);
    } else {
      const newListValues = [...listInputValues];
      newListValues[index] = suggestion.description;
      setListInputValues(newListValues);
      setShowSuggestions(prev => ({...prev, [index]: false}));
    }
  }, [listInputValues]);

  // Setup total questions counter
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
  
  // Handle question changes
  useEffect(() => {
    if (currentQuestion) {
      if (DEBUG) console.log('Handling question change:', currentQuestion.id, currentQuestion.type);
      
      // Don't reset selectedOptions if we already have a valid selection
      // Only reset when the question ID actually changes
      const shouldResetOptions = !selectedOptions.length || 
        !currentQuestion.options || 
        !currentQuestion.options.includes(selectedOptions[0]);
        
      if (shouldResetOptions) {
        if (DEBUG) console.log('Resetting selected options due to new question');
        setSelectedOptions([]);
      } else if (DEBUG) {
        console.log('Keeping current selection:', selectedOptions);
      }
      
      if (currentQuestion.type === 'slider' && currentQuestion.config) {
        const min = currentQuestion.config.min !== undefined ? currentQuestion.config.min : 0;
        const max = currentQuestion.config.max !== undefined ? currentQuestion.config.max : 100;
        setPriceMin(min);
        setPriceMax(max);
      }
      if (currentQuestion.type === 'list-input') {
        setListInputValues(['']);
        setPlaceSuggestions({});
        setShowSuggestions({});
      }
      if (currentQuestion.type === 'text') {
        setTextInputValue('');
        setTextSuggestions([]);
        setShowTextSuggestions(false);
      }
      setSubmissionError(null);
    }
  }, [currentQuestion?.id]); // Only run this effect when the question ID changes, not on every render

  useEffect(() => {
    if (isSubmitted) {
      navigate('/recommendations');
    }
  }, [isSubmitted, navigate]);

  // Load existing answer when question changes
  useEffect(() => {
    if (currentQuestion && answers && answers[currentQuestion.id]) {
      const existingAnswer = answers[currentQuestion.id];
      if (DEBUG) console.log(`Loading existing answer for question ${currentQuestion.id}:`, existingAnswer);
      
      // Reset all UI states first
      setSelectedOptions([]);
      setTextInputValue('');
      setPriceMin(2000);
      setPriceMax(20000);
      setListInputValues(['']);
      
      // Load the existing answer based on question type
      if (currentQuestion.type === 'single-choice') {
        setSelectedOptions([existingAnswer]);
      } else if (currentQuestion.type === 'multiple-choice') {
        // Handle both array and string formats
        if (Array.isArray(existingAnswer)) {
          setSelectedOptions(existingAnswer);
        } else if (typeof existingAnswer === 'string' && existingAnswer.startsWith('[')) {
          try {
            setSelectedOptions(JSON.parse(existingAnswer));
          } catch (e) {
            setSelectedOptions([existingAnswer]);
          }
        } else {
          setSelectedOptions([existingAnswer]);
        }
      } else if (currentQuestion.type === 'text') {
        setTextInputValue(existingAnswer);
      } else if (currentQuestion.type === 'slider' && Array.isArray(existingAnswer)) {
        setPriceMin(existingAnswer[0] || 2000);
        setPriceMax(existingAnswer[1] || 20000);
      } else if (currentQuestion.type === 'list-input') {
        if (Array.isArray(existingAnswer)) {
          setListInputValues(existingAnswer.length > 0 ? existingAnswer : ['']);
        } else {
          setListInputValues([existingAnswer]);
        }
      }
    } else if (currentQuestion) {
      // No existing answer - clear all UI states
      setSelectedOptions([]);
      setTextInputValue('');
      setPriceMin(2000);
      setPriceMax(20000);
      setListInputValues(['']);
    }
  }, [currentQuestion, answers]);
  
  const handleBack = async () => {
    // Try to go to previous question first
    if (canGoBack()) {
      const success = await goToPreviousQuestion();
      if (success) {
        // Don't clear answers - they will be populated from the existing answer
        return;
      }
    }
    
    // If can't go back or failed, exit questionnaire
    navigate(-1); 
  };

  // Add debug logging for selectedOptions changes
  useEffect(() => {
    if (DEBUG) console.log('Selected options changed:', selectedOptions);
  }, [selectedOptions]);
  
  const handleSingleChoiceAnswer = (option) => {
    if (currentQuestion) {
      if (DEBUG) console.log('Single choice selected:', option);
      setSelectedOptions([option]);
      // answerQuestion is removed, will be handled by Next button
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

  const handleListInputChange = (index, event) => {
    const newListValues = [...listInputValues];
    newListValues[index] = event.target.value;
    setListInputValues(newListValues);
    
    // Trigger place suggestions
    handlePlaceInput(event.target.value, index, false);
  };

  const handleAddListInput = () => {
    if (listInputValues.length < 5) {
      setListInputValues([...listInputValues, '']);
    }
  };

  const handleRemoveListInput = (index) => {
    const newListValues = [...listInputValues];
    newListValues.splice(index, 1);
    setListInputValues(newListValues);
    
    // Clean up suggestions for removed item
    setPlaceSuggestions(prev => {
      const updated = {...prev};
      delete updated[index];
      return updated;
    });
    setShowSuggestions(prev => {
      const updated = {...prev};
      delete updated[index];
      return updated;
    });
  };

  const handleTextInputChange = (event) => {
    setTextInputValue(event.target.value);
    
    // Trigger place suggestions for text input
    handlePlaceInput(event.target.value, null, true);
  };
  
  const handleSubmit = () => {
    submitQuestionnaire();
    navigate('/recommendations');
  };
  
  const goToNextQuestion = (skip = false) => {
    setSubmissionError(null); 

    if (DEBUG) console.log(`goToNextQuestion called - skip: ${skip}`);

    if (skip && currentQuestion) {
      if (DEBUG) console.log('Skipping question:', currentQuestion.id);
      answerQuestion(currentQuestion.id, null); 
      return;
    }
    
    if (!currentQuestion) return;
    
    let currentAnswer = null;

    switch (currentQuestion.type) {
      case 'single-choice':
        if (!selectedOptions.length) {
          setSubmissionError("Please select an option to continue.");
          return;
        }
        currentAnswer = selectedOptions[0];
        break;
      case 'multiple-choice':
        if (selectedOptions.length === 0) {
          setSubmissionError("Please select at least one option.");
          return;
        }
        currentAnswer = JSON.stringify(selectedOptions);
        break;
      case 'slider':
        if (priceMin > priceMax) {
          setSubmissionError("Minimum range value cannot be greater than maximum range value.");
          return;
        }
        currentAnswer = JSON.stringify([priceMin, priceMax]);
        break;
      case 'list-input':
        const filteredListInputs = listInputValues.map(item => item.trim()).filter(item => item !== '');
        if (filteredListInputs.length === 0) {
          setSubmissionError("Please add at least one item to the list or skip.");
          return;
        }
        currentAnswer = JSON.stringify(filteredListInputs);
        break;
      case 'text':
        currentAnswer = textInputValue;
        break;
      default:
        console.warn("Unsupported question type for goToNextQuestion:", currentQuestion.type);
        return;
    }
    
    if (DEBUG) console.log(`Submitting answer for ${currentQuestion.id}:`, currentAnswer);
    answerQuestion(currentQuestion.id, currentAnswer);
    
    if (currentQuestion.type === 'list-input') {
        setListInputValues(['']);
        setPlaceSuggestions({});
        setShowSuggestions({});
    }
    setSelectedOptions([]);
  };
  
  const handleContinuationPrompt = (answer) => {
    let selectedOptionText = "";
    
    // Check if this is a completion prompt or a continuation prompt
    if (currentQuestion.id === "final_completion_prompt") {
      submitQuestionnaire();
      // Handle the completion prompt options
      if (answer === "yes") {
        // First option (View matched apartments)
        navigate('/recommendations');
      } else {
        // Second option (Go to dashboard)
        navigate('/dashboard');
      }
      return;
    }
    
    // Handle regular continuation prompt
    if (answer === "yes") {
      selectedOptionText = "Continue with more questions";
    } else {
      selectedOptionText = "Submit my responses now";
      submitQuestionnaire();
      //navigate('/apartment-swipe');
      navigate('/recommendations');
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
  
  if (currentQuestion && currentQuestion.display_type === 'continuation_page') {
    // Check if this is a completion prompt based on the ID
    const isCompletion = currentQuestion.id === "final_completion_prompt";
    
    return (
      <ContinuationPrompt
        text={currentQuestion.text}
        options={currentQuestion.options}
        onAnswer={handleContinuationPrompt}
        isCompletion={isCompletion}
      />
    );
  }
  
  if (isComplete && !currentQuestion) {
    // If there's no completion question but isComplete is true, show default completion screen
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
  
  const currentSelections = Array.isArray(selectedOptions) ? selectedOptions : [];
  const sliderConfig = currentQuestion.config || { min: 0, max: 100, step: 1, unit: '', labels: [] };

  let showNextButton = currentQuestion.display_type !== 'continuation_page';
  let nextButtonEnabled = true;

  if (currentQuestion.type === 'multiple-choice' && selectedOptions.length === 0) {
      nextButtonEnabled = false;
  } else if (currentQuestion.type === 'single-choice' && selectedOptions.length === 0) {
      nextButtonEnabled = false;
  } else if (currentQuestion.type === 'list-input') {
      const filteredListInputs = listInputValues.map(item => item.trim()).filter(item => item !== '');
      if (filteredListInputs.length === 0) {
          nextButtonEnabled = false;
      }
  }

  return (
    <div className={styles.pageContainer}>
      <div className={styles.header}>
        <button 
          onClick={handleBack} 
          className={`${styles.backButton} ${!canGoBack() ? styles.backButtonDisabled : ''}`}
          aria-label={canGoBack() ? "חזור לשאלה הקודמת" : "יציאה מהשאלון"}
          title={canGoBack() ? "חזור לשאלה הקודמת" : "יציאה מהשאלון"}
        >
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
            <div className={styles.sliderGroup}>
              <RangeSlider
                min={sliderConfig.min}
                max={sliderConfig.max}
                step={sliderConfig.step}
                valueMin={priceMin}
                valueMax={priceMax}
                onChangeMin={setPriceMin}
                onChangeMax={setPriceMax}
                labels={sliderConfig.labels}
              />
            </div>
          </div>
        )}

        {currentQuestion.type === 'text' && (
          <div className={styles.textInputContainer}>
            <div className={styles.autocompleteContainer}>
              <input
                type="text"
                value={textInputValue}
                onChange={handleTextInputChange}
                placeholder={currentQuestion.placeholder}
                className={styles.textInput}
                onFocus={() => {
                  if (textSuggestions.length > 0) {
                    setShowTextSuggestions(true);
                  }
                }}
              />
              {showTextSuggestions && textSuggestions.length > 0 && (
                <div className={styles.suggestionsDropdown}>
                  {textSuggestions.map((suggestion, index) => (
                    <div
                      key={suggestion.place_id || index}
                      className={styles.suggestionItem}
                      onClick={() => handleSuggestionSelect(suggestion, null, true)}
                    >
                      <div className={styles.suggestionText}>
                        {suggestion.structured_formatting?.main_text && (
                          <span className={styles.mainText}>
                            {suggestion.structured_formatting.main_text}
                          </span>
                        )}
                        {suggestion.structured_formatting?.secondary_text && (
                          <span className={styles.secondaryText}>
                            {suggestion.structured_formatting.secondary_text}
                          </span>
                        )}
                        {!suggestion.structured_formatting && (
                          <span>{suggestion.description}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {loadingSuggestions && <p className={styles.loadingText}>Loading suggestions...</p>}
          </div>
        )}
        

        {currentQuestion.type === 'list-input' && (
          <div className={styles.listInputContainer}>
            {listInputValues.map((value, index) => (
              <div key={index} className={styles.listItem}>
                <div className={styles.autocompleteContainer}>
                  <input
                    type="text"
                    value={value}
                    onChange={(e) => handleListInputChange(index, e)}
                    placeholder={index === 0 ? 'eg. your office, university...' : ''}
                    className={styles.listInput}
                    onFocus={() => {
                      if (placeSuggestions[index] && placeSuggestions[index].length > 0) {
                        setShowSuggestions(prev => ({...prev, [index]: true}));
                      }
                    }}
                  />
                  {showSuggestions[index] && placeSuggestions[index] && placeSuggestions[index].length > 0 && (
                    <div className={styles.suggestionsDropdown}>
                      {placeSuggestions[index].map((suggestion, suggestionIndex) => (
                        <div
                          key={suggestion.place_id || suggestionIndex}
                          className={styles.suggestionItem}
                          onClick={() => handleSuggestionSelect(suggestion, index, false)}
                        >
                          <div className={styles.suggestionText}>
                            {suggestion.structured_formatting?.main_text && (
                              <span className={styles.mainText}>
                                {suggestion.structured_formatting.main_text}
                              </span>
                            )}
                            {suggestion.structured_formatting?.secondary_text && (
                              <span className={styles.secondaryText}>
                                {suggestion.structured_formatting.secondary_text}
                              </span>
                            )}
                            {!suggestion.structured_formatting && (
                              <span>{suggestion.description}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                {listInputValues.length > 1 && (
                  <button 
                    onClick={() => handleRemoveListInput(index)} 
                    className={styles.removeListItemButton}
                    aria-label={`Remove item ${index + 1}`}
                  >
                    &times;
                  </button>
                )}
              </div>
            ))}
            {listInputValues.length < 5 && (
              <button 
                onClick={handleAddListInput} 
                className={styles.addListItemButton}
              >
                + Add Item
              </button>
            )}
            {loadingSuggestions && <p className={styles.loadingText}>Loading suggestions...</p>}
          </div>
        )}
      </div>
        
      {showNextButton && ( 
        <button
          className={styles.nextButton}
          onClick={() => goToNextQuestion()}
          disabled={!nextButtonEnabled || submissionLoading}
        >
          {submissionLoading ? 'Submitting...' : (currentQuestionIndex < totalQuestions - 1 || currentQuestion.display_type === 'continuation_page' ? 'Next Question' : 'Finish')}
        </button>
      )}
      
      {currentQuestionIndex <= totalQuestions - 1 && (
          <button 
            className={styles.skipLink} 
            onClick={() => goToNextQuestion(true)}
          >
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

