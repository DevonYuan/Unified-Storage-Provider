/**
 * OmniDrive — Preload Script
 *
 * Exposes a minimal, secure API to the renderer process via contextBridge.
 * Uses CommonJS because Electron preload scripts loaded from asar archives
 * do not reliably support ESM imports.
 */

const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('omnidrive', {
  platform: process.platform,
  isElectron: true,
})
