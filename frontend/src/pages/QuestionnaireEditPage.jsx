import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Edit3, Plus, CheckCircle, Circle, BarChart3 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import styles from '../styles/QuestionnaireEditPage.module.css';
import API_BASE from '../config/api.js';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

const QuestionnaireEditPage = () => {
    const navigate = useNavigate();
    const { idToken, user } = useAuth();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [questionsData, setQuestionsData] = useState(null);
    const [userResponses, setUserResponses] = useState({});

    // Fetch questionnaire data
    const fetchQuestionnaireData = useCallback(async () => {
        if (!idToken) return;

        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`${API_BASE}/api/v1/questionnaire/responses`, {
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch questionnaire data: ${response.status}`);
            }

            const data = await response.json();
            setQuestionsData(data);
            setUserResponses(data.user_responses || {});
        } catch (err) {
            console.error('Error fetching questionnaire data:', err);
            setError(err.message || 'Failed to load questionnaire data');
        } finally {
            setLoading(false);
        }
    }, [idToken]);

    useEffect(() => {
        fetchQuestionnaireData();
    }, [fetchQuestionnaireData]);

    const handleBack = () => navigate(-1);

    const handleAnswerMore = async () => {
        try {
            // Clear any cached questionnaire state to ensure fresh start
            if (user?.uid) {
                const userPrefix = `user-${user.uid}-`;
                
                // Clear localStorage cache for questionnaire using the same keys as useQuestionnaire hook
                try {
                    localStorage.removeItem(`${userPrefix}questionnaire-answers`);
                    localStorage.removeItem(`${userPrefix}questionnaire-answered-questions`);
                    localStorage.removeItem(`${userPrefix}questionnaire-continuation-shown`);
                    
                    console.log('Cleared questionnaire cache for fresh start');
                } catch (error) {
                    console.warn('Error clearing questionnaire cache:', error);
                }
            }
            
            // Reset the current question pointer on the backend
            if (idToken) {
                try {
                    const response = await fetch(`${API_BASE}/api/v1/questionnaire/reset-current-question`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${idToken}`,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    if (response.ok) {
                        console.log('Reset current question pointer on backend');
                    } else {
                        console.warn('Failed to reset current question pointer:', response.status);
                    }
                } catch (error) {
                    console.warn('Error resetting current question pointer:', error);
                }
            }
            
        } catch (error) {
            console.warn('Error in handleAnswerMore setup:', error);
        }
        
        // Navigate to regular questionnaire to answer remaining questions
        navigate('/questionnaire');
    };

    const handleEditAnswers = () => {
        // Navigate to detailed edit mode (we'll create this later)
        navigate('/questionnaire-edit-detailed');
    };



    if (loading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return (
            <div className={styles.pageContainer}>
                <div className={styles.header}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={24} />
                    </button>
                </div>
                <div className={styles.errorContainer}>
                    <p className={styles.errorMessage}>{error}</p>
                    <button onClick={fetchQuestionnaireData} className={styles.retryButton}>
                        <RefreshCw size={16} />
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    if (!questionsData) {
        return null;
    }

    const allQuestions = questionsData.all_questions || {};
    const answeredCount = Object.keys(userResponses).length;
    const totalQuestions = Object.keys(allQuestions).length;
    const completionPercentage = Math.round((answeredCount / totalQuestions) * 100);

    return (
        <div className={styles.pageContainer}>
            <div className={styles.header}>
                <button className={styles.backButton} onClick={handleBack}>
                    <ArrowLeft size={24} />
                </button>
            </div>

            <div className={styles.mainContent}>
                {/* Progress Overview */}
                <div className={styles.progressSection}>
                    <div className={styles.progressHeader}>
                        <BarChart3 size={28} className={styles.progressIcon} />
                        <h2>Your Questionnaire Status</h2>
                    </div>
                    
                    <div className={styles.progressStats}>
                        <div className={styles.progressBar}>
                            <div 
                                className={styles.progressFill}
                                style={{ width: `${completionPercentage}%` }}
                            ></div>
                        </div>
                        <div className={styles.progressText}>
                            {completionPercentage}% Complete
                        </div>
                    </div>

                    <div className={styles.statsGrid}>
                        <div className={styles.statCard}>
                            <CheckCircle size={24} className={styles.statIcon} />
                            <div className={styles.statInfo}>
                                <span className={styles.statNumber}>{answeredCount}</span>
                                <span className={styles.statLabel}>Questions Answered</span>
                            </div>
                        </div>
                        
                        <div className={styles.statCard}>
                            <Circle size={24} className={styles.statIcon} />
                            <div className={styles.statInfo}>
                                <span className={styles.statNumber}>{totalQuestions - answeredCount}</span>
                                <span className={styles.statLabel}>Questions Remaining</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className={styles.actionsSection}>
                    <h2>What would you like to do?</h2>
                    
                    <div className={styles.actionButtons}>
                        <button 
                            className={styles.actionButton}
                            onClick={handleAnswerMore}
                        >
                            <div className={styles.buttonIcon}>
                                <Plus size={32} />
                            </div>
                            <div className={styles.buttonContent}>
                                <h3>Answer Additional Questions</h3>
                                <p>Continue answering questions you haven't completed yet or skipped</p>
                                {totalQuestions - answeredCount > 0 && (
                                    <span className={styles.badge}>
                                        {totalQuestions - answeredCount} questions remaining
                                    </span>
                                )}
                            </div>
                        </button>

                        <button 
                            className={styles.actionButton}
                            onClick={handleEditAnswers}
                        >
                            <div className={styles.buttonIcon}>
                                <Edit3 size={32} />
                            </div>
                            <div className={styles.buttonContent}>
                                <p>Change or update answers you've already provided</p>
                                {answeredCount > 0 && (
                                    <span className={styles.badge}>
                                        {answeredCount} answers available for editing
                                    </span>
                                )}
                            </div>
                        </button>
                    </div>
                </div>

                {/* Completion Status */}
                {completionPercentage === 100 && (
                    <div className={styles.completionMessage}>
                        <CheckCircle size={24} className={styles.completionIcon} />
                        <span>Congratulations! You've completed all questionnaire questions</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default QuestionnaireEditPage;
