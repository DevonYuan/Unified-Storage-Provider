/**
 * OmniDrive — Electron Main Process
 *
 * Launches the FastAPI backend as a subprocess, waits for it to be ready,
 * then opens the React frontend in a BrowserWindow.
 */

import electron from 'electron'
const { app, BrowserWindow, dialog, Menu } = electron
import { spawn, execSync } from 'child_process'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const isDev = !app.isPackaged

// ── Single-instance lock ─────────────────────────────────────────────────

let mainWindow = null

const gotTheLock = app.requestSingleInstanceLock()

if (!gotTheLock) {
  // Another instance is already running — quit this one
  app.quit()
}

app.on('second-instance', (_event, _commandLine, _workingDirectory) => {
  // Someone tried to launch a second copy — focus the existing window
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  }
})

// ── Backend process ──────────────────────────────────────────────────────

let backendProcess = null
const BACKEND_PORT = 8000
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

function killExistingBackend() {
  if (process.platform !== 'win32') return
  try {
    // Find PID using the port
    const output = execSync(`netstat -ano | findstr :${BACKEND_PORT} | findstr LISTENING`, { encoding: 'utf8', timeout: 3000 })
    const match = output.match(/LISTENING\s+(\d+)/)
    if (match) {
      const pid = match[1]
      console.log(`[electron] Killing existing process on port ${BACKEND_PORT} (PID ${pid})`)
      execSync(`taskkill /PID ${pid} /F /T`, { timeout: 3000 })
    }
  } catch (err) {
    // No existing process, or netstat/taskkill failed — ignore
  }
}

function getBackendDir() {
  if (isDev) {
    return path.resolve(__dirname, '..', 'backend')
  }
  return path.join(process.resourcesPath, 'backend')
}

function getBackendExe() {
  if (isDev) {
    return path.resolve(__dirname, '..', 'backend', 'dist', 'omnidrive-backend.exe')
  }
  return path.join(process.resourcesPath, 'backend', 'omnidrive-backend.exe')
}

function startBackend() {
  const backendDir = getBackendDir()
  const backendExe = getBackendExe()

  // In production, try standalone .exe first (no Python required).
  // In development, always use Python source (the .exe may be blocked by AppLocker).
  if (!isDev && fs.existsSync(backendExe)) {
    console.log(`[electron] Starting backend (exe): ${backendExe}`)
    backendProcess = spawn(backendExe, [], {
      cwd: backendDir,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
  } else {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    console.log(`[electron] Starting backend (python): ${pythonCmd} -m uvicorn main:app`)

    backendProcess = spawn(pythonCmd, [
      '-m', 'uvicorn', 'main:app',
      '--host', '127.0.0.1',
      '--port', String(BACKEND_PORT),
      '--log-level', 'info',
    ], {
      cwd: backendDir,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    backendProcess.on('error', (err) => {
      if (err.code === 'ENOENT') {
        dialog.showErrorBox(
          'Python Not Found',
          'Could not find Python. Make sure Python is installed and added to your PATH.\n\n' +
          'You can also start the backend manually:\n' +
          `cd ${backendDir}\npython -m uvicorn main:app --host 127.0.0.1 --port ${BACKEND_PORT}`
        )
      }
    })
  }

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`)
  })

  backendProcess.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    // uvicorn writes normal logs to stderr, not errors
    if (msg.includes('Error') || msg.includes('Traceback')) {
      console.error(`[backend:err] ${msg}`)
    } else {
      console.log(`[backend] ${msg}`)
    }
  })

  backendProcess.on('error', (err) => {
    console.error('[electron] Failed to start backend:', err.message)
    dialog.showErrorBox(
      'Backend Error',
      `Could not start the OmniDrive backend.\n\n${err.message}\n\nMake sure Python is installed and in your PATH.`
    )
  })

  backendProcess.on('close', (code) => {
    console.log(`[electron] Backend exited with code ${code}`)
    if (code !== 0 && code !== null) {
      dialog.showErrorBox(
        'Backend Crashed',
        `The OmniDrive backend exited unexpectedly (code ${code}).\nCheck the console for details.`
      )
    }
    backendProcess = null
  })
}

async function waitForBackend(maxRetries = 25, delay = 400) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(`${BACKEND_URL}/health`)
      if (response.ok) {
        console.log('[electron] Backend is ready')
        return true
      }
    } catch {
      // Still starting up
    }
    await new Promise((resolve) => setTimeout(resolve, delay))
  }
  console.error('[electron] Backend failed to start within timeout')
  return false
}

function stopBackend() {
  if (backendProcess) {
    console.log('[electron] Stopping backend...')
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/f', '/t'])
    } else {
      backendProcess.kill('SIGTERM')
    }
    backendProcess = null
  }
}

// ── Window ───────────────────────────────────────────────────────────────

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
    show: true,
  })

  // Load the frontend
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    const frontendPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html')
    console.log(`[electron] Loading frontend from: ${frontendPath}`)
    mainWindow.loadFile(frontendPath)
  }

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error(`[electron] Page load failed: ${errorCode} - ${errorDescription}`)
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── App lifecycle ────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  // If we didn't get the single-instance lock, quit already happened
  if (!gotTheLock) return

  Menu.setApplicationMenu(null)  // Remove default menu bar

  // Show the window immediately so the user sees something
  createWindow()

  // Start backend in parallel — the frontend already handles API not being ready
  killExistingBackend()
  startBackend()

  const backendReady = await waitForBackend()
  if (!backendReady) {
    dialog.showErrorBox(
      'Backend Not Ready',
      'The OmniDrive backend did not start in time.\n\n' +
      'If you\'re running in development mode:\n' +
      '1. Start the backend manually: cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000\n' +
      '2. Restart the Electron app\n\n' +
      'If you\'re running a packaged build, Python may not be installed.'
    )
    app.quit()
    return
  }

  console.log('[electron] App ready — backend and frontend both running')

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
