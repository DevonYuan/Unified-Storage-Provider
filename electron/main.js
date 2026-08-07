/**
 * OmniDrive — Electron Main Process
 *
 * Launches the FastAPI backend as a subprocess, waits for it to be ready,
 * then opens the React frontend in a BrowserWindow.
 */

import electron from 'electron'
const { app, BrowserWindow } = electron
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const isDev = !app.isPackaged

// ── Backend process ──────────────────────────────────────────────────────

let backendProcess = null
const BACKEND_PORT = 8000

function getBackendPath() {
  if (isDev) {
    // In development, run from the source directory
    return path.resolve(__dirname, '..', 'backend', 'main.py')
  }
  // In production, the backend is bundled in resources/backend
  return path.join(process.resourcesPath, 'backend', 'main.py')
}

function getPythonCommand() {
  // On Windows, "python" or "python3". Electron-builder can bundle a Python runtime too.
  return process.platform === 'win32' ? 'python' : 'python3'
}

function startBackend() {
  const pythonCmd = getPythonCommand()
  const backendPath = getBackendPath()

  console.log(`Starting backend: ${pythonCmd} ${backendPath}`)

  backendProcess = spawn(pythonCmd, [backendPath], {
    env: {
      ...process.env,
      OMNIDRIVE_PORT: String(BACKEND_PORT),
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`)
  })

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend:err] ${data.toString().trim()}`)
  })

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err.message)
  })

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`)
    backendProcess = null
  })
}

async function waitForBackend(url, maxRetries = 30, delay = 500) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(`${url}/health`)
      if (response.ok) {
        console.log('Backend is ready')
        return true
      }
    } catch {
      // Backend not ready yet
    }
    await new Promise((resolve) => setTimeout(resolve, delay))
  }
  console.error('Backend failed to start within timeout')
  return false
}

function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend...')
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/f', '/t'])
    } else {
      backendProcess.kill('SIGTERM')
    }
    backendProcess = null
  }
}

// ── Window ───────────────────────────────────────────────────────────────

let mainWindow = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'OmniDrive',
    backgroundColor: '#0a0a0a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  })

  // Load the frontend
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── App lifecycle ────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  startBackend()

  const backendReady = await waitForBackend(`http://localhost:${BACKEND_PORT}`)
  if (!backendReady) {
    console.error('Backend did not start. Exiting.')
    app.quit()
    return
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopBackend()
})

app.on('quit', () => {
  stopBackend()
})
