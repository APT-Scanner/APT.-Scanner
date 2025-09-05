
import API_BASE from '../config/api.js';

export const createUserInDatabase = async (user) => {
    try {
        console.log('🔑 Getting Firebase ID token...');
        const idToken = await user.getIdToken();
        console.log('✅ Firebase ID token obtained, length:', idToken.length);
        console.log('🚀 Creating user in database...');
        
        const response = await fetch(`${API_BASE}/api/v1/users/me`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${idToken}`,
                'Content-Type': 'application/json',
            },
        });
        
        console.log('📡 Response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('❌ Backend error response:', errorData);
            throw new Error(`Failed to create user: ${response.status} - ${errorData.detail || 'Unknown error'}`);
        }
        
        const userData = await response.json();
        console.log('✅ User created successfully:', userData);
        return userData;
    } catch (error) {
        console.error('💥 Error creating user in database:', error);
        throw error;
    }
}

export const getUserFromDatabase = async (user) => {
    try {
        console.log('🔍 Getting existing user from database...');
        const idToken = await user.getIdToken();
        const response = await fetch(`${API_BASE}/api/v1/users/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${idToken}`,
            },
        });
        
        if (!response.ok) {
            console.log('ℹ️ User not found in database (expected for new users)');
            throw new Error(`User not found: ${response.status}`);
        }
        
        const userData = await response.json();
        console.log('✅ Found existing user:', userData);
        return userData;
    } catch (error) {
        console.log('ℹ️ getUserFromDatabase error (normal for new users):', error.message);
        throw error;
    }
}