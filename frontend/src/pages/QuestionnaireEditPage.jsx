import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Edit3, Plus, CheckCircle, Circle, BarChart3 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import styles from '../styles/QuestionnaireEditPage.module.css';

const QuestionnaireEditPage = () => {
    const navigate = useNavigate();
    const { idToken } = useAuth();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [questionsData, setQuestionsData] = useState(null);
    const [userResponses, setUserResponses] = useState({});

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

    const handleAnswerMore = () => {
        // Navigate to regular questionnaire to answer remaining questions
        navigate('/questionnaire');
    };

    const handleEditAnswers = () => {
        // Navigate to detailed edit mode (we'll create this later)
        navigate('/questionnaire-edit-detailed');
    };



    if (loading) {
        return (
            <div className={styles.pageContainer}>
                <div className={styles.header}>
                    <button className={styles.backButton} onClick={handleBack}>
                        <ArrowLeft size={24} />
                    </button>
                    <h1>ניהול שאלון</h1>
                </div>
                <div className={styles.loadingContainer}>
                    <RefreshCw size={48} className={styles.spinner} />
                    <p>טוען נתונים...</p>
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
                    <h1>ניהול שאלון</h1>
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
    const answeredCount = Object.keys(userResponses).length;
    const totalQuestions = Object.keys(allQuestions).length;
    const completionPercentage = Math.round((answeredCount / totalQuestions) * 100);

    return (
        <div className={styles.pageContainer}>
            <div className={styles.header}>
                <button className={styles.backButton} onClick={handleBack}>
                    <ArrowLeft size={24} />
                </button>
                <h1>ניהול שאלון</h1>
            </div>

            <div className={styles.mainContent}>
                {/* Progress Overview */}
                <div className={styles.progressSection}>
                    <div className={styles.progressHeader}>
                        <BarChart3 size={28} className={styles.progressIcon} />
                        <h2>סטטוס השאלון שלך</h2>
                    </div>
                    
                    <div className={styles.progressStats}>
                        <div className={styles.progressBar}>
                            <div 
                                className={styles.progressFill}
                                style={{ width: `${completionPercentage}%` }}
                            ></div>
                        </div>
                        <div className={styles.progressText}>
                            {completionPercentage}% הושלם
                        </div>
                    </div>

                    <div className={styles.statsGrid}>
                        <div className={styles.statCard}>
                            <CheckCircle size={24} className={styles.statIcon} />
                            <div className={styles.statInfo}>
                                <span className={styles.statNumber}>{answeredCount}</span>
                                <span className={styles.statLabel}>שאלות נענו</span>
                            </div>
                        </div>
                        
                        <div className={styles.statCard}>
                            <Circle size={24} className={styles.statIcon} />
                            <div className={styles.statInfo}>
                                <span className={styles.statNumber}>{totalQuestions - answeredCount}</span>
                                <span className={styles.statLabel}>שאלות נותרו</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className={styles.actionsSection}>
                    <h2>מה תרצה לעשות?</h2>
                    
                    <div className={styles.actionButtons}>
                        <button 
                            className={styles.actionButton}
                            onClick={handleAnswerMore}
                        >
                            <div className={styles.buttonIcon}>
                                <Plus size={32} />
                            </div>
                            <div className={styles.buttonContent}>
                                <h3>ענה על שאלות נוספות</h3>
                                <p>המשך לענות על שאלות שטרם נענו או שדילגת עליהן</p>
                                {totalQuestions - answeredCount > 0 && (
                                    <span className={styles.badge}>
                                        {totalQuestions - answeredCount} שאלות נותרו
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
                                <h3>ערוך תשובות קיימות</h3>
                                <p>שנה או עדכן תשובות שכבר נתת בעבר</p>
                                {answeredCount > 0 && (
                                    <span className={styles.badge}>
                                        {answeredCount} תשובות זמינות לעריכה
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
                        <span>כל הכבוד! השלמת את כל השאלות בשאלון</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default QuestionnaireEditPage;
