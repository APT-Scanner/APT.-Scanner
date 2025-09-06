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
 * Supports caching, offline mode, error recovery, and race condition protection.
 * 
 * Race condition prevention mechanisms:
 * - Request versioning: Each async operation gets a unique requestId to ensure "latest wins"
 * - Loading reference count: Tracks multiple concurrent requests to prevent early loading=false
 * - AbortController: Cancels old requests when new ones start
 * - Functional state updates: Prevents stale closure issues in rapid interactions
 */
export const useQuestionnaire = () => {

  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loadingCount, setLoadingCount] = useState(0); // Reference count instead of boolean
  const [error, setError] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStageTotalQuestions, setCurrentStageTotalQuestions] = useState(0);
  const [currentStageAnsweredQuestions, setCurrentStageAnsweredQuestions] = useState(0);
  // eslint-disable-next-line no-unused-vars
  const [answeredQuestions, setAnsweredQuestions] = useState([]);
  const [isOffline, setIsOffline] = useState(false);
  
  // Derived loading state from reference count
  const loading = loadingCount > 0;
  
  // Track if continuation prompt has been shown
  const continuationPromptShown = useRef(false);
  
  // Request versioning to prevent race conditions ("latest wins")
  const startRequestIdRef = useRef(0);
  const fetchNextRequestIdRef = useRef(0);
  const goBackRequestIdRef = useRef(0);
  const submitRequestIdRef = useRef(0);
  
  // AbortController refs for canceling old requests
  const startAbortRef = useRef(null);
  const fetchNextAbortRef = useRef(null);
  const goBackAbortRef = useRef(null);
  const submitAbortRef = useRef(null);
  
  // Ref for answers to avoid dependency loops in startQuestionnaire
  const answersRef = useRef(answers);
  
  const { idToken, user, loading: authLoading } = useAuth();

  /**
   * Mirror answers state in ref to avoid dependency loops
   * startQuestionnaire should not depend on mutable answers state
   */
  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  /**
   * Helper to safely increment loading count
   */
  const incLoading = useCallback(() => {
    setLoadingCount(prev => prev + 1);
  }, []);

  /**
   * Helper to safely decrement loading count (min 0)
   */
  const decLoading = useCallback(() => {
    setLoadingCount(prev => Math.max(0, prev - 1));
  }, []);

  /**
   * Helper to abort and replace an AbortController
   */
  const replaceAbortController = useCallback((abortRef) => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    abortRef.current = new AbortController();
    return abortRef.current.signal;
  }, []);

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
   * Start or resume the questionnaire with race condition protection
   * - Uses requestId versioning to ensure only latest response updates state
   * - Uses loading reference count to handle concurrent requests properly  
   * - AbortController cancels previous requests
   * - Does not depend on mutable answers state to prevent re-runs
   */
  const startQuestionnaire = useCallback(async () => {
    if (authLoading || !idToken) return;
    
    // Generate requestId and setup abort controller
    const requestId = ++startRequestIdRef.current;
    const signal = replaceAbortController(startAbortRef);
    
    incLoading();
    setError(null);
    
    if (DEBUG) console.log(`🔄 Starting questionnaire (requestId: ${requestId})`);
    
    try {
      // If offline, use cached data if available
      if (isOffline) {
        // Check if this is still the latest request
        if (requestId !== startRequestIdRef.current) return;
        
        setError('Working in offline mode, cached data is being used');
        return;
      }
      
      if (DEBUG) console.log("Starting/resuming questionnaire");
      
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/current`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        signal
      });

      // Check if this is still the latest request after async operation
      if (requestId !== startRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale startQuestionnaire response (${requestId})`);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to start questionnaire: ${response.status}`);
      }

      const data = await response.json();
      
      // Check again after another async operation
      if (requestId !== startRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale startQuestionnaire data (${requestId})`);
        return;
      }
      
      if (DEBUG) console.log("Questionnaire started, data:", data);
      
      // If we don't have any answers cached (e.g., after reset), sync with backend
      // Use answersRef instead of answers state to avoid dependency issues
      if (Object.keys(answersRef.current).length === 0) {
        try {
          if (DEBUG) console.log("No cached answers found, syncing with backend...");
          
          const responsesResponse = await fetch(`${API_BASE}/api/v1/questionnaire/responses`, {
            headers: {
              'Authorization': `Bearer ${idToken}`,
              'Content-Type': 'application/json'
            },
            signal
          });
          
          // Check requestId after sync fetch
          if (requestId !== startRequestIdRef.current) {
            if (DEBUG) console.log(`🚫 Ignoring stale sync response (${requestId})`);
            return;
          }
          
          if (responsesResponse.ok) {
            const responsesData = await responsesResponse.json();
            
            // Final requestId check before applying sync data
            if (requestId !== startRequestIdRef.current) {
              if (DEBUG) console.log(`🚫 Ignoring stale sync data (${requestId})`);
              return;
            }
            
            const backendAnswers = responsesData.user_responses || {};
            const backendAnsweredQuestions = Object.keys(backendAnswers);
            
            if (Object.keys(backendAnswers).length > 0) {
              if (DEBUG) console.log(`Synced ${Object.keys(backendAnswers).length} answers from backend:`, backendAnswers);
              
              // Update frontend state with backend data
              setAnswers(backendAnswers);
              setAnsweredQuestions(backendAnsweredQuestions);
              setProgress(backendAnsweredQuestions.length);
              
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
          // Ignore aborted requests
          if (syncError.name === 'AbortError') {
            if (DEBUG) console.log(`🚫 Sync request aborted (${requestId})`);
            return;
          }
          console.warn("Error syncing answers from backend:", syncError);
          // Continue with normal flow even if sync fails
        }
      }
      
      // Final check before setting main response data
      if (requestId !== startRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale main response (${requestId})`);
        return;
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
      
      if (DEBUG) console.log(`✓ Successfully started questionnaire (${requestId})`);
      
    } catch (err) {
      // Ignore aborted requests
      if (err.name === 'AbortError') {
        if (DEBUG) console.log(`🚫 Start request aborted (${requestId})`);
        return;
      }
      
      // Only show error for latest request
      if (requestId === startRequestIdRef.current) {
        console.error('Error starting questionnaire:', err);
        setError(err.message || 'Failed to start the questionnaire.');
      }
    } finally {
      decLoading();
    }
  }, [idToken, authLoading, isOffline, removeFromLocalStorage, saveToLocalStorage, incLoading, decLoading, replaceAbortController]);
  
  /**
   * Initialize the questionnaire on component mount or when user changes
   * Only depends on stable identities to prevent re-runs from mutable state
   */
  useEffect(() => {
    if (!authLoading && idToken && user?.uid) {
      startQuestionnaire();
    }
  }, [idToken, authLoading, user?.uid, startQuestionnaire]);

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
   * Fetch the next question with race condition protection  
   * - Uses requestId versioning to ensure only latest response updates state
   * - Uses loading reference count for concurrent request handling
   * - AbortController cancels old requests
   * - Functional state updates prevent stale closure issues in rapid interactions
   */
  const fetchNextQuestion = useCallback(async (newAnswers = {}) => {
    if (!idToken || !user?.uid) return;
    
    // Generate requestId and setup abort controller
    const requestId = ++fetchNextRequestIdRef.current;
    const signal = replaceAbortController(fetchNextAbortRef);
    
    incLoading();
    setError(null);
    
    try {
      // Debug the new answers being submitted
      if (DEBUG) {
        console.log(`🔄 fetchNextQuestion called (requestId: ${requestId}):`, {
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
        
        // Check if still latest request
        if (requestId !== fetchNextRequestIdRef.current) {
          if (DEBUG) console.log(`🚫 Ignoring stale continuation prompt (${requestId})`);
          return;
        }
        
        // If user chose to submit, mark as complete
        if (answer === "Submit my responses now") {
          setIsComplete(true);
          return;
        }
        // Otherwise, just continue to fetch the next question (we'll proceed below)
        continuationPromptShown.current = true;
        saveToLocalStorage('continuation-shown', true);
      }
      
      // Update local state immediately for better UX using functional updates
      setAnswers(prev => {
        const updatedAnswers = { ...prev, ...newAnswers };
        // Cache answers in localStorage as backup
        saveToLocalStorage('answers', updatedAnswers);
        return updatedAnswers;
      });
      
      // If offline, use cached data
      if (isOffline) {
        // Check if still latest request
        if (requestId !== fetchNextRequestIdRef.current) return;
        
        setError('Working in offline mode. Your answers are saved locally and will sync when you reconnect.');
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
        signal
      });

      // Check if this is still the latest request after API call
      if (requestId !== fetchNextRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale fetchNext response (${requestId})`);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to fetch next question: ${response.status}`);
      }

      // Process response
      const data = await response.json();
      
      // Final check before processing response data
      if (requestId !== fetchNextRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale fetchNext data (${requestId})`);
        return;
      }
      
      // Add the current question ID to answered questions using functional update
      if (questionId) {
        setAnsweredQuestions(prev => {
          // Prevent duplicate additions and use fresh state
          if (prev.includes(questionId)) return prev;
          
          const updatedAnsweredQuestions = [...prev, questionId];
          
          // Store answered questions in localStorage
          saveToLocalStorage('answered-questions', updatedAnsweredQuestions);
          
          // Update progress based on fresh array length
          setProgress(updatedAnsweredQuestions.length);
          
          if (DEBUG) {
            console.log("Updated progress:", {
              questionId,
              updatedAnsweredQuestions,
              newProgress: updatedAnsweredQuestions.length,
              answer: newAnswers[questionId]
            });
          }
          
          return updatedAnsweredQuestions;
        });
      }
      
      // Log the progress update
      if (DEBUG) {
        console.log("API Response:", {
          questionId: data.question?.id,
          apiProgress: data.progress,
          isComplete: data.is_complete,
          skippedQuestion: newAnswers[questionId] === null,
          showContinuationPrompt: data.show_continuation_prompt
        });
      }
      
      // Check if the backend wants us to show a continuation prompt
      if (data.show_continuation_prompt) {
        if (DEBUG) console.log("Backend requested showing continuation prompt");
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
      
      if (DEBUG) console.log(`✓ Successfully fetched next question (${requestId})`);
      
    } catch (err) {
      // Ignore aborted requests
      if (err.name === 'AbortError') {
        if (DEBUG) console.log(`🚫 FetchNext request aborted (${requestId})`);
        return;
      }
      
      // Only show error for latest request
      if (requestId === fetchNextRequestIdRef.current) {
        console.error('Error fetching next question:', err);
        setError(err.message || 'Failed to get the next question.');
      }
    } finally {
      decLoading();
    }
  }, [idToken, user, isOffline, saveToLocalStorage, incLoading, decLoading, replaceAbortController]);

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
   * Go back to the previous question with race condition protection
   * - Uses requestId versioning to ensure only latest response updates state  
   * - Uses loading reference count for concurrent request handling
   * - AbortController cancels old requests
   * - Uses fresh answeredQuestions state to check if going back is possible
   */
  const goToPreviousQuestion = useCallback(async () => {
    if (!idToken || !user?.uid) return false;
    
    // Cannot go back if no questions were answered - use functional check for fresh state
    let canGoBackResult = false;
    setAnsweredQuestions(prev => {
      canGoBackResult = prev.length > 0;
      return prev; // No state change, just reading fresh value
    });
    
    if (!canGoBackResult) {
      if (DEBUG) console.log("Cannot go back - no previous questions");
      return false;
    }
    
    // Generate requestId and setup abort controller
    const requestId = ++goBackRequestIdRef.current;
    const signal = replaceAbortController(goBackAbortRef);
    
    incLoading();
    setError(null);
    
    if (DEBUG) console.log(`🔄 Going to previous question (requestId: ${requestId})`);
    
    try {
      // Request the previous question from backend
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/current/previous`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        signal
      });

      // Check if this is still the latest request after API call
      if (requestId !== goBackRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale goBack response (${requestId})`);
        return false;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to get previous question: ${response.status}`);
      }

      const data = await response.json();
      
      // Final check before processing response data
      if (requestId !== goBackRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale goBack data (${requestId})`);
        return false;
      }
      
      if (data.question) {
        setCurrentQuestion(data.question);
        setProgress(data.progress || 0);
        setCurrentStageAnsweredQuestions(data.current_stage_answered_questions || 0);
        setCurrentStageTotalQuestions(data.current_stage_total_questions || 0);
        setIsComplete(false);
        
        if (DEBUG) console.log(`✓ Successfully went back to previous question (${requestId}):`, data.question.id);
        return true;
      }
      
      return false;
      
    } catch (err) {
      // Ignore aborted requests
      if (err.name === 'AbortError') {
        if (DEBUG) console.log(`🚫 GoBack request aborted (${requestId})`);
        return false;
      }
      
      // Only show error for latest request
      if (requestId === goBackRequestIdRef.current) {
        console.error('Error going to previous question:', err);
        setError(err.message || 'Failed to go back to previous question');
      }
      return false;
    } finally {
      decLoading();
    }
  }, [idToken, user, incLoading, decLoading, replaceAbortController]);

  /**
   * Check if user can go back to previous question
   * Uses functional state check to get fresh values
   */
  const canGoBack = useCallback(() => {
    let result = false;
    setAnsweredQuestions(prev => {
      result = prev.length > 0;
      return prev; // No state change, just reading fresh value
    });
    return result && currentQuestion?.id !== CONTINUATION_PROMPT_ID;
  }, [currentQuestion]);

  /**
   * Submit the completed questionnaire with race condition protection
   * - Uses requestId versioning to ensure only latest response updates state
   * - Uses loading reference count for concurrent request handling
   * - AbortController cancels old requests  
   * - Handles offline queuing with proper state management
   */
  const submitQuestionnaire = useCallback(async () => {
    if (!idToken || !user?.uid) return;
    
    // Generate requestId and setup abort controller
    const requestId = ++submitRequestIdRef.current;
    const signal = replaceAbortController(submitAbortRef);
    
    incLoading();
    setError(null);
    
    if (DEBUG) console.log(`🔄 Submitting questionnaire (requestId: ${requestId})`);
    
    try {
      // If offline, queue submission for when back online
      if (isOffline) {
        // Check if still latest request
        if (requestId !== submitRequestIdRef.current) {
          if (DEBUG) console.log(`🚫 Ignoring stale offline submit (${requestId})`);
          return;
        }
        
        saveToLocalStorage('pending-submit', true);
        setError('You are offline. Your questionnaire will be submitted when you reconnect.');
        return;
      }
      
      const response = await fetch(`${API_BASE}/api/v1/questionnaire/`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        signal
      });

      // Check if this is still the latest request after API call
      if (requestId !== submitRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale submit response (${requestId})`);
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `HTTP error! status: ${response.status}` 
        }));
        throw new Error(errorData.detail || `Failed to submit questionnaire: ${response.status}`);
      }

      // Final check before processing success
      if (requestId !== submitRequestIdRef.current) {
        if (DEBUG) console.log(`🚫 Ignoring stale submit success (${requestId})`);
        return;
      }

      // Successfully submitted
      setIsSubmitted(true);
      
      // Clear cache
      removeFromLocalStorage('answers');
      removeFromLocalStorage('answered-questions');
      removeFromLocalStorage('pending-submit');
      removeFromLocalStorage('continuation-shown');
      continuationPromptShown.current = false;
      
      if (DEBUG) console.log(`✓ Successfully submitted questionnaire (${requestId})`);
      
    } catch (err) {
      // Ignore aborted requests
      if (err.name === 'AbortError') {
        if (DEBUG) console.log(`🚫 Submit request aborted (${requestId})`);
        return;
      }
      
      // Only show error for latest request
      if (requestId === submitRequestIdRef.current) {
        console.error('Error submitting questionnaire:', err);
        setError(err.message || 'Failed to submit your answers. Please try again.');
      }
    } finally {
      decLoading();
    }
  }, [idToken, user, isOffline, saveToLocalStorage, removeFromLocalStorage, incLoading, decLoading, replaceAbortController]);

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

  /**
   * Cleanup function to cancel pending operations on unmount
   */
  useEffect(() => {
    // Capture current ref values when effect runs
    const startAbort = startAbortRef.current;
    const fetchNextAbort = fetchNextAbortRef.current;
    const goBackAbort = goBackAbortRef.current;
    const submitAbort = submitAbortRef.current;
    
    return () => {
      // Cancel all pending requests on cleanup using captured values
      if (startAbort) startAbort.abort();
      if (fetchNextAbort) fetchNextAbort.abort();
      if (goBackAbort) goBackAbort.abort();
      if (submitAbort) submitAbort.abort();
    };
  }, []);

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