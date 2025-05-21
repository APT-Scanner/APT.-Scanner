import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { IoMdArrowBack } from 'react-icons/io';
import { useQuestionnaire } from '../hooks/useQuestionnaire';
import styles from '../styles/QuestionnairePage.module.css';
import { LoadingSpinner } from '../components/loadingSpinner';
import ContinuationPrompt from '../components/ContinuationPrompt';


const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
const loadGoogleMapsScript = (callback) => {
  if (window.google && window.google.maps && window.google.maps.places) {
    callback();
    return;
  }
  const existingScript = document.getElementById('googleMapsScript');
  if (existingScript) {
    existingScript.addEventListener('load', callback);
    return;
  }
  const script = document.createElement('script');
  // Add a callback parameter to handle errors more gracefully
  script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places&callback=Function.prototype`;
  script.id = 'googleMapsScript';
  script.async = true;
  script.defer = true;
  document.body.appendChild(script);
  script.onload = () => callback();
};

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
  const [sliderRangeValue, setSliderRangeValue] = useState([0, 100]);
  const [listInputValues, setListInputValues] = useState(['']);
  const [googleMapsReady, setGoogleMapsReady] = useState(false);

  // Refs for autocomplete inputs
  const autocompleteRefs = useRef([]);
  
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  useEffect(() => {
    if (currentQuestion && currentQuestion.type === 'list-input') {
      loadGoogleMapsScript(() => {
        setGoogleMapsReady(true);
      });
    }
  }, [currentQuestion]);

  // Initialize Autocomplete for list inputs
  useEffect(() => {
    if (googleMapsReady && currentQuestion && currentQuestion.type === 'list-input') {
      listInputValues.forEach((_, index) => {
        if (autocompleteRefs.current[index] && !autocompleteRefs.current[index].__googleAutocompleteInitialized) {
          const autocomplete = new window.google.maps.places.Autocomplete(
            autocompleteRefs.current[index],
            { types: ['geocode', 'establishment'], componentRestrictions: { country: 'IL' } }
          );
          autocomplete.addListener('place_changed', () => {
            const place = autocomplete.getPlace();
            if (place && place.formatted_address) {
              const newListValues = [...listInputValues];
              newListValues[index] = place.formatted_address;
              setListInputValues(newListValues);
            } else if (place && place.name) {
                const newListValues = [...listInputValues];
                newListValues[index] = place.name;
                setListInputValues(newListValues);
            }
          });
          autocompleteRefs.current[index].__googleAutocompleteInitialized = true;
        }
      });
    }
    // Cleanup function to remove __googleAutocompleteInitialized flag if component unmounts or inputs change
    return () => {
        autocompleteRefs.current.forEach(ref => {
            if (ref) delete ref.__googleAutocompleteInitialized;
        });
    };
  }, [googleMapsReady, currentQuestion?.type, listInputValues.length]);

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
      setSelectedOptions([]);
      if (currentQuestion.type === 'slider' && currentQuestion.config) {
        const min = currentQuestion.config.min !== undefined ? currentQuestion.config.min : 0;
        const max = currentQuestion.config.max !== undefined ? currentQuestion.config.max : 100;
        setSliderRangeValue([min, max]);
      }
      if (currentQuestion.type === 'list-input') {
        setListInputValues(['']);
        // Ensure refs array is ready for the inputs
        autocompleteRefs.current = listInputValues.map(
            (_, i) => autocompleteRefs.current[i] || React.createRef()
        );
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

  useEffect(() => {
    if (currentQuestion) {
      setSelectedOptions([]);
    }
  }, [currentQuestion]);
  
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
  
  const handleSliderRangeChange = (index, value) => {
    setSliderRangeValue(prevRange => {
      const newRange = [...prevRange];
      newRange[index] = parseInt(value, 10);

      if (index === 0 && newRange[0] > newRange[1]) {
        newRange[1] = newRange[0];
      } else if (index === 1 && newRange[1] < newRange[0]) {
        newRange[0] = newRange[1];
      }
      return newRange;
    });
  };

  const handleListInputChange = (index, event) => {
    const newListValues = [...listInputValues];
    newListValues[index] = event.target.value;
    setListInputValues(newListValues);
    // If Google Autocomplete manually updates the input, this might be redundant
    // but good for direct typing.
  };

  const handleAddListInput = () => {
    if (listInputValues.length < 5) {
      setListInputValues([...listInputValues, '']);
      // Prepare ref for the new input
       autocompleteRefs.current = [...listInputValues, ''].map(
            (_, i) => autocompleteRefs.current[i] || React.createRef()
        );
    }
  };

  const handleRemoveListInput = (index) => {
    const newListValues = [...listInputValues];
    newListValues.splice(index, 1);
    setListInputValues(newListValues);
    // Adjust refs array
    autocompleteRefs.current.splice(index, 1);
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
        if (sliderRangeValue[0] > sliderRangeValue[1]) {
          setSubmissionError("Minimum range value cannot be greater than maximum range value.");
          return;
        }
        currentAnswer = JSON.stringify(sliderRangeValue);
        break;
      case 'list-input':
        const filteredListInputs = listInputValues.map(item => item.trim()).filter(item => item !== '');
        if (filteredListInputs.length === 0) {
          setSubmissionError("Please add at least one item to the list or skip.");
          return;
        }
        currentAnswer = JSON.stringify(filteredListInputs);
        break;
      default:
        console.warn("Unsupported question type for goToNextQuestion:", currentQuestion.type);
        return;
    }
    answerQuestion(currentQuestion.id, currentAnswer);
    if (currentQuestion.type === 'list-input') {
        setListInputValues(['']); 
        autocompleteRefs.current = [React.createRef()]; // Reset refs for next list-input q
    }
    setSelectedOptions([]);
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

  let showNextButton = currentQuestion.type !== 'single-choice' && currentQuestion.display_type !== 'continuation_page';
  let nextButtonEnabled = true;

  if (currentQuestion.type === 'multiple-choice' && selectedOptions.length === 0) {
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
            <div className={styles.sliderGroup}>
              <label htmlFor="minRange" className={styles.sliderLabel}>Minimum: {sliderRangeValue[0]} {sliderConfig.unit}</label>
              <input 
                type="range"
                id="minRange"
                min={sliderConfig.min} 
                max={sliderConfig.max} 
                step={sliderConfig.step} 
                value={sliderRangeValue[0]}
                onChange={(e) => handleSliderRangeChange(0, e.target.value)}
                className={styles.sliderInput}
                aria-label={`Minimum range value, current value ${sliderRangeValue[0]}`}
              />
            </div>
            <div className={styles.sliderGroup}>
              <label htmlFor="maxRange" className={styles.sliderLabel}>Maximum: {sliderRangeValue[1]} {sliderConfig.unit}</label>
              <input 
                type="range"
                id="maxRange"
                min={sliderConfig.min} 
                max={sliderConfig.max} 
                step={sliderConfig.step} 
                value={sliderRangeValue[1]}
                onChange={(e) => handleSliderRangeChange(1, e.target.value)}
                className={styles.sliderInput}
                aria-label={`Maximum range value, current value ${sliderRangeValue[1]}`}
              />
            </div>
            <div className={styles.sliderValueDisplay}>
              Range: {sliderRangeValue[0]} {sliderConfig.unit} - {sliderRangeValue[1]} {sliderConfig.unit}
            </div>
          </div>
        )}

        {currentQuestion.type === 'list-input' && (
          <div className={styles.listInputContainer}>
            {listInputValues.map((value, index) => (
              <div key={index} className={styles.listItem}>
                <input
                  type="text"
                  ref={el => autocompleteRefs.current[index] = el} // Assign ref
                  value={value} // Controlled component
                  onChange={(e) => handleListInputChange(index, e)}
                  placeholder={index === 0 ? 'eg. your office, university...' : ''}
                  className={styles.listInput}
                  disabled={!googleMapsReady && currentQuestion.type === 'list-input'} // Disable if maps not ready
                />
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
                disabled={!googleMapsReady && currentQuestion.type === 'list-input'}
              >
                + Add Item
              </button>
            )}
            {!googleMapsReady && currentQuestion.type === 'list-input' && <p className={styles.mapsLoadingText}>Loading Google Maps...</p>}
          </div>
        )}
      </div>
        
      {showNextButton && ( 
        <button
          className={styles.nextButton}
          onClick={() => goToNextQuestion()}
          disabled={!nextButtonEnabled || submissionLoading || (!googleMapsReady && currentQuestion.type === 'list-input')}
        >
          {submissionLoading ? 'Submitting...' : (currentQuestionIndex < totalQuestions - 1 || currentQuestion.display_type === 'continuation_page' ? 'Next Question' : 'Finish')}
        </button>
      )}
      
      {!(currentQuestionIndex >= totalQuestions - 1 && totalQuestions > 0) && currentQuestion.type !== 'single-choice' && (
          <button 
            className={styles.skipLink} 
            onClick={() => goToNextQuestion(true)}
            disabled={!googleMapsReady && currentQuestion.type === 'list-input'} // Also disable skip if maps not ready for list-input
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

