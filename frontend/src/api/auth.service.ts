import axios from 'axios';

const API_BASE_URL = '/api/v1';

const authApi = axios.create({
    baseURL: API_BASE_URL,
});

// Interceptor to attach JWT token to requests
authApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('omnidrive_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authService = {
    async register(email, password) {
        const response = await authApi.post('/register', { email, password });
        return response.data;
    },

    async login(email, password) {
        // FastAPI OAuth2PasswordRequestForm expects form data, not JSON
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const response = await authApi.post('/login', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    async verifyEmail(token) {
        const response = await authApi.get(`/verify-email?token=${token}`);
        return response.data;
    },

    async resendVerification(email) {
        const response = await authApi.post('/resend-verification', { email });
        return response.data;
    },

    async forgotPassword(email) {
        const response = await authApi.post('/forgot-password', { email });
        return response.data;
    },

    async resetPassword(token, password) {
        const response = await authApi.post('/reset-password', { token, password });
        return response.data;
    },

    async logout() {
        const response = await authApi.post('/logout');
        return response.data;
    }
};
