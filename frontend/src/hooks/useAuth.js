import { useState, useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../config/firebase'; 

export const useAuth = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [idToken, setIdToken] = useState(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
            setUser(currentUser);
            if (currentUser) {
                try {
                    const token = await currentUser.getIdToken();
                    setIdToken(token);
                } catch (error) {
                    console.error("Error getting ID token:", error);
                    setIdToken(null);
                }
            } else {
                setIdToken(null);
            }
            setLoading(false);
        });

        // Cleanup subscription on unmount
        return () => unsubscribe();
    }, []);

    // פונקציה לרענון טוקן במידת הצורך (אופציונלי, פיירבייס מטפל בזה אוטומטית)
    const refreshToken = async () => {
         if (user) {
            try {
               const token = await user.getIdToken(true); // Force refresh
               setIdToken(token);
               return token;
            } catch (error) {
               console.error("Error refreshing ID token:", error);
               setIdToken(null);
               return null;
            }
         }
         return null;
    }

    return { user, idToken, loading, refreshToken };
};


