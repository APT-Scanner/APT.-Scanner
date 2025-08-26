import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Edit, Check, X, Save } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import styles from '../styles/QuestionnaireEditDetailedPage.module.css';

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
    const fetchQuestionnaireData = async () => {
        if (!idToken) return;

        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`/api/v1/questionnaire/responses`, {
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
    };

    useEffect(() => {
        fetchQuestionnaireData();
    }, [idToken]);

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

            const response = await fetch(`/api/v1/questionnaire/responses`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    answers: {
                        [questionId]: tempAnswer
                    }
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save answer');
            }

            setUserResponses(prev => ({
                ...prev,
                [questionId]: tempAnswer
            }));

            setEditingQuestion(null);
            setTempAnswer('');
        } catch (err) {
            console.error('Error saving answer:', err);
            setError('Failed to save answer');
        } finally {
            setSaving(false);
        }
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
                            placeholder="הכנס את התשובה שלך..."
                        />
                    )}

                    {question.type === 'slider' && (
                        <div className={styles.sliderContainer}>
                            <span>טווח תקציב: {question.config?.min} - {question.config?.max} {question.config?.unit}</span>
                            <input
                                type="text"
                                value={tempAnswer}
                                onChange={(e) => setTempAnswer(e.target.value)}
                                className={styles.textInput}
                                placeholder="הכנס טווח כ [מינימום, מקסימום]"
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
                            {saving ? 'שומר...' : 'שמור'}
                        </button>
                        <button 
                            onClick={cancelEditing}
                            className={styles.cancelButton}
                        >
                            <X size={16} />
                            ביטול
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
                            {typeof currentAnswer === 'string' && currentAnswer.startsWith('[') 
                                ? JSON.parse(currentAnswer).join(', ')
                                : Array.isArray(currentAnswer) 
                                    ? currentAnswer.join(', ')
                                    : currentAnswer
                            }
                        </span>
                    ) : (
                        <span className={styles.noAnswer}>לא נענתה</span>
                    )}
                </div>
                <button 
                    onClick={() => startEditing(questionId, currentAnswer)}
                    className={styles.editButton}
                >
                    <Edit size={16} />
                    ערוך
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
                    <h1>ערוך תשובות</h1>
                </div>
                <div className={styles.loadingContainer}>
                    <RefreshCw size={48} className={styles.spinner} />
                    <p>טוען תשובות...</p>
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
                    <h1>ערוך תשובות</h1>
                </div>
                <div className={styles.errorContainer}>
                    <p className={styles.errorMessage}>{error}</p>
                    <button onClick={fetchQuestionnaireData} className={styles.retryButton}>
                        <RefreshCw size={16} />
                        נסה שוב
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
                    <h1>ערוך תשובות</h1>
                </div>
                <div className={styles.emptyContainer}>
                    <Save size={48} className={styles.emptyIcon} />
                    <h2>אין תשובות לעריכה</h2>
                    <p>טרם ענית על שאלות כלשהן. התחל בלענות על השאלון כדי שתוכל לערוך תשובות.</p>
                    <button 
                        onClick={() => navigate('/questionnaire')}
                        className={styles.startButton}
                    >
                        התחל לענות על שאלות
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
                <h1>ערוך תשובות</h1>
                <div className={styles.headerInfo}>
                    {answeredQuestions.length} תשובות זמינות לעריכה
                </div>
            </div>

            <div className={styles.questionsContainer}>
                {answeredQuestions.map(([questionId, question]) => (
                    <div key={questionId} className={styles.questionCard}>
                        <div className={styles.questionHeader}>
                            <span className={styles.category}>{question.category}</span>
                            {question.required && <span className={styles.required}>חובה</span>}
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
