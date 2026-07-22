import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../api/auth.service';

interface User {
    id: number;
    email: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    signIn: (token: string, user: User) => void;
    signOut: () => Promise<void>;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const loadStoredAuth = () => {
            const storedToken = localStorage.getItem('omnidrive_token');
            const storedUser = localStorage.getItem('omnidrive_user');

            if (storedToken && storedUser) {
                setToken(storedToken);
                setUser(JSON.parse(storedUser));
            }
            setIsLoading(false);
        };
        loadStoredAuth();
    }, []);

    const signIn = (newToken: string, newUser: User) => {
        setToken(newToken);
        setUser(newUser);
        localStorage.setItem('omnidrive_token', newToken);
        localStorage.setItem('omnidrive_user', JSON.stringify(newUser));
    };

    const signOut = async () => {
        try {
            await authService.logout();
        } catch (error) {
            console.error('Logout API call failed', error);
        } finally {
            setToken(null);
            setUser(null);
            localStorage.removeItem('omnidrive_token');
            localStorage.removeItem('omnidrive_user');
        }
    };

    return (
        <AuthContext.Provider value={{ user, token, signIn, signOut, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
