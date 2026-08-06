// API client for OmniDrive backend

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include',
    ...options,
  };

  if (options.body && typeof options.body === 'object') {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const authApi = {
  async startGoogleOAuth(redirectUri) {
    return request('/auth/oauth/start', {
      method: 'POST',
      body: {
        provider: 'google_drive',
        redirect_uri: redirectUri,
      },
    });
  },

  async startMicrosoftOAuth(redirectUri) {
    return request('/auth/oauth/start', {
      method: 'POST',
      body: {
        provider: 'onedrive',
        redirect_uri: redirectUri,
      },
    });
  },

  async handleOAuthCallback(provider, code, state, redirectUri) {
    return request('/auth/oauth/callback', {
      method: 'POST',
      body: {
        provider,
        code,
        state,
        redirect_uri: redirectUri,
      },
    });
  },

  async listAccounts() {
    return request('/auth/accounts');
  },

  async deleteAccount(accountId) {
    return request(`/auth/accounts/${accountId}`, {
      method: 'DELETE',
    });
  },
};

export const storageApi = {
  async listStorageAccounts() {
    return request('/storage');
  },

  async getStorageInfo(accountId) {
    return request(`/storage/${accountId}`);
  },

  async syncStorage(accountId) {
    return request(`/storage/${accountId}/sync`, {
      method: 'POST',
    });
  },

  async getTotalStorage() {
    return request('/storage/accounts/total');
  },

  async listFiles(accountId, parentId = 'root') {
    return request(`/storage/${accountId}/files?parent_id=${parentId}`);
  },

  async getFileMetadata(accountId, fileId) {
    return request(`/storage/${accountId}/files/${fileId}`);
  },

  async uploadFile(accountId, file, parentId = 'root') {
    const formData = new FormData();
    formData.append('file', file);

    const url = `/storage/${accountId}/files/upload?parent_id=${parentId}`;

    // For file uploads, we need to not set Content-Type header
    // so the browser can set it to multipart/form-data with boundary
    const urlFull = `${API_BASE}${url}`;

    const response = await fetch(urlFull, {
      method: 'POST',
      credentials: 'include',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  async createFolder(accountId, folderName, parentId = 'root') {
    return request(`/storage/${accountId}/folders?parent_id=${parentId}`, {
      method: 'POST',
      body: { folder_name: folderName },
    });
  },

  async renameFile(accountId, fileId, name) {
    return request(`/storage/${accountId}/files/${encodeURIComponent(fileId)}`, {
      method: 'PATCH',
      body: { name },
    });
  },

  async deleteFile(accountId, fileId) {
    return request(`/storage/${accountId}/files/${encodeURIComponent(fileId)}`, {
      method: 'DELETE',
    });
  },

  getDownloadUrl(accountId, fileId) {
    return `${API_BASE}/storage/${accountId}/files/${encodeURIComponent(fileId)}/download`;
  },

  async moveFile(accountId, fileId, newParentId = 'root') {
    return request(`/storage/${accountId}/files/${encodeURIComponent(fileId)}/move?new_parent_id=${encodeURIComponent(newParentId)}`, {
      method: 'POST',
    });
  },

  async copyFile(accountId, fileId, newParentId = 'root') {
    return request(`/storage/${accountId}/files/${encodeURIComponent(fileId)}/copy?new_parent_id=${encodeURIComponent(newParentId)}`, {
      method: 'POST',
    });
  },

  async getQuota(accountId) {
    return request(`/storage/${accountId}/quota`);
  },

  async getQuotaSummary() {
    return request('/storage/quota/summary');
  },

  async listTrash(accountId) {
    return request(`/storage/${accountId}/trash`);
  },

  async restoreTrash(accountId, fileId) {
    return request(`/storage/${accountId}/trash/${encodeURIComponent(fileId)}/restore`, {
      method: 'POST',
    });
  },
};

export const omnidriveApi = {
  async listFiles(path = '/', pageSize = 100, pageToken = null) {
    let url = `/omnidrive/files?path=${encodeURIComponent(path)}&page_size=${pageSize}`;
    if (pageToken) {
      url += `&page_token=${encodeURIComponent(pageToken)}`;
    }
    return request(url);
  },

  async uploadFile(file, parentPath = '/') {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${API_BASE}/omnidrive/files/upload?parent_path=${encodeURIComponent(parentPath)}`;

    const response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  },

  async createFolder(name, parentPath = '/') {
    return request('/omnidrive/folders', {
      method: 'POST',
      body: { name, parent_path: parentPath },
    });
  },

  async renameItem(virtualId, name) {
    return request(`/omnidrive/files/${encodeURIComponent(virtualId)}`, {
      method: 'PATCH',
      body: { name },
    });
  },

  async deleteItem(virtualId) {
    return request(`/omnidrive/files/${encodeURIComponent(virtualId)}`, {
      method: 'DELETE',
    });
  },

  async refreshTree() {
    return request('/omnidrive/refresh', {
      method: 'POST',
    });
  },

  getDownloadUrl(virtualId) {
    return `${API_BASE}/omnidrive/files/${encodeURIComponent(virtualId)}/download`;
  },

  async moveItem(virtualId, newParentPath = '/') {
    return request(`/omnidrive/files/${encodeURIComponent(virtualId)}/move?new_parent_path=${encodeURIComponent(newParentPath)}`, {
      method: 'POST',
    });
  },

  async copyItem(virtualId, newParentPath = '/') {
    return request(`/omnidrive/files/${encodeURIComponent(virtualId)}/copy?new_parent_path=${encodeURIComponent(newParentPath)}`, {
      method: 'POST',
    });
  },
};

export default {
  auth: authApi,
  storage: storageApi,
  omnidrive: omnidriveApi,
};