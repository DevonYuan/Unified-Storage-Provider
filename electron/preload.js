/**
 * OmniDrive — Preload Script
 *
 * Exposes a minimal, secure API to the renderer process via contextBridge.
 * Currently, the frontend communicates directly with the local backend
 * via fetch(), so no IPC is needed. This file exists as a placeholder
 * for future secure IPC channels if needed.
 */

import electron from 'electron'
const { contextBridge } = electron

contextBridge.exposeInMainWorld('omnidrive', {
  platform: process.platform,
  isElectron: true,
})
