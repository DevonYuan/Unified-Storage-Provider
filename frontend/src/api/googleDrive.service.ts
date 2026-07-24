import axios from 'axios';

const API_BASE_URL = '/auth/google'; // Changed from '/api/v1' to '/auth/google' to match backend route

const googleDriveApi = axios.create({
    baseURL: API_BASE_URL,
});

// Interceptor to attach JWT token to requests
googleDriveApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('omnidrive_token');
    if (token) {
        console.log(`[GoogleDriveService] Attaching token to request: ${token.substring(0, 20)}...`);
        config.headers.Authorization = `Bearer ${token}`;
    } else {
        console.log('[GoogleDriveService] No token found for request');
    }
    return config;
});

googleDriveApi.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        console.error('[GoogleDriveService] API error:', {
            status: error.response?.status,
            data: error.response?.data,
            message: error.message
        });
        return Promise.reject(error);
    }
);

export const googleDriveService = {
    // OAuth 2.0 endpoints
    async getGoogleOAuthUrl(state?: string) {
        console.log('[GoogleDriveService] Getting OAuth URL', state ? 'with state' :' : ');
        const params: { [key: string]: string } = {};
        if (state !== undefined && state !== '') {
            params.state = state;
        }
        try {
            const response = await googleDriveApi.get('/oauth/url', {
            params
        });
        console.log('[GoogleDriveService] OAuth URL response:', response.data);
        return response.data;
    } catch (error) {
        console.error('[GoogleDriveService] Failed to get OAuth URL:', {
            status: error.response?.status,
            data: error.response?.data,
            message: error.message
        });
        throw error;
    }
    },

    async handleGoogleCallback(code: string, state?: string) {
        console.log('[GoogleDriveService] Handling Google callback with code:', code.substring(0, 10) + '...');
        try {
            const response = await googleDriveApi.get('/oauth/callback', {
                params: { code, state }
            });
            console.log('[GoogleDriveService] Callback response:', response.data);
            return response.data;
        } catch (error) {
            console.error('[GoogleDriveService] Failed to handle callback:', {
                status: error.response?.status,
                data: error.response?.data,
                message: error.message
            });
            throw error;
        }
    },

    // Token management
    async storeGoogleTokens(tokenData: {
        access_token: string;
        refresh_token: string;
        expires_at: string;
    }) {
        console.log('[GoogleDriveService] Storing Google tokens');
        const response = await googleDriveApi.post('/tokens', tokenData);
        return response.data;
    },

    async getGoogleTokens() {
        console.log('[GoogleDriveService] Getting Google tokens');
        try {
            const response = await googleDriveApi.get('/tokens');
            console.log('[GoogleDriveService] Got tokens:', response.data);
            return response.data;
        } catch (error) {
            console.error('[GoogleDriveService] Failed to get tokens:', {
                status: error.response?.status,
                data: error.response?.data,
                message: error.message
            });
            throw error;
        }
    },

    // File operations
    async listGoogleFiles(parentId?: string) {
        const response = await googleDriveApi.get('/files', {
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
            '/files/upload',
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
        const response = await googleDriveApi.get(`/files/${fileId}/download`, {
            responseType: 'blob'
        });
        return response.data;
    },

    // Folder operations
    async createGoogleFolder(folderData: {
        name: string;
        parent_id?: string;
    }) {
        const response = await googleDriveApi.post('/folders', folderData);
        return response.data;
    },

    // File modifications
    async deleteGoogleFile(fileId: string) {
        const response = await googleDriveApi.delete(`/files/${fileId}`);
        return response.data;
    },

    async renameGoogleFile(fileId: string, fileData: { name: string }) {
        const response = await googleDriveApi.patch(`/files/${fileId}`, fileData);
        return response.data;
    }
};