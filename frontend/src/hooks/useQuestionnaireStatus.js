// frontend/src/hooks/useQuestionnaireStatus.js
import { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

/**
 * Custom hook to check if the user has completed the questionnaire
 * @returns {Object} - { isCompleted, loading, error }
 */
export const useQuestionnaireStatus = () => {
  const [isCompleted, setIsCompleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { idToken, user, loading: authLoading } = useAuth();

  useEffect(() => {
    const checkQuestionnaireStatus = async () => {
      if (authLoading || !idToken || !user?.uid) {
        return;
      }

      try {
        console.log("Checking questionnaire status for user:", user.uid);
        setLoading(true);
        const response = await fetch(`${BACKEND_URL}/questionnaire/status`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${idToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch questionnaire status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Questionnaire status response:", data);
        setIsCompleted(data.is_complete);
      } catch (err) {
        console.error('Error checking questionnaire status:', err);
        setError(err.message || 'Failed to check questionnaire status');
        // Set completion to false on error to be safe
        setIsCompleted(false);
      } finally {
        setLoading(false);
      }
    };

    checkQuestionnaireStatus();
  }, [idToken, user, authLoading]);

  return { isCompleted, loading, error };
};
