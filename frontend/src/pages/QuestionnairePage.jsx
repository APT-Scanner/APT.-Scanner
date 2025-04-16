import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { IoMdArrowBack } from 'react-icons/io';
import { useQuestions } from '../hooks/useQuestion'; 
import { useAuth } from '../hooks/useAuth';
import styles from '../styles/QuestionnairePage.module.css';

const IMPORTANCE_LEVELS = ['A little', 'Somewhat', 'Very'];
const BACKEND_URL = 'http://localhost:8000/api/v1';

const QuestionnairePage = () => {
    const navigate = useNavigate();
    const { questions, loading: questionsLoading, error: questionsError } = useQuestions();
    const { idToken } = useAuth();
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState({});
    const [submissionLoading, setSubmissionLoading] = useState(false);
    const [submissionError, setSubmissionError] = useState(null);
    const currentQuestion = questions && questions.length > 0 && currentQuestionIndex < questions.length
                            ? questions[currentQuestionIndex]
                            : null;
    const totalQuestions = questions ? questions.length : 0;
    const currentAnswerData = currentQuestion ? answers[currentQuestion.id] : {};
    const selectedOption = currentAnswerData?.option;
    const selectedImportance = currentAnswerData?.importance;

    const handleOptionSelect = (optionValue) => {
        if (!currentQuestion) return;

        const questionId = currentQuestion.id;
        const currentType = currentQuestion.type;

        setAnswers(prev => {
            const previousAnswer = prev[questionId] || {};
            let newOptionValue;

            if (currentType === 'multiple-choice') {
                const currentSelected = Array.isArray(previousAnswer.option) ? previousAnswer.option : [];
                if (currentSelected.includes(optionValue)) {
                    // Deselect: remove the option
                    newOptionValue = currentSelected.filter(item => item !== optionValue);
                } else {
                    // Select: add the option
                    newOptionValue = [...currentSelected, optionValue];
                }
            } else {
                newOptionValue = optionValue;
            }

            return {
                ...prev,
                [questionId]: {
                    ...previousAnswer,
                    option: newOptionValue,
                }
            };
        });
    };

    const handleImportanceSelect = (level) => {
        if (!currentQuestion) return;
        const questionId = currentQuestion.id;
        setAnswers(prev => ({
            ...prev,
            [questionId]: {
                ...(prev[questionId] || {}),
                importance: level,
            }
        }));
    };

     const goToNextQuestion = (isSkipping = false) => {
         if (currentQuestionIndex < totalQuestions - 1) {
             setCurrentQuestionIndex(prevIndex => prevIndex + 1);
         } else {
             handleSubmitAnswers();
         }
     };

      const goToPreviousQuestion = () => {
          if (currentQuestionIndex > 0) {
              setCurrentQuestionIndex(prevIndex => prevIndex - 1);
          } else {
              navigate('/getstarted');
          }
      };

     const handleSubmitAnswers = async () => {
          if (submissionLoading) return;
          setSubmissionLoading(true);
          setSubmissionError(null);
          console.log("Submitting answers:", answers);

          if (!idToken) {
              setSubmissionError("Authentication token is missing.");
              setSubmissionLoading(false);
              return;
          }

          try {
              const response = await fetch(`${BACKEND_URL}/answers`, {
                  method: 'POST',
                  headers: {
                      'Authorization': `Bearer ${idToken}`,
                      'Content-Type': 'application/json',
                  },
                  body: JSON.stringify({ answers: answers }),
              });

              if (!response.ok) {
                  const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                  throw new Error(errorData.detail || `Failed to submit answers: ${response.status}`);
              }

              const result = await response.json();
              console.log("Submission successful:", result);
              navigate('/home'); 

          } catch (error) {
              console.error("Failed to submit answers:", error);
              setSubmissionError(error.message || "An unknown error occurred.");
          } finally {
              setSubmissionLoading(false);
          }
      };


    const renderAnswerOptions = () => {
        if (!currentQuestion) return null;

        const { type, options = [], config = {} } = currentQuestion;

        switch (type) {
            case 'single-choice':
                return options.map((option, index) => (
                    <button
                        key={option + index}
                        role="radio"
                        aria-checked={selectedOption === option}
                        className={`${styles.optionButton} ${selectedOption === option ? styles.selected : ''}`}
                        onClick={() => handleOptionSelect(option)}
                    >
                        <span className={styles.radioCircle} aria-hidden="true"></span>
                        {option}
                    </button>
                ));

            case 'multiple-choice':
                const currentSelections = Array.isArray(selectedOption) ? selectedOption : [];
                return options.map((option, index) => (
                     <button
                         key={option + index}
                         role="checkbox"
                         aria-checked={currentSelections.includes(option)}
                         className={`${styles.optionButton} ${currentSelections.includes(option) ? styles.selected : ''} ${styles.checkbox}`}
                         onClick={() => handleOptionSelect(option)} 
                     >
                         <span className={styles.checkboxSquare} aria-hidden="true">
                              {currentSelections.includes(option) && <span className={styles.checkmark}>✓</span>}
                         </span>
                         {option}
                     </button>
                 ));

             case 'slider':
                 const { min = 0, max = 120, step = 1, unit = '' } = config;
                 const currentValue = typeof selectedOption === 'number' ? selectedOption : Math.round((min + max) / 2) ; 
                 return (
                     <div className={styles.sliderContainer}>
                         <input
                             type="range"
                             min={min}
                             max={max}
                             step={step}
                             value={currentValue}
                             onChange={(e) => handleOptionSelect(Number(e.target.value))} 
                             className={styles.sliderInput}
                         />
                         <div className={styles.sliderValueDisplay}>
                             {currentValue} {unit}
                         </div>
                     </div>
                 );

            case 'importance':
                 return null; 

            default:
                console.warn(`Unsupported question type: ${type}`);
                return <div>Unsupported question type: {type}</div>;
        }
    };

    if (questionsLoading) return <div className={styles.message}>Loading questions...</div>;
    if (questionsError) return <div className={`${styles.message} ${styles.error}`}>Error: {questionsError}</div>;
    if (!currentQuestion && !questionsLoading) return <div className={styles.message}>No questions found or error displaying question. <button onClick={() => navigate('/home')}>Go Home</button></div>;


    return (
        <div className={styles.pageContainer}>
            <div className={styles.header}>
                <button onClick={goToPreviousQuestion} className={styles.backButton} aria-label="Go back">
                    <IoMdArrowBack size={24} />
                </button>
                {totalQuestions > 0 && (
                    <div className={styles.progressBarContainer} aria-label={`Question ${currentQuestionIndex + 1} of ${totalQuestions}`}>
                        {Array.from({ length: totalQuestions }).map((_, index) => (
                            <div
                                key={index}
                                className={`${styles.progressDot} ${index <= currentQuestionIndex ? styles.active : ''}`}
                            />
                        ))}
                    </div>
                )}
                <span className={styles.progressText} aria-hidden="true">
                    {currentQuestionIndex + 1} of {totalQuestions}
                </span>
            </div>

            <div className={styles.questionCard}>
                <p id="question-text" className={styles.questionText}>{currentQuestion.text}</p>
            </div>

            <div className={styles.optionsContainer} role="group" aria-labelledby="question-text">
                 {renderAnswerOptions()}
            </div>

            {['single-choice', 'multiple-choice', 'importance'].includes(currentQuestion.type) && (
                 <div className={styles.importanceContainer}>
                     <h2 id="importance-label" className={styles.importanceTitle}>Importance</h2>
                     <div className={styles.importanceButtons} role="group" aria-labelledby="importance-label">
                         {(currentQuestion.type === 'importance' ? currentQuestion.options : IMPORTANCE_LEVELS).map((level) => (
                             <button
                                 key={level}
                                 className={`${styles.importanceButton} ${selectedImportance === level ? styles.selected : ''}`}
                                 onClick={() => handleImportanceSelect(level)}
                                 aria-pressed={selectedImportance === level}
                             >
                                 {level}
                             </button>
                         ))}
                     </div>
                 </div>
            )}

            {(selectedOption || currentQuestion.type === 'importance') && (selectedImportance !== undefined || !['single-choice', 'multiple-choice', 'importance'].includes(currentQuestion.type)) && ( 
                <button
                    className={styles.nextButton}
                    onClick={() => goToNextQuestion()}
                    disabled={submissionLoading}
                >
                    {submissionLoading ? 'Submitting...' : (currentQuestionIndex < totalQuestions - 1 ? 'Next Question' : 'Finish')}
                </button>
            )}

            <button className={styles.skipLink} onClick={() => goToNextQuestion(true)}>
                SKIP TO NEXT QUESTION &gt;
            </button>

            {submissionError && <p className={`${styles.message} ${styles.error}`}>{submissionError}</p>}
        </div>
    );
};

export default QuestionnairePage;

