import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Edit, Check, X, Save } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import styles from '../styles/QuestionnaireEditDetailedPage.module.css';
import API_BASE from '../config/api.js';

const QuestionnaireEditDetailedPage = () => {
    const navigate = useNavigate();
    const { idToken } = useAuth();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [questionsData, setQuestionsData] = useState(null);
    const [userResponses, setUserResponses] = useState({});
    const [editingQuestion, setEditingQuestion] = useState(null);
    const [tempAnswer, setTempAnswer] = useState('');
    const [saving, setSaving] = useState(false);

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
            console.log(`Fetched questionnaire data: ${Object.keys(data.user_responses || {}).length} user responses`);
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

    const startEditing = (questionId, currentAnswer) => {
        setEditingQuestion(questionId);
        setTempAnswer(currentAnswer || '');
    };

    const cancelEditing = () => {
        setEditingQuestion(null);
        setTempAnswer('');
    };

    const saveAnswer = async (questionId) => {
        try {
            setSaving(true);

            // Include all existing answers plus the updated one to prevent data loss
            const updatedAnswers = {
                ...userResponses,
                [questionId]: tempAnswer
            };

            console.log(`Saving answers for question ${questionId}. Total answers being sent: ${Object.keys(updatedAnswers).length}`);

            const response = await fetch(`${API_BASE}/api/v1/questionnaire/responses`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answers: updatedAnswers
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Failed to save answer' }));
                throw new Error(errorData.detail || 'Failed to save answer');
            }

            const responseData = await response.json();
            console.log(`Save successful for question ${questionId}:`, responseData);

            // Update local state
            setUserResponses(updatedAnswers);

            // Clear editing state
            setEditingQuestion(null);
            setTempAnswer('');

            // Optionally refresh data from server to ensure consistency
            // This ensures we have the latest server state
            setTimeout(() => {
                fetchQuestionnaireData();
            }, 500);
        } catch (err) {
            console.error('Error saving answer:', err);
            setError('Failed to save answer');
        } finally {
            setSaving(false);
        }
    };

    // Helper function to format POI (Points of Interest) answers
    const formatPOIAnswer = (answer) => {
        try {
            // Handle null/undefined/empty cases
            if (!answer || answer === '' || answer === 'null' || answer === 'undefined') {
                return 'No locations selected';
            }
            
            let pois = answer;
            
            // Parse if it's a JSON string
            if (typeof answer === 'string' && (answer.startsWith('[') || answer.startsWith('{'))) {
                try {
                    pois = JSON.parse(answer);
                } catch {
                    console.warn('Failed to parse POI JSON string:', answer);
                    return answer; // Return original if parsing fails
                }
            }
            
            // If it's an array of POI objects, extract location names
            if (Array.isArray(pois)) {
                if (pois.length === 0) {
                    return 'No locations selected';
                }
                
                const locationNames = pois.map((poi, index) => {
                    if (typeof poi === 'object' && poi !== null) {
                        // Extract location name from various possible fields
                        const locationName = poi.description || poi.name || poi.formatted_address || poi.place_id;
                        if (locationName) {
                            return locationName;
                        }
                        return `Location ${index + 1}`;
                    }
                    return poi || `Location ${index + 1}`;
                }).filter(name => name); // Remove any empty names
                
                return locationNames.length > 0 ? locationNames.join(', ') : 'No valid locations';
            }
            
            // If it's a single POI object
            if (typeof pois === 'object' && pois !== null) {
                const locationName = pois.description || pois.name || pois.formatted_address || pois.place_id;
                return locationName || 'Unknown Location';
            }
            
            // If it's a plain string that's not JSON, return as-is
            if (typeof pois === 'string') {
                return pois;
            }
            
            return answer || 'No location data';
        } catch (error) {
            console.error('Error formatting POI answer:', error, 'Original answer:', answer);
            return typeof answer === 'string' ? answer : 'Error displaying locations';
        }
    };

    // Helper function to format answer display
    const formatAnswerDisplay = (questionId, answer) => {
        // Special handling for points of interest question
        if (questionId === 'points_of_interest') {
            return formatPOIAnswer(answer);
        }
        
        // Handle arrays and JSON strings for other questions
        if (typeof answer === 'string' && answer.startsWith('[')) {
            try {
                return JSON.parse(answer).join(', ');
            } catch {
                return answer;
            }
        }
        
        if (Array.isArray(answer)) {
            return answer.join(', ');
        }
        
        return answer;
    };

    const renderQuestionAnswer = (question) => {
        const questionId = question.id;
        const currentAnswer = userResponses[questionId];
        const isEditing = editingQuestion === questionId;

        if (isEditing) {
            return (
                <div className={styles.editingContainer}>
                    {question.type === 'single-choice' && (
                        <div className={styles.optionsContainer}>
                            {question.options?.map((option, index) => (
                                <label key={index} className={styles.optionLabel}>
                                    <input
                                        type="radio"
                                        name={questionId}
                                        value={option}
                                        checked={tempAnswer === option}
                                        onChange={(e) => setTempAnswer(e.target.value)}
                                    />
                                    <span>{option}</span>
                                </label>
                            ))}
                        </div>
                    )}
                    
                    {question.type === 'multiple-choice' && (
                        <div className={styles.optionsContainer}>
                            {question.options?.map((option, index) => {
                                const selectedOptions = Array.isArray(tempAnswer) ? tempAnswer : 
                                    (tempAnswer && tempAnswer.startsWith('[') ? JSON.parse(tempAnswer) : []);
                                return (
                                    <label key={index} className={styles.optionLabel}>
                                        <input
                                            type="checkbox"
                                            value={option}
                                            checked={selectedOptions.includes(option)}
                                            onChange={(e) => {
                                                const current = Array.isArray(tempAnswer) ? tempAnswer : 
                                                    (tempAnswer && tempAnswer.startsWith('[') ? JSON.parse(tempAnswer) : []);
                                                if (e.target.checked) {
                                                    setTempAnswer(JSON.stringify([...current, option]));
                                                } else {
                                                    setTempAnswer(JSON.stringify(current.filter(o => o !== option)));
                                                }
                                            }}
                                        />
                                        <span>{option}</span>
                                    </label>
                                );
                            })}
                        </div>
                    )}

                    {question.type === 'text' && (
                        <input
                            type="text"
                            value={tempAnswer}
                            onChange={(e) => setTempAnswer(e.target.value)}
                            className={styles.textInput}
                            placeholder="Enter your answer..."
                        />
                    )}

                    {question.type === 'slider' && (
                        <div className={styles.sliderContainer}>
                            <span>Budget Range: {question.config?.min} - {question.config?.max} {question.config?.unit}</span>
                            <input
                                type="text"
                                value={tempAnswer}
                                onChange={(e) => setTempAnswer(e.target.value)}
                                className={styles.textInput}
                                placeholder="Enter range as [minimum, maximum]"
                            />
                        </div>
                    )}

                    <div className={styles.editActions}>
                        <button 
                            onClick={() => saveAnswer(questionId)}
                            disabled={saving}
                            className={styles.saveButton}
                        >
                            <Check size={16} />
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                        <button 
                            onClick={cancelEditing}
                            className={styles.cancelButton}
                        >
                            <X size={16} />
                            Cancel
                        </button>
                    </div>
                </div>
            );
        }

        // Display mode
        return (
            <div className={styles.answerContainer}>
                <div className={styles.answerDisplay}>
                    {currentAnswer ? (
                        <span className={styles.answer}>
                            {formatAnswerDisplay(questionId, currentAnswer)}
                        </span>
                    ) : (
                        <span className={styles.noAnswer}>Not answered</span>
                    )}
                </div>
                <button 
                    onClick={() => startEditing(questionId, currentAnswer)}
                    className={styles.editButton}
                >
                    <Edit size={16} />
                    Edit
                </button>
            </div>
        );
    };

    if (loading) {
        return (
            <div className={styles.pageContainer}>
                <div className={styles.header}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={24} />
                    </button>
                    <h1>Edit Answers</h1>
                </div>
                <div className={styles.loadingContainer}>
                    <RefreshCw size={48} className={styles.spinner} />
                    <p>Loading answers...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={styles.pageContainer}>
                <div className={styles.header}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={24} />
                    </button>
                    <h1>Edit Answers</h1>
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
    
    // Filter only answered questions
    const answeredQuestions = Object.entries(allQuestions).filter(([questionId]) => 
        userResponses[questionId] !== undefined && userResponses[questionId] !== null
    );

    if (answeredQuestions.length === 0) {
        return (
            <div className={styles.pageContainer}>
                <div className={styles.header}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={24} />
                    </button>
                    <h1>Edit Answers</h1>
                </div>
                <div className={styles.emptyContainer}>
                    <Save size={48} className={styles.emptyIcon} />
                    <h2>No answers to edit</h2>
                    <p>You haven't answered any questions yet. Start answering the questionnaire to be able to edit answers.</p>
                    <button 
                        onClick={() => navigate('/questionnaire')}
                        className={styles.startButton}
                    >
                        Start answering questions
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.pageContainer}>
            <div className={styles.header}>
                <button className={styles.backButton} onClick={handleBack}>
                    <ArrowLeft size={24} />
                </button>
                <h1>Edit Answers</h1>
                <div className={styles.headerInfo}>
                    {answeredQuestions.length} answers available for editing
                </div>
            </div>

            <div className={styles.questionsContainer}>
                {answeredQuestions.map(([questionId, question]) => (
                    <div key={questionId} className={styles.questionCard}>
                        <div className={styles.questionHeader}>
                            <span className={styles.category}>{question.category}</span>
                            {question.required && <span className={styles.required}>Required</span>}
                        </div>
                        <h3 className={styles.questionText}>{question.text}</h3>
                        {renderQuestionAnswer(question)}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default QuestionnaireEditDetailedPage;
