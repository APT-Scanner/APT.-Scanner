// frontend/src/hooks/useQuestionnaireStatus.js
import { useState, useEffect } from 'react';
import { useAuth } from './useAuth';
import { BACKEND_URL } from '../config/constants';

/**
 * Custom hook to check if the user has completed the questionnaire
 * @param {boolean} shouldCheck - Whether to automatically check status
 * @returns {Object} - { isCompleted, loading, error, checkStatus }
 */
export const useQuestionnaireStatus = (shouldCheck = true) => {
  const [isCompleted, setIsCompleted] = useState(false);
  const [loading, setLoading] = useState(shouldCheck);
  const [error, setError] = useState(null);
  const { idToken, user, loading: authLoading } = useAuth();

  const checkQuestionnaireStatus = async (userOverride = null) => {
    const targetUser = userOverride || user;
    const targetToken = userOverride ? await userOverride.getIdToken() : idToken;

    if (!targetUser?.uid || !targetToken) {
      throw new Error('User not authenticated');
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${BACKEND_URL}/questionnaire/status`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${targetToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch questionnaire status: ${response.status}`);
      }

      const data = await response.json();
      setIsCompleted(data.is_complete);
      return data.is_complete;
      
    } catch (err) {
      setError(err.message || 'Failed to check questionnaire status');
      setIsCompleted(false);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!shouldCheck || authLoading || !user?.uid || !idToken) {
      if (!shouldCheck) setLoading(false);
      return;
    }

    checkQuestionnaireStatus().catch(console.error);
  }, [idToken, user, authLoading, shouldCheck]);

  // Reset state when user logs out
  useEffect(() => {
    if (!user) {
      setIsCompleted(false);
      setError(null);
      setLoading(true);
    }
  }, [user]);

  return { isCompleted, loading, error, checkStatus: checkQuestionnaireStatus };
};
