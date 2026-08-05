import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { storageApi, omnidriveApi, authApi } from '../api/client.js'
import {
  HardDrive,
  LogOut,
  Filter,
  ArrowUpDown,
  Grid,
  List,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Folder,
  FolderPlus,
  Upload,
} from 'lucide-react'
import { FileCard } from './FileCard.jsx'
import { ContextMenu } from './ContextMenu.jsx'
import '../styles/ConnectedHomePage.css'

export function ConnectedHomePage() {
  const { user, isGoogleConnected, checkGoogleConnection, logout } = useAuth()
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [sortBy, setSortBy] = useState('recent')
  const [filterBy, setFilterBy] = useState('all')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [showNewFolderInput, setShowNewFolderInput] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [showSortMenu, setShowSortMenu] = useState(false)

  // Context menu state
  const [contextMenu, setContextMenu] = useState(null) // { x, y, file } or null

  // Clipboard state for cut/copy/paste
  const [clipboard, setClipboard] = useState(null) // { action: 'cut'|'copy', files: [...], sourceView, sourcePath } or null

  // Connected accounts state
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState(null)

  // OmniDrive unified view state
  const [selectedView, setSelectedView] = useState('omnidrive') // 'omnidrive' or account_id number

  // Folder navigation state (per-provider mode)
  const [currentFolderId, setCurrentFolderId] = useState('root')
  const [currentFolderName, setCurrentFolderName] = useState('All files')
  const [folderStack, setFolderStack] = useState([])

  // Path navigation state (OmniDrive mode)
  const [currentPath, setCurrentPath] = useState('/')
  const [currentPathName, setCurrentPathName] = useState('All files')
  const [pathStack, setPathStack] = useState([]) // [{path: '/Documents', name: 'Documents'}]

  // Get the currently selected account
  const selectedAccount = accounts.find(acc => acc.account_id === selectedAccountId)

  // Current display name and stack for breadcrumbs (unified across both modes)
  const displayName = selectedView === 'omnidrive' ? currentPathName : currentFolderName
  const breadcrumbStack = selectedView === 'omnidrive' ? pathStack : folderStack

  // Filter and sort options - simplified to only what API supports
  const filterOptions = [
    { value: 'all', label: 'All files' },
    { value: 'folder', label: 'Folders' },
    { value: 'image', label: 'Images' },
    { value: 'video', label: 'Videos' },
    { value: 'document', label: 'Documents' },
  ]

  const sortOptions = [
    { value: 'recent', label: 'Recent' },
    { value: 'name', label: 'Name' },
    { value: 'size', label: 'Size' },
  ]

  const loadAccounts = async () => {
    try {
      const response = await storageApi.listStorageAccounts()
      const accts = response.storage_accounts || []
      setAccounts(accts)
      // Auto-select first account if none selected or current selection is gone
      if (!selectedAccountId || !accts.find(a => a.account_id === selectedAccountId)) {
        if (accts.length > 0) {
          setSelectedAccountId(accts[0].account_id)
        }
      }
      // Default to OmniDrive view if we have accounts and no explicit selection yet
      if (accts.length > 0 && selectedView === 'omnidrive') {
        // Keep omnidrive as default
      }
      return accts
    } catch (err) {
      console.error('Failed to load accounts:', err)
      return []
    }
  }

  const fetchFiles = async (targetPath = null, targetFolderId = null) => {
    setLoading(true)
    setError(null)

    try {
      // Refresh accounts list
      const accts = await loadAccounts()

      if (selectedView === 'omnidrive') {
        // ── OmniDrive unified view ────────────────────────────
        const path = targetPath ?? currentPath
        const response = await omnidriveApi.listFiles(path)
        const fileItems = response.items || []

        // Surface per-provider errors from the merge response
        if (response.errors && response.errors.length > 0) {
          setError(response.errors.join('; '))
        }

        setFiles(fileItems.map(item => ({
          id: item.virtual_id,
          name: item.name,
          mime_type: item.mime_type,
          category: item.category,
          size: item.size,
          size_formatted: item.size_formatted,
          modified_time: item.modified_time,
          modified_time_formatted: item.modified_time_formatted,
          thumbnail_link: item.thumbnail_link,
          web_view_link: item.web_view_link,
          is_folder: item.is_folder,
          item_count: item.item_count,
          providers: item.providers || [],
        })))
      } else {
        // ── Per-provider view (existing logic) ────────────────
        const targetId = targetFolderId ?? currentFolderId
        const account = accts.find(acc => acc.account_id === selectedView)

        if (!account) {
          setError('No storage account selected')
          setLoading(false)
          return
        }

        const response = await storageApi.listFiles(account.account_id, targetId)
        const fileItems = response.items || []

        setFiles(fileItems.map(item => ({
          id: item.id,
          name: item.name,
          mime_type: item.mime_type,
          category: item.category,
          size: item.size,
          size_formatted: item.size_formatted,
          modified_time: item.modified_time,
          modified_time_formatted: item.modified_time_formatted,
          thumbnail_link: item.thumbnail_link,
          web_view_link: item.web_view_link,
          is_folder: item.is_folder,
          item_count: item.item_count,
          providers: [response.provider === 'google_drive' ? 'google' : 'onedrive'],
        })))
      }
    } catch (err) {
      console.error('Failed to fetch files:', err)
      setError(err.message || 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }

  const uploadFile = async (e) => {
    const fileInput = document.getElementById('file-upload')
    if (!fileInput.files || fileInput.files.length === 0) {
      return
    }

    const file = fileInput.files[0]
    setUploading(true)
    setUploadError(null)

    try {
      let uploadedFile

      if (selectedView === 'omnidrive') {
        uploadedFile = await omnidriveApi.uploadFile(file, currentPath)
      } else {
        if (!selectedAccountId) {
          setUploadError('No storage account selected')
          return
        }
        uploadedFile = await storageApi.uploadFile(selectedView, file, currentFolderId)
      }

      // Add the uploaded file to the beginning of the list
      setFiles(prev => [{
        id: uploadedFile.virtual_id || uploadedFile.id,
        name: uploadedFile.name,
        mime_type: uploadedFile.mime_type,
        category: uploadedFile.category,
        size: uploadedFile.size,
        size_formatted: uploadedFile.size_formatted,
        modified_time: uploadedFile.modified_time,
        modified_time_formatted: uploadedFile.modified_time_formatted,
        thumbnail_link: uploadedFile.thumbnail_link,
        web_view_link: uploadedFile.web_view_link,
        is_folder: uploadedFile.is_folder,
        item_count: uploadedFile.item_count,
        providers: uploadedFile.providers || [],
      }, ...prev])

      // Reset file input
      fileInput.value = ''
    } catch (err) {
      console.error('Failed to upload file:', err)
      setUploadError('Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  const handleCreateFolder = async () => {
    const name = newFolderName.trim()
    if (!name) return

    if (selectedView !== 'omnidrive' && !selectedAccountId) return

    setCreatingFolder(true)
    try {
      let newFolder

      if (selectedView === 'omnidrive') {
        newFolder = await omnidriveApi.createFolder(name, currentPath)
      } else {
        newFolder = await storageApi.createFolder(selectedView, name, currentFolderId)
      }

      setFiles(prev => [{
        id: newFolder.virtual_id || newFolder.id,
        name: newFolder.name,
        mime_type: newFolder.mime_type,
        category: newFolder.category,
        size: newFolder.size,
        size_formatted: newFolder.size_formatted,
        modified_time: newFolder.modified_time,
        modified_time_formatted: newFolder.modified_time_formatted,
        thumbnail_link: newFolder.thumbnail_link,
        web_view_link: newFolder.web_view_link,
        is_folder: newFolder.is_folder,
        item_count: newFolder.item_count,
        providers: newFolder.providers || [],
      }, ...prev])
      setNewFolderName('')
      setShowNewFolderInput(false)
    } catch (err) {
      console.error('Failed to create folder:', err)
      setError('Failed to create folder')
    } finally {
      setCreatingFolder(false)
    }
  }

  // Folder navigation handlers
  const navigateToFolder = (folderId, folderName) => {
    if (selectedView === 'omnidrive') {
      // Path-based navigation
      const newPath = currentPath === '/' ? `/${folderName}` : `${currentPath}/${folderName}`
      setPathStack(prev => [...prev, { path: newPath, name: folderName }])
      setCurrentPath(newPath)
      setCurrentPathName(folderName)
    } else {
      // ID-based navigation (existing)
      setFolderStack(prev => [...prev, { id: folderId, name: folderName }])
      setCurrentFolderId(folderId)
      setCurrentFolderName(folderName)
    }
  }

  const goBack = () => {
    if (selectedView === 'omnidrive') {
      const newStack = pathStack.slice(0, -1)
      const parent = newStack[newStack.length - 1]
      if (parent) {
        setCurrentPath(parent.path)
        setCurrentPathName(parent.name)
      } else {
        setCurrentPath('/')
        setCurrentPathName('All files')
      }
      setPathStack(newStack)
    } else {
      const newStack = folderStack.slice(0, -1)
      const parent = newStack[newStack.length - 1]
      if (parent) {
        setCurrentFolderId(parent.id)
        setCurrentFolderName(parent.name)
      } else {
        setCurrentFolderId('root')
        setCurrentFolderName('All files')
      }
      setFolderStack(newStack)
    }
  }

  const navigateToRoot = () => {
    if (selectedView === 'omnidrive') {
      setCurrentPath('/')
      setCurrentPathName('All files')
      setPathStack([])
    } else {
      setCurrentFolderId('root')
      setCurrentFolderName('All files')
      setFolderStack([])
    }
  }

  const navigateToBreadcrumb = (index) => {
    if (selectedView === 'omnidrive') {
      const target = pathStack[index]
      if (target) {
        setCurrentPath(target.path)
        setCurrentPathName(target.name)
        setPathStack(pathStack.slice(0, index + 1))
      }
    } else {
      const target = folderStack[index]
      if (target) {
        setCurrentFolderId(target.id)
        setCurrentFolderName(target.name)
        setFolderStack(folderStack.slice(0, index + 1))
      }
    }
  }

  const handleOpenFile = (file) => {
    if (file.is_folder) {
      navigateToFolder(file.id, file.name)
    } else if (file.web_view_link) {
      window.open(file.web_view_link, '_blank')
    }
  }

  // ── One-click OAuth reconnect ──────────────────────────────────────

  const [reconnecting, setReconnecting] = useState(null) // 'google' | 'microsoft' | null

  const handleReconnect = async (provider) => {
    setReconnecting(provider)
    try {
      const redirectUri = provider === 'google'
        ? 'http://localhost:8000/auth/google/callback'
        : 'http://localhost:8000/auth/microsoft/callback'

      const { auth_url, state } = provider === 'google'
        ? await authApi.startGoogleOAuth(redirectUri)
        : await authApi.startMicrosoftOAuth(redirectUri)

      sessionStorage.setItem(provider === 'google' ? 'oauth_state' : 'oauth_state_ms', state)
      window.location.href = auth_url
    } catch (err) {
      setReconnecting(null)
      setError(`Failed to start ${provider === 'google' ? 'Google' : 'Microsoft'} reconnection: ${err.message}`)
    }
  }

  // Detect which provider an error is about
  const failedProvider = (() => {
    if (!error) return null
    const msg = error.toLowerCase()
    // Explicit provider mentions in the error
    if (msg.includes('google') || msg.includes('drive')) return 'google'
    if (msg.includes('microsoft') || msg.includes('onedrive') || msg.includes('graph')) return 'microsoft'
    // If viewing a specific provider account, that's the one that failed
    if (selectedView !== 'omnidrive' && selectedAccount) {
      return selectedAccount.provider === 'google_drive' ? 'google' : 'microsoft'
    }
    return null
  })()
  
  // ── Context menu handlers ─────────────────────────────────────────

  const handleContextMenu = (e, file) => {
    setContextMenu({ x: e.clientX, y: e.clientY, file })
  }

  const closeContextMenu = () => {
    setContextMenu(null)
  }

  const handleRename = async (file) => {
    const newName = window.prompt('Enter new name:', file.name)
    if (!newName || newName.trim() === '' || newName.trim() === file.name) return

    try {
      if (selectedView === 'omnidrive') {
        await omnidriveApi.renameItem(file.id, newName.trim())
      } else {
        await storageApi.renameFile(selectedView, file.id, newName.trim())
      }
      // Refresh to show the renamed file
      fetchFiles()
    } catch (err) {
      setError(`Failed to rename: ${err.message}`)
    }
  }

  const handleDelete = async (file) => {
    const confirmed = window.confirm(`Are you sure you want to delete "${file.name}"?`)
    if (!confirmed) return

    try {
      if (selectedView === 'omnidrive') {
        await omnidriveApi.deleteItem(file.id)
      } else {
        await storageApi.deleteFile(selectedView, file.id)
      }
      // Remove from local state immediately
      setFiles(prev => prev.filter(f => f.id !== file.id))
    } catch (err) {
      setError(`Failed to delete: ${err.message}`)
    }
  }

  const handleDownload = (file) => {
    let url
    if (selectedView === 'omnidrive') {
      url = omnidriveApi.getDownloadUrl(file.id)
    } else {
      url = storageApi.getDownloadUrl(selectedView, file.id)
    }
    // Trigger download by creating a temporary anchor
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  // ── Cut / Copy / Paste ─────────────────────────────────────────────

  const handleCut = (file) => {
    setClipboard({
      action: 'cut',
      files: [file],
      sourceView: selectedView,
      sourcePath: selectedView === 'omnidrive' ? currentPath : currentFolderId,
    })
  }

  const handleCopy = (file) => {
    setClipboard({
      action: 'copy',
      files: [file],
      sourceView: selectedView,
      sourcePath: selectedView === 'omnidrive' ? currentPath : currentFolderId,
    })
  }

  const handlePaste = async () => {
    if (!clipboard || clipboard.files.length === 0) return

    const destPath = selectedView === 'omnidrive' ? currentPath : currentFolderId

    // Don't paste to the same location — silently ignore
    if (clipboard.sourceView === selectedView && clipboard.sourcePath === destPath) {
      return
    }

    setError(null)
    const file = clipboard.files[0]
    try {
      if (clipboard.action === 'cut') {
        if (selectedView === 'omnidrive') {
          await omnidriveApi.moveItem(file.id, currentPath)
        } else {
          await storageApi.moveFile(selectedView, file.id, currentFolderId)
        }
      } else {
        if (selectedView === 'omnidrive') {
          await omnidriveApi.copyItem(file.id, currentPath)
        } else {
          await storageApi.copyFile(selectedView, file.id, currentFolderId)
        }
      }
      if (clipboard.action === 'cut') {
        setClipboard(null)
      }
      fetchFiles()
    } catch (err) {
      setError(`Failed to ${clipboard.action === 'cut' ? 'move' : 'copy'}: ${err.message}`)
    }
  }

  // Empty-area right-click — shows paste-only menu when clipboard has content
  const handleGridContextMenu = (e) => {
    if (!clipboard || clipboard.files.length === 0) return
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY, file: null })
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  useEffect(() => {
    if (selectedView === 'omnidrive') {
      fetchFiles(currentPath)
    } else if (selectedView) {
      fetchFiles(null, currentFolderId)
    }
  }, [selectedView, currentPath, currentFolderId])

  useEffect(() => {
    checkGoogleConnection()
  }, [checkGoogleConnection])

  // Filter files based on filterBy
  const filteredFiles = files.filter(file => {
    if (filterBy === 'all') return true
    return file.category === filterBy
  })

  // Sort files
  const sortedFiles = [...filteredFiles].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name)
      case 'size':
        if (a.size === null && b.size === null) return 0
        if (a.size === null) return 1
        if (b.size === null) return -1
        return b.size - a.size
      case 'recent':
      default:
        if (!a.modified_time && !b.modified_time) return 0
        if (!a.modified_time) return 1
        if (!b.modified_time) return -1
        return new Date(b.modified_time) - new Date(a.modified_time)
    }
  })

  const itemCount = sortedFiles.length
  const folderCount = sortedFiles.filter(f => f.is_folder).length
  const fileCount = itemCount - folderCount

  const isAuthError = error && (
    error.toLowerCase().includes('refresh') ||
    error.toLowerCase().includes('token') ||
    error.toLowerCase().includes('expired') ||
    error.toLowerCase().includes('auth')
  )

  return (
    <div className="connected-home-page">
      {/* Header */}
      <header className="connected-home-page__header">
        <div className="connected-home-page__brand">
          <div className="connected-home-page__logo">
            <HardDrive className="connected-home-page__logo-icon" size={20} />
          </div>
          <span className="connected-home-page__brand-name">OmniDrive</span>
        </div>

        <div className="connected-home-page__actions">
          <button
            onClick={fetchFiles}
            disabled={loading}
            className="connected-home-page__refresh"
            aria-label="Refresh files"
          >
            <Loader2 className={`connected-home-page__refresh-icon ${loading ? 'connected-home-page__refresh-icon--spinning' : ''}`} size={16} />
          </button>
          <button
            onClick={logout}
            className="connected-home-page__signout"
          >
            <LogOut className="connected-home-page__signout-icon" size={16} />
            Sign out
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="connected-home-page__main">
        {/* Toolbar */}
        <div className="connected-home-page__toolbar">
          {/* Title and item count */}
          <div className="connected-home-page__title-section">
            <div className="connected-home-page__title-row">
              {breadcrumbStack.length > 0 && (
                <button
                  onClick={goBack}
                  className="connected-home-page__back-btn"
                  aria-label="Go back to parent folder"
                  title={`Back to ${breadcrumbStack.length > 1 ? breadcrumbStack[breadcrumbStack.length - 2].name : 'All files'}`}
                >
                  <ChevronLeft size={20} />
                </button>
              )}
              <h1 className="connected-home-page__title">{displayName}</h1>
            </div>
            <p className="connected-home-page__subtitle">
              {itemCount} item{itemCount !== 1 ? 's' : ''} · sorted by {sortBy === 'recent' ? 'recent' : sortBy === 'name' ? 'name' : 'size'}
            </p>
          </div>

          {/* Controls */}
          <div className="connected-home-page__controls">
            {/* Provider selector */}
            {accounts.length > 0 && (
              <div className="connected-home-page__dropdown">
                <select
                  value={selectedView}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === 'omnidrive') {
                      setSelectedView('omnidrive')
                      navigateToRoot()
                    } else {
                      const numVal = Number(val)
                      setSelectedView(numVal)
                      setSelectedAccountId(numVal)
                      navigateToRoot()
                    }
                  }}
                  className="connected-home-page__provider-select"
                >
                  <option value="omnidrive">🌐 OmniDrive (Unified)</option>
                  {accounts.map(acc => (
                    <option key={acc.account_id} value={acc.account_id}>
                      {acc.provider === 'google_drive' ? '🟢 Google Drive' : '🔵 OneDrive'} · {acc.display_name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Filter dropdown */}
            <div className="connected-home-page__dropdown">
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className="connected-home-page__dropdown-trigger"
                aria-expanded={showFilterMenu}
                aria-haspopup="listbox"
              >
                <Filter className="connected-home-page__dropdown-icon" size={16} />
                <span>{filterOptions.find(f => f.value === filterBy)?.label || 'All files'}</span>
                <ChevronDown className="connected-home-page__dropdown-chevron" size={14} />
              </button>
              {showFilterMenu && (
                <ul className="connected-home-page__dropdown-menu" role="listbox">
                  {filterOptions.map(option => (
                    <li key={option.value} role="option" aria-selected={filterBy === option.value}>
                      <button
                        onClick={() => {
                          setFilterBy(option.value)
                          setShowFilterMenu(false)
                        }}
                        className={`connected-home-page__dropdown-item ${filterBy === option.value ? 'connected-home-page__dropdown-item--active' : ''}`}
                      >
                        {option.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Sort dropdown */}
            <div className="connected-home-page__dropdown">
              <button
                onClick={() => setShowSortMenu(!showSortMenu)}
                className="connected-home-page__dropdown-trigger"
                aria-expanded={showSortMenu}
                aria-haspopup="listbox"
              >
                <ArrowUpDown className="connected-home-page__dropdown-icon" size={16} />
                <span>{sortOptions.find(s => s.value === sortBy)?.label || 'Recent'}</span>
                <ChevronDown className="connected-home-page__dropdown-chevron" size={14} />
              </button>
              {showSortMenu && (
                <ul className="connected-home-page__dropdown-menu" role="listbox">
                  {sortOptions.map(option => (
                    <li key={option.value} role="option" aria-selected={sortBy === option.value}>
                      <button
                        onClick={() => {
                          setSortBy(option.value)
                          setShowSortMenu(false)
                        }}
                        className={`connected-home-page__dropdown-item ${sortBy === option.value ? 'connected-home-page__dropdown-item--active' : ''}`}
                      >
                        {option.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* View toggle */}
            <div className="connected-home-page__view-toggle" role="group" aria-label="View mode">
              <button
                onClick={() => setViewMode('grid')}
                className={`connected-home-page__view-btn ${viewMode === 'grid' ? 'connected-home-page__view-btn--active' : ''}`}
                aria-label="Grid view"
                aria-pressed={viewMode === 'grid'}
              >
                <Grid className="connected-home-page__view-icon" size={16} />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`connected-home-page__view-btn ${viewMode === 'list' ? 'connected-home-page__view-btn--active' : ''}`}
                aria-label="List view"
                aria-pressed={viewMode === 'list'}
              >
                <List className="connected-home-page__view-icon" size={16} />
              </button>
            </div>

            {/* New Folder button */}
            <div className="connected-home-page__upload">
              {showNewFolderInput ? (
                <div className="connected-home-page__new-folder-form">
                  <input
                    type="text"
                    value={newFolderName}
                    onChange={(e) => setNewFolderName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleCreateFolder(); if (e.key === 'Escape') { setShowNewFolderInput(false); setNewFolderName(''); } }}
                    placeholder="Folder name..."
                    className="connected-home-page__new-folder-input"
                    autoFocus
                    disabled={creatingFolder}
                  />
                  <button
                    onClick={handleCreateFolder}
                    disabled={creatingFolder || !newFolderName.trim()}
                    className="connected-home-page__new-folder-confirm"
                  >
                    {creatingFolder ? '...' : 'Create'}
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowNewFolderInput(true)}
                  className="connected-home-page__upload-btn"
                  disabled={!selectedAccountId && selectedView !== 'omnidrive'}
                >
                  <FolderPlus className="connected-home-page__upload-icon" size={16} />
                  New Folder
                </button>
              )}
            </div>

            {/* Upload button */}
            <div className="connected-home-page__upload">
              <label
                htmlFor="file-upload"
                className={`connected-home-page__upload-btn ${uploading ? 'connected-home-page__upload-btn--uploading' : ''}`}
              >
                <Upload className="connected-home-page__upload-icon" size={16} />
                {uploading ? 'Uploading...' : 'Upload'}
              </label>
              <input
                type="file"
                id="file-upload"
                style={{ display: 'none' }}
                onChange={uploadFile}
              />
            </div>
          </div>
        </div>

        {/* File Grid */}
        <div className="connected-home-page__content" onContextMenu={handleGridContextMenu}>
          {/* Breadcrumb trail */}
          {breadcrumbStack.length > 0 && (
            <div className="connected-home-page__breadcrumb">
              <button
                onClick={() => navigateToRoot()}
                className="connected-home-page__breadcrumb-item"
              >
                All files
              </button>
              {breadcrumbStack.map((crumb, i) => (
                <span key={crumb.id || crumb.path} className="connected-home-page__breadcrumb-segment">
                  <ChevronRight size={12} className="connected-home-page__breadcrumb-sep" />
                  <button
                    onClick={() => navigateToBreadcrumb(i)}
                    className={`connected-home-page__breadcrumb-item ${i === breadcrumbStack.length - 1 ? 'connected-home-page__breadcrumb-item--active' : ''}`}
                  >
                    {crumb.name}
                  </button>
                </span>
              ))}
            </div>
          )}
          {error && isAuthError ? (
            <div className="connected-home-page__error">
              <Folder className="connected-home-page__error-icon" size={48} />
              <p>{error}</p>
              <div className="connected-home-page__error-actions">
                <p className="connected-home-page__error-hint">
                  Your session may have expired. Click below to re-authenticate.
                </p>
                <div className="connected-home-page__error-buttons">
                  {(!failedProvider || failedProvider === 'google') && (
                    <button
                      onClick={() => handleReconnect('google')}
                      disabled={reconnecting !== null}
                      className="connected-home-page__retry-btn"
                    >
                      {reconnecting === 'google' ? 'Connecting...' : 'Reconnect Google Drive'}
                    </button>
                  )}
                  {(!failedProvider || failedProvider === 'microsoft') && (
                    <button
                      onClick={() => handleReconnect('microsoft')}
                      disabled={reconnecting !== null}
                      className="connected-home-page__retry-btn connected-home-page__retry-btn--ms"
                    >
                      {reconnecting === 'microsoft' ? 'Connecting...' : 'Reconnect OneDrive'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Non-auth error banner */}
              {error && !isAuthError && (
                <div className="connected-home-page__error-banner">
                  <span>{error}</span>
                  <button onClick={() => setError(null)} className="connected-home-page__error-dismiss" aria-label="Dismiss">×</button>
                </div>
              )}
              {loading ? (
                <div className="connected-home-page__loading">
                  <Loader2 className="connected-home-page__loader" size={24} />
                  <span>Loading files...</span>
                </div>
              ) : sortedFiles.length === 0 ? (
                <div className="connected-home-page__empty">
                  <Folder className="connected-home-page__empty-icon" size={64} />
                  <h2>No files found</h2>
                  <p>{accounts.length === 0 ? 'Connect a storage provider to see your files' : 'This folder is empty'}</p>
                </div>
              ) : (
                <div
                  className={`connected-home-page__grid ${viewMode === 'list' ? 'connected-home-page__grid--list' : ''}`}
                  role="list"
                  aria-label="Files and folders"
                >
                  {sortedFiles.map(file => (
                    <FileCard
                      key={file.id}
                      file={file}
                      viewMode={viewMode}
                      providers={file.providers || (selectedAccount?.provider === 'google_drive' ? ['google'] : ['onedrive'])}
                      onOpen={handleOpenFile}
                      onContextMenu={handleContextMenu}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          file={contextMenu.file}
          clipboardCount={clipboard ? clipboard.files.length : 0}
          onClose={closeContextMenu}
          onCut={handleCut}
          onCopy={handleCopy}
          onPaste={handlePaste}
          onRename={handleRename}
          onDelete={handleDelete}
          onDownload={handleDownload}
        />
      )}
    </div>
  )
}