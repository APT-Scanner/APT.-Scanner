import { useState, useEffect } from 'react';
import { useAuth } from './useAuth'; // ייבוא Hook האימות

// הגדר מחוץ לקומפוננטה או בקובץ קונפיגורציה
const BACKEND_URL = 'http://localhost:8000/api/v1'; // שנה לכתובת ה-API שלך

export const useQuestions = () => {
    const [questions, setQuestions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { idToken, loading: authLoading } = useAuth(); // קבלת טוקן ומצב טעינת אימות

    useEffect(() => {
        // אל תשלח בקשה לפני שנדע את סטטוס האימות ויש לנו טוקן
        if (authLoading) {
            return; // המתן לסיום טעינת האימות
        }

        if (!idToken) {
             setLoading(false);
             setError("User not authenticated."); // אין משתמש מחובר או טוקן
             setQuestions([]);
             return;
         }

        const fetchQuestions = async () => {
            setLoading(true);
            setError(null);
            try {
                // החלף עם נקודת הקצה שלך
                const response = await fetch(`${BACKEND_URL}/questions/all`, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${idToken}`,
                        'Content-Type': 'application/json',
                    },
                });

                if (!response.ok) {
                     const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
                     throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                // מניחים שה-Backend מחזיר מערך שאלות
                setQuestions(Array.isArray(data) ? data : []); // ודא שהתוצאה היא מערך
            } catch (err) {
                console.error("Failed to fetch questions:", err);
                setError(err.message || 'Failed to load questions.');
                setQuestions([]);
            } finally {
                setLoading(false);
            }
        };

        fetchQuestions();
    }, [idToken, authLoading]); // תלות בטוקן ובמצב טעינת האימות

    return { questions, loading, error };
};


