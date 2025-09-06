import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';
import { CONTINUATION_PROMPT_ID } from '../config/constants';
import API_BASE from '../config/api.js';

const DEBUG = true;

const CONTINUATION_PROMPT_QUESTION = {
  id: CONTINUATION_PROMPT_ID,
  text: "You've completed the initial questions! Would you like to continue with more questions to help us better understand your needs, or submit your responses now?",
  type: "single-choice",
  options: ["Continue with more questions", "Submit my responses now"],
  category: "System",
  display_type: "continuation_page"  // Special flag for frontend to render this differently
};

/**
 * Custom hook for managing questionnaire state and API interactions.
 * Supports caching, offline mode, and error recovery.
 */
export const useQuestionnaire = () => {

  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStageTotalQuestions, setCurrentStageTotalQuestions] = useState(0);
  const [currentStageAnsweredQuestions, setCurrentStageAnsweredQuestions] = useState(0);
  const [answeredQuestions, setAnsweredQuestions] = useState([]);
  const [isOffline, setIsOffline] = useState(false);
  
  // Track if continuation prompt has been shown
  const continuationPromptShown = useRef(false);
  
  const { idToken, user, loading: authLoading } = useAuth();

  // User-specific localStorage key prefixes
  const getUserPrefix = useCallback(() => {
    return user?.uid ? `user-${user.uid}-` : '';
  }, [user]);

  // Helper functions for localStorage operations with user-specific keys
  const getLocalStorageKey = useCallback((key) => {
    return `${getUserPrefix()}questionnaire-${key}`;
  }, [getUserPrefix]);

  const saveToLocalStorage = useCallback((key, data) => {
    if (!user?.uid) return; // Don't save if no user is logged in
    
    try {
      localStorage.setItem(getLocalStorageKey(key), JSON.stringify(data));
    } catch (err) {
      console.error(`Error saving to localStorage (${key}):`, err);
    }
  }, [user, getLocalStorageKey]);

  const getFromLocalStorage = useCallback((key) => {
    if (!user?.uid) return null;
    
    try {
      const item = localStorage.getItem(getLocalStorageKey(key));
      return item ? JSON.parse(item) : null;
    } catch (err) {
      console.error(`Error loading from localStorage (${key}):`, err);
      return null;
    }
  }, [user, getLocalStorageKey]);

  const removeFromLocalStorage = useCallback((key) => {
    if (!user?.uid) return;
    
    try {
      localStorage.removeItem(getLocalStorageKey(key));
    } catch (err) {
      console.error(`Error removing from localStorage (${key}):`, err);
    }
  }, [user, getLocalStorageKey]);

  /**
   * Watch for online/offline status
   */
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  /**
   * Load cached answers from localStorage when user changes
   */
  useEffect(() => {
    if (user?.uid) {
      setAnswers({});
      setAnsweredQuestions([]);
      setProgress(0);
      
      // Load cached data for the current user
      const cachedAnswers = getFromLocalStorage('answers');
      if (cachedAnswers) {
        setAnswers(cachedAnswers);
      }
      
      const cachedAnsweredQuestions = getFromLocalStorage('answered-questions');
      if (cachedAnsweredQuestions) {
        setAnsweredQuestions(cachedAnsweredQuestions);
        setProgress(cachedAnsweredQuestions.length);
      }
      
      // Load continuation prompt state
      const cachedContinuationShown = getFromLocalStorage('continuation-shown');
      if (cachedContinuationShown) {
        continuationPromptShown.current = cachedContinuationShown;
      }
    }
  }, [user, getFromLocalStorage]);

  /**
   * Start or resume the questionnaire
   */
  const startQuestionnaire = useCallback(async () => {
    if (authLoading || !idToken) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // If offline, use cached data if available
      if (isOffline) {
        setError('Working in offline mode, cached data is being used');
        setLoading(false);
        return;
      }
      
      if (DEBUG) console.log("Starting/resuming questionnaire");
      
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/current`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to start questionnaire: ${response.status}`);
      }

      const data = await response.json();
      
      if (DEBUG) console.log("Questionnaire started, data:", data);
      
      // If we don't have any answers cached (e.g., after reset), sync with backend
      if (Object.keys(answers).length === 0) {
        try {
          if (DEBUG) console.log("No cached answers found, syncing with backend...");
          
          const responsesResponse = await fetch(`${API_BASE}/api/v1/questionnaire/responses`, {
            headers: {
              'Authorization': `Bearer ${idToken}`,
              'Content-Type': 'application/json'
            }
          });
          
          if (responsesResponse.ok) {
            const responsesData = await responsesResponse.json();
            const backendAnswers = responsesData.user_responses || {};
            const backendAnsweredQuestions = Object.keys(backendAnswers);
            
            if (Object.keys(backendAnswers).length > 0) {
              if (DEBUG) console.log(`Synced ${Object.keys(backendAnswers).length} answers from backend:`, backendAnswers);
              
              // Update frontend state with backend data
              setAnswers(backendAnswers);
              setAnsweredQuestions(backendAnsweredQuestions);
              
              // Cache the synced data
              saveToLocalStorage('answers', backendAnswers);
              saveToLocalStorage('answered-questions', backendAnsweredQuestions);
            } else {
              if (DEBUG) console.log("No existing answers found in backend");
            }
          } else {
            if (DEBUG) console.warn("Failed to sync answers from backend:", responsesResponse.status);
          }
        } catch (syncError) {
          console.warn("Error syncing answers from backend:", syncError);
          // Continue with normal flow even if sync fails
        }
      }
      
      // Check if we need to show a continuation prompt
      if (data.show_continuation_prompt) {
        if (DEBUG) console.log("Backend requested showing continuation prompt on start");
        // Show custom continuation prompt
        setCurrentQuestion(CONTINUATION_PROMPT_QUESTION);
        continuationPromptShown.current = true;
        saveToLocalStorage('continuation-shown', true);
      } else {
        // Normal flow 
        setCurrentQuestion(data.question);
      }
      
      setIsComplete(data.is_complete);
      setProgress(data.progress || 0);
      setCurrentStageTotalQuestions(data.current_stage_total_questions || 0);
      setCurrentStageAnsweredQuestions(data.current_stage_answered_questions || 0);
      
      // Cache the results
      if (data.is_complete) {
        setAnswers({});
        removeFromLocalStorage('answers');
        removeFromLocalStorage('answered-questions');
        removeFromLocalStorage('continuation-shown');
        continuationPromptShown.current = false;
      }
    } catch (err) {
      console.error('Error starting questionnaire:', err);
      setError(err.message || 'Failed to start the questionnaire.');
    } finally {
      setLoading(false);
    }
  }, [idToken, authLoading, isOffline, removeFromLocalStorage, saveToLocalStorage, answers]);
  
  /**
   * Initialize the questionnaire on component mount or when user changes
   */
  useEffect(() => {
    if (!authLoading && idToken && user?.uid) {
      startQuestionnaire();
    }
  }, [idToken, authLoading, startQuestionnaire, user]);

  const getNumberOfBasicQuestions = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/v1/questionnaire/basic-questions-count`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${idToken}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get the number of basic questions.');
    }

    return response.json();
  }, [idToken]);

  /**
   * Reset questionnaire state for fresh start
   */
  const resetQuestionnaireState = useCallback(() => {
    if (!user?.uid) return;
    
    try {
      // Clear localStorage cache
      removeFromLocalStorage('answers');
      removeFromLocalStorage('answered-questions');
      removeFromLocalStorage('continuation-shown');
      
      // Reset local state
      setAnswers({});
      setAnsweredQuestions([]);
      setProgress(0);
      setCurrentQuestion(null);
      setIsComplete(false);
      setIsSubmitted(false);
      continuationPromptShown.current = false;
      
      if (DEBUG) console.log('Reset questionnaire state for fresh start');
    } catch (error) {
      console.error('Error resetting questionnaire state:', error);
    }
  }, [user, removeFromLocalStorage]);

  /**
   * Fetch the next question with the current answers
   */
  const fetchNextQuestion = useCallback(async (newAnswers = {}) => {
    if (!idToken || !user?.uid) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Debug the new answers being submitted
      if (DEBUG) {
        console.log("fetchNextQuestion called with:", {
          newAnswers,
          questionId: Object.keys(newAnswers)[0],
          answerValue: Object.values(newAnswers)[0]
        });
      }
      
      // Process continuation prompt answers here to handle the user's choice locally
      const questionId = Object.keys(newAnswers)[0];
      if (questionId === CONTINUATION_PROMPT_ID) {
        const answer = newAnswers[questionId];
        if (DEBUG) console.log(`Processing continuation prompt answer: ${answer}`);
        
        // If user chose to submit, mark as complete
        if (answer === "Submit my responses now") {
          setIsComplete(true);
          setLoading(false);
          return;
        }
        // Otherwise, just continue to fetch the next question (we'll proceed below)
        continuationPromptShown.current = true;
        saveToLocalStorage('continuation-shown', true);
      }
      
      // Update local state immediately for better UX
      const updatedAnswers = { ...answers, ...newAnswers };
      setAnswers(updatedAnswers);
      
      // Cache answers in localStorage as backup
      saveToLocalStorage('answers', updatedAnswers);
      
      // If offline, use cached data
      if (isOffline) {
        setError('Working in offline mode. Your answers are saved locally and will sync when you reconnect.');
        setLoading(false);
        return;
      }
      
      // Send request to API
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/answers`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          answers: newAnswers
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to fetch next question: ${response.status}`);
      }

      // Process response
      const data = await response.json();
      
      // Add the current question ID to answered questions
      if (questionId && !answeredQuestions.includes(questionId)) {
        const updatedAnsweredQuestions = [...answeredQuestions, questionId];
        setAnsweredQuestions(updatedAnsweredQuestions);
        
        // Store answered questions in localStorage
        saveToLocalStorage('answered-questions', updatedAnsweredQuestions);
        
        // Calculate progress locally
        const newProgress = updatedAnsweredQuestions.length;
        setProgress(newProgress);
        
        if (DEBUG) {
          console.log("Updated progress:", {
            questionId,
            updatedAnsweredQuestions,
            newProgress,
            answer: newAnswers[questionId]
          });
        }
      }
      
      // Log the progress update
      if (DEBUG) {
        console.log("API Response:", {
          questionId: data.question?.id,
          apiProgress: data.progress,
          localProgress: answeredQuestions.length + 1,
          isComplete: data.is_complete,
          skippedQuestion: newAnswers[questionId] === null,
          showContinuationPrompt: data.show_continuation_prompt
        });
      }
      
      // Check if the backend wants us to show a continuation prompt
      if (data.show_continuation_prompt) {
        if (DEBUG) console.log("Backend requested showing continuation prompt after", answeredQuestions.length, "questions");
        // Show our custom continuation prompt
        setCurrentQuestion(CONTINUATION_PROMPT_QUESTION);
        continuationPromptShown.current = true;
        saveToLocalStorage('continuation-shown', true);
      } else {
        // Normal flow - show the question from the backend
        setCurrentQuestion(data.question);
        setIsComplete(data.is_complete);
        setProgress(data.progress || 0);
        setCurrentStageTotalQuestions(data.current_stage_total_questions || 0);
        setCurrentStageAnsweredQuestions(data.current_stage_answered_questions || 0);
      }
      
    } catch (err) {
      console.error('Error fetching next question:', err);
      setError(err.message || 'Failed to get the next question.');
    } finally {
      setLoading(false);
    }
  }, [idToken, user, answers, isOffline, answeredQuestions, saveToLocalStorage]);

  /**
   * Handle answering a question
   */
  const answerQuestion = useCallback((questionId, answer) => {

    if (!questionId) {
      if (DEBUG) console.warn("answerQuestion called with no questionId");
      return;
    }
    
    // Prevent answering with empty arrays 
    if (Array.isArray(answer) && answer.length === 0) {
      if (DEBUG) console.warn(`Prevented submission of empty array for question ${questionId}`);
      return;
    }
    
    if (DEBUG) console.log(`answerQuestion called: ${questionId} with answer:`, answer);
    
    // Create an object with the new answer
    const newAnswer = { [questionId]: answer };
    
    // Fetch the next question
    fetchNextQuestion(newAnswer);
  }, [fetchNextQuestion]);

  /**
   * Go back to the previous question
   */
  const goToPreviousQuestion = useCallback(async () => {
    if (!idToken || !user?.uid) return false;
    
    // Cannot go back if no questions were answered
    if (answeredQuestions.length === 0) {
      if (DEBUG) console.log("Cannot go back - no previous questions");
      return false;
    }
    
    try {
      setLoading(true);
      setError(null);

      // Request the previous question from backend
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/current/previous`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to get previous question: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.question) {
        setCurrentQuestion(data.question);
        setProgress(data.progress || 0);
        setCurrentStageAnsweredQuestions(data.current_stage_answered_questions || 0);
        setCurrentStageTotalQuestions(data.current_stage_total_questions || 0);
        setIsComplete(false);
        
        if (DEBUG) console.log("Successfully went back to previous question:", data.question.id);
        return true;
      }
      
      return false;
      
    } catch (err) {
      console.error('Error going to previous question:', err);
      setError(err.message || 'Failed to go back to previous question');
      return false;
    } finally {
      setLoading(false);
    }
  }, [idToken, user, answeredQuestions, saveToLocalStorage]);

  /**
   * Check if user can go back to previous question
   */
  const canGoBack = useCallback(() => {
    return answeredQuestions.length > 0 && currentQuestion?.id !== CONTINUATION_PROMPT_ID;
  }, [answeredQuestions, currentQuestion]);

  /**
   * Submit the completed questionnaire
   */
  const submitQuestionnaire = useCallback(async () => {
    if (!idToken || !user?.uid) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // If offline, queue submission for when back online
      if (isOffline) {
        saveToLocalStorage('pending-submit', true);
        setError('You are offline. Your questionnaire will be submitted when you reconnect.');
        setLoading(false);
        return;
      }
      
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to submit questionnaire: ${response.status}`);
      }

      // Successfully submitted
      setIsSubmitted(true);
      
      // Clear cache
      removeFromLocalStorage('answers');
      removeFromLocalStorage('answered-questions');
      removeFromLocalStorage('pending-submit');
      removeFromLocalStorage('continuation-shown');
      continuationPromptShown.current = false;
      
    } catch (err) {
      console.error('Error submitting questionnaire:', err);
      setError(err.message || 'Failed to submit your answers. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [idToken, user, isComplete, isOffline, saveToLocalStorage, removeFromLocalStorage]);

  /**
   * Check and handle pending submissions when coming back online
   */
  useEffect(() => {
    // If online and there's a pending submission
    if (!isOffline && isComplete && user?.uid && getFromLocalStorage('pending-submit') === true) {
      submitQuestionnaire();
    }
  }, [isOffline, isComplete, user, getFromLocalStorage, submitQuestionnaire]);

  /**
   * Retry after an error
   */
  const retry = useCallback(() => {
    if (isComplete) {
      submitQuestionnaire();
    } else {
      startQuestionnaire();
    }
  }, [isComplete, submitQuestionnaire, startQuestionnaire]);

  return {
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
    answerQuestion,
    submitQuestionnaire,
    retry,
    startQuestionnaire,
    getNumberOfBasicQuestions,
    goToPreviousQuestion,
    canGoBack,
    resetQuestionnaireState
  };
}; 