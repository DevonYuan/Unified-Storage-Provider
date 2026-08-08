/**
 * OmniDrive — Preload Script
 *
 * Exposes a minimal, secure API to the renderer process via contextBridge.
 * Uses CommonJS because Electron preload scripts loaded from asar archives
 * do not reliably support ESM imports.
 */

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('omnidrive', {
  platform: process.platform,
  isElectron: true,
  // Called by the OAuth callback page to navigate back to the frontend.
  // Needed because Chromium blocks http→file:// redirects.
  navigateToHome: () => ipcRenderer.send('navigate-to-home'),
  navigateTo: (hash) => ipcRenderer.send('navigate-to', hash),
})
