import axios from 'axios';

const API_BASE_URL = '/api/v1';

const googleDriveApi = axios.create({
    baseURL: API_BASE_URL,
});

// Interceptor to attach JWT token to requests
googleDriveApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('omnidrive_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const googleDriveService = {
    // OAuth 2.0 endpoints
    async getGoogleOAuthUrl(state?: string) {
        const response = await googleDriveApi.get('/google/oauth/url', {
            params: { state }
        });
        return response.data;
    },

    async handleGoogleCallback(code: string, state?: string) {
        const response = await googleDriveApi.get('/google/oauth/callback', {
            params: { code, state }
        });
        return response.data;
    },

    // Token management
    async storeGoogleTokens(tokenData: {
        access_token: string;
        refresh_token: string;
        expires_at: string;
    }) {
        const response = await googleDriveApi.post('/google/tokens', tokenData);
        return response.data;
    },

    async getGoogleTokens() {
        const response = await googleDriveApi.get('/google/tokens');
        return response.data;
    },

    // File operations
    async listGoogleFiles(parentId?: string) {
        const response = await googleDriveApi.get('/google/files', {
            params: { parent_id: parentId }
        });
        return response.data;
    },

    async uploadGoogleFile(
        file: File,
        parentId?: string
    ) {
        const formData = new FormData();
        formData.append('file', file);
        if (parentId) {
            formData.append('parent_id', parentId);
        }

        const response = await googleDriveApi.post(
            '/google/files/upload',
            formData,
            {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            }
        );
        return response.data;
    },

    async downloadGoogleFile(fileId: string) {
        const response = await googleDriveApi.get(`/google/files/${fileId}/download`, {
            responseType: 'blob'
        });
        return response.data;
    },

    // Folder operations
    async createGoogleFolder(folderData: {
        name: string;
        parent_id?: string;
    }) {
        const response = await googleDriveApi.post('/google/folders', folderData);
        return response.data;
    },

    // File modifications
    async deleteGoogleFile(fileId: string) {
        const response = await googleDriveApi.delete(`/google/files/${fileId}`);
        return response.data;
    },

    async renameGoogleFile(fileId: string, fileData: { name: string }) {
        const response = await googleDriveApi.patch(`/google/files/${fileId}`, fileData);
        return response.data;
    }
};