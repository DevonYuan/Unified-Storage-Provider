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
  Loader2,
  Folder,
  FolderPlus,
  Upload,
} from 'lucide-react'
import { FileCard } from './FileCard.jsx'
import { ContextMenu } from './ContextMenu.jsx'
import { Sidebar } from './Sidebar.jsx'
import { TopBar } from './TopBar.jsx'
import '../styles/ConnectedHomePage.css'

export function ConnectedHomePage() {
  const { checkGoogleConnection, logout } = useAuth()
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [sortBy, setSortBy] = useState('recent')
  const [filterBy, setFilterBy] = useState('all')
  const [uploading, setUploading] = useState(false)
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [showNewFolderInput, setShowNewFolderInput] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [showSortMenu, setShowSortMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [contextMenu, setContextMenu] = useState(null)
  const [clipboard, setClipboard] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [selectedAccountId, setSelectedAccountId] = useState(null)
  const [selectedView, setSelectedView] = useState('omnidrive')
  const [activeNav, setActiveNav] = useState('all')
  const [currentFolderId, setCurrentFolderId] = useState('root')
  const [currentFolderName, setCurrentFolderName] = useState('All files')
  const [folderStack, setFolderStack] = useState([])
  const [currentPath, setCurrentPath] = useState('/')
  const [currentPathName, setCurrentPathName] = useState('All files')
  const [pathStack, setPathStack] = useState([])
  const [reconnecting, setReconnecting] = useState(null)

  const selectedAccount = accounts.find(acc => acc.account_id === selectedAccountId)
  const displayName = selectedView === 'omnidrive' ? currentPathName : currentFolderName
  const breadcrumbStack = selectedView === 'omnidrive' ? pathStack : folderStack

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

  // ── Data loading ────────────────────────────────────────────────

  const loadAccounts = async () => {
    try {
      const response = await storageApi.listStorageAccounts()
      const accts = response.storage_accounts || []
      setAccounts(accts)
      if (!selectedAccountId || !accts.find(a => a.account_id === selectedAccountId)) {
        if (accts.length > 0) setSelectedAccountId(accts[0].account_id)
      }
      return accts
    } catch (err) {
      console.error('Failed to load accounts:', err)
      return []
    }
  }

  const fetchTrash = async (accts) => {
    const allTrash = []
    for (const acc of accts) {
      try {
        const result = await storageApi.listTrash(acc.account_id)
        const items = (result.items || []).map(item => ({
          ...item,
          providers: [acc.provider === 'google_drive' ? 'google' : 'onedrive'],
        }))
        allTrash.push(...items)
      } catch (err) {
        console.error(`Failed to fetch trash for account ${acc.account_id}:`, err)
      }
    }
    setFiles(allTrash)
    setLoading(false)
  }

  const fetchFiles = async (targetPath = null, targetFolderId = null) => {
    setLoading(true)
    setError(null)
    try {
      const accts = await loadAccounts()

      if (activeNav === 'trash') {
        await fetchTrash(accts)
        return
      }

      if (selectedView === 'omnidrive') {
        const path = targetPath ?? currentPath
        const response = await omnidriveApi.listFiles(path)
        const fileItems = response.items || []
        if (response.errors && response.errors.length > 0) setError(response.errors.join('; '))
        setFiles(fileItems.map(item => ({
          id: item.virtual_id, name: item.name, mime_type: item.mime_type, category: item.category,
          size: item.size, size_formatted: item.size_formatted, modified_time: item.modified_time,
          modified_time_formatted: item.modified_time_formatted, thumbnail_link: item.thumbnail_link,
          web_view_link: item.web_view_link, is_folder: item.is_folder, item_count: item.item_count,
          providers: item.providers || [],
        })))
      } else {
        const targetId = targetFolderId ?? currentFolderId
        const account = accts.find(acc => acc.account_id === selectedView)
        if (!account) { setError('No storage account selected'); setLoading(false); return }
        const response = await storageApi.listFiles(account.account_id, targetId)
        const fileItems = response.items || []
        setFiles(fileItems.map(item => ({
          id: item.id, name: item.name, mime_type: item.mime_type, category: item.category,
          size: item.size, size_formatted: item.size_formatted, modified_time: item.modified_time,
          modified_time_formatted: item.modified_time_formatted, thumbnail_link: item.thumbnail_link,
          web_view_link: item.web_view_link, is_folder: item.is_folder, item_count: item.item_count,
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

  // ── Sidebar nav ──────────────────────────────────────────────────

  const handleNavChange = (navId) => {
    setActiveNav(navId)
    if (navId === 'all') {
      setSelectedView('omnidrive')
      setCurrentPath('/')
      setCurrentPathName('All files')
      setPathStack([])
    }
  }

  // ── Upload ──────────────────────────────────────────────────────

  const uploadFile = async (e) => {
    const fileInput = e.target
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) return
    const file = fileInput.files[0]
    setUploading(true)
    try {
      let uploadedFile
      if (selectedView === 'omnidrive') {
        uploadedFile = await omnidriveApi.uploadFile(file, currentPath)
      } else {
        if (!selectedAccountId) { setUploading(false); return }
        uploadedFile = await storageApi.uploadFile(selectedView, file, currentFolderId)
      }
      setFiles(prev => [{
        id: uploadedFile.virtual_id || uploadedFile.id, name: uploadedFile.name,
        mime_type: uploadedFile.mime_type, category: uploadedFile.category,
        size: uploadedFile.size, size_formatted: uploadedFile.size_formatted,
        modified_time: uploadedFile.modified_time, modified_time_formatted: uploadedFile.modified_time_formatted,
        thumbnail_link: uploadedFile.thumbnail_link, web_view_link: uploadedFile.web_view_link,
        is_folder: uploadedFile.is_folder, item_count: uploadedFile.item_count,
        providers: uploadedFile.providers || [],
      }, ...prev])
      fileInput.value = ''
    } catch (err) {
      console.error('Failed to upload file:', err)
      setError('Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  // ── Create folder ────────────────────────────────────────────────

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
        id: newFolder.virtual_id || newFolder.id, name: newFolder.name,
        mime_type: newFolder.mime_type, category: newFolder.category,
        size: newFolder.size, size_formatted: newFolder.size_formatted,
        modified_time: newFolder.modified_time, modified_time_formatted: newFolder.modified_time_formatted,
        thumbnail_link: newFolder.thumbnail_link, web_view_link: newFolder.web_view_link,
        is_folder: newFolder.is_folder, item_count: newFolder.item_count,
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

  // ── Navigation ──────────────────────────────────────────────────

  const navigateToFolder = (folderId, folderName) => {
    if (selectedView === 'omnidrive') {
      const newPath = currentPath === '/' ? `/${folderName}` : `${currentPath}/${folderName}`
      setPathStack(prev => [...prev, { path: newPath, name: folderName }])
      setCurrentPath(newPath)
      setCurrentPathName(folderName)
    } else {
      setFolderStack(prev => [...prev, { id: folderId, name: folderName }])
      setCurrentFolderId(folderId)
      setCurrentFolderName(folderName)
    }
  }

  const navigateToRoot = () => {
    if (selectedView === 'omnidrive') {
      setCurrentPath('/'); setCurrentPathName('All files'); setPathStack([])
    } else {
      setCurrentFolderId('root'); setCurrentFolderName('All files'); setFolderStack([])
    }
  }

  const navigateToBreadcrumb = (index) => {
    if (selectedView === 'omnidrive') {
      const target = pathStack[index]
      if (target) { setCurrentPath(target.path); setCurrentPathName(target.name); setPathStack(pathStack.slice(0, index + 1)) }
    } else {
      const target = folderStack[index]
      if (target) { setCurrentFolderId(target.id); setCurrentFolderName(target.name); setFolderStack(folderStack.slice(0, index + 1)) }
    }
  }

  const handleOpenFile = (file) => {
    if (file.is_folder) navigateToFolder(file.id, file.name)
    else if (file.web_view_link) window.open(file.web_view_link, '_blank')
  }

  // ── OAuth reconnect ─────────────────────────────────────────────

  const handleReconnect = async (provider) => {
    setReconnecting(provider)
    try {
      const redirectUri = provider === 'google'
        ? `${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/auth/google/callback`
        : `${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/auth/microsoft/callback`
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

  const failedProvider = (() => {
    if (!error) return null
    const msg = error.toLowerCase()
    if (msg.includes('google') || msg.includes('drive')) return 'google'
    if (msg.includes('microsoft') || msg.includes('onedrive') || msg.includes('graph')) return 'microsoft'
    if (selectedView !== 'omnidrive' && selectedAccount) {
      return selectedAccount.provider === 'google_drive' ? 'google' : 'microsoft'
    }
    return null
  })()

  // ── Context menu handlers ───────────────────────────────────────

  const handleContextMenu = (e, file) => setContextMenu({ x: e.clientX, y: e.clientY, file })
  const closeContextMenu = () => setContextMenu(null)

  const handleRename = async (file) => {
    const newName = window.prompt('Enter new name:', file.name)
    if (!newName || newName.trim() === '' || newName.trim() === file.name) return
    try {
      if (selectedView === 'omnidrive') await omnidriveApi.renameItem(file.id, newName.trim())
      else await storageApi.renameFile(selectedView, file.id, newName.trim())
      fetchFiles()
    } catch (err) { setError(`Failed to rename: ${err.message}`) }
  }

  const handleDelete = async (file) => {
    const confirmed = window.confirm(`Are you sure you want to delete "${file.name}"?`)
    if (!confirmed) return
    try {
      if (selectedView === 'omnidrive') await omnidriveApi.deleteItem(file.id)
      else await storageApi.deleteFile(selectedView, file.id)
      setFiles(prev => prev.filter(f => f.id !== file.id))
    } catch (err) { setError(`Failed to delete: ${err.message}`) }
  }

  const handleDownload = async (file) => {
    let url
    if (selectedView === 'omnidrive') url = omnidriveApi.getDownloadUrl(file.id)
    else url = storageApi.getDownloadUrl(selectedView, file.id)

    // For folders, request ZIP format
    if (file.is_folder) {
      url += '?format=zip'
    }

    try {
      const response = await fetch(url, { credentials: 'include' })
      if (!response.ok) {
        let errorMsg = `Download failed (HTTP ${response.status})`
        try { const errorData = await response.json(); if (errorData.detail) errorMsg = errorData.detail } catch {}
        throw new Error(errorMsg)
      }
      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = file.is_folder ? `${file.name}.zip` : file.name
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) { setError(`Failed to download "${file.name}": ${err.message}`) }
  }

  // ── Cut / Copy / Paste ──────────────────────────────────────────

  const handleCut = (file) => setClipboard({ action: 'cut', files: [file], sourceView: selectedView, sourcePath: selectedView === 'omnidrive' ? currentPath : currentFolderId })
  const handleCopy = (file) => setClipboard({ action: 'copy', files: [file], sourceView: selectedView, sourcePath: selectedView === 'omnidrive' ? currentPath : currentFolderId })

  const handlePaste = async () => {
    if (!clipboard || clipboard.files.length === 0) return
    const destPath = selectedView === 'omnidrive' ? currentPath : currentFolderId
    if (clipboard.sourceView === selectedView && clipboard.sourcePath === destPath) return
    setError(null)
    const file = clipboard.files[0]
    try {
      if (clipboard.action === 'cut') {
        if (selectedView === 'omnidrive') await omnidriveApi.moveItem(file.id, currentPath)
        else await storageApi.moveFile(selectedView, file.id, currentFolderId)
      } else {
        if (selectedView === 'omnidrive') await omnidriveApi.copyItem(file.id, currentPath)
        else await storageApi.copyFile(selectedView, file.id, currentFolderId)
      }
      if (clipboard.action === 'cut') setClipboard(null)
      fetchFiles()
    } catch (err) { setError(`Failed to ${clipboard.action === 'cut' ? 'move' : 'copy'}: ${err.message}`) }
  }

  const handleGridContextMenu = (e) => {
    if (!clipboard || clipboard.files.length === 0) return
    e.preventDefault(); e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY, file: null })
  }

  // ── Filters & sorting ───────────────────────────────────────────

  const isAuthError = error && (error.toLowerCase().includes('token') || error.toLowerCase().includes('auth') || error.toLowerCase().includes('expired'))
  const itemCount = files.length

  let filteredFiles = files.filter(file => filterBy === 'all' || file.category === filterBy)
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase()
    filteredFiles = filteredFiles.filter(file => file.name.toLowerCase().includes(q))
  }

  const sortedFiles = [...filteredFiles].sort((a, b) => {
    switch (sortBy) {
      case 'name': return a.name.localeCompare(b.name)
      case 'size': return (b.size || 0) - (a.size || 0)
      default: return b.modified_time?.localeCompare(a.modified_time || '') || 0
    }
  })

  // ── Effects ─────────────────────────────────────────────────────

  useEffect(() => { loadAccounts() }, [])
  useEffect(() => {
    if (activeNav === 'trash') { fetchFiles(); return }
    if (selectedView === 'omnidrive') fetchFiles(currentPath)
    else if (selectedView) fetchFiles(null, currentFolderId)
  }, [selectedView, currentPath, currentFolderId, activeNav])
  useEffect(() => { checkGoogleConnection() }, [checkGoogleConnection])

  // ── Render ──────────────────────────────────────────────────────

  return (
    <div className="app-layout">
      <Sidebar
        activeNav={activeNav}
        onNavChange={handleNavChange}
        accounts={accounts}
        onUpload={uploadFile}
      />

      <div className="app-main">
        <TopBar
          breadcrumbStack={breadcrumbStack}
          currentName={displayName}
          onNavigateRoot={navigateToRoot}
          onNavigateBreadcrumb={navigateToBreadcrumb}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        <main className="app-content">
          {/* Title + Toolbar */}
          <div className="content-header">
            <div className="content-header__left">
              <h1 className="content-header__title">
                {activeNav === 'trash' ? 'Trash' : displayName}
              </h1>
              <p className="content-header__subtitle">
                {itemCount} item{itemCount !== 1 ? 's' : ''} · sorted by {sortBy === 'recent' ? 'recent' : sortBy === 'name' ? 'name' : 'size'}
              </p>
            </div>

            <div className="content-header__controls">
              {/* Provider selector (hidden in trash view) */}
              {activeNav !== 'trash' && accounts.length > 0 && (
                <div className="content-header__dropdown">
                  <select
                    value={selectedView}
                    onChange={(e) => {
                      const val = e.target.value
                      if (val === 'omnidrive') { setSelectedView('omnidrive'); navigateToRoot() }
                      else { const numVal = Number(val); setSelectedView(numVal); setSelectedAccountId(numVal); navigateToRoot() }
                    }}
                    className="content-header__select"
                  >
                    <option value="omnidrive"> OmniDrive</option>
                    {accounts.map(acc => (
                      <option key={acc.account_id} value={acc.account_id}>
                        {acc.provider === 'google_drive' ? ' Google' : ' OneDrive'} · {acc.display_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Filter */}
              <div className="content-header__dropdown">
                <button onClick={() => setShowFilterMenu(!showFilterMenu)} className="content-header__toolbar-btn">
                  <Filter size={14} />
                  <span>{filterOptions.find(f => f.value === filterBy)?.label || 'All'}</span>
                  <ChevronDown size={12} />
                </button>
                {showFilterMenu && (
                  <ul className="content-header__dropdown-menu">
                    {filterOptions.map(option => (
                      <li key={option.value}>
                        <button onClick={() => { setFilterBy(option.value); setShowFilterMenu(false) }} className={`content-header__dropdown-item ${filterBy === option.value ? 'content-header__dropdown-item--active' : ''}`}>{option.label}</button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Sort */}
              <div className="content-header__dropdown">
                <button onClick={() => setShowSortMenu(!showSortMenu)} className="content-header__toolbar-btn">
                  <ArrowUpDown size={14} />
                  <span>{sortOptions.find(s => s.value === sortBy)?.label || 'Recent'}</span>
                  <ChevronDown size={12} />
                </button>
                {showSortMenu && (
                  <ul className="content-header__dropdown-menu">
                    {sortOptions.map(option => (
                      <li key={option.value}>
                        <button onClick={() => { setSortBy(option.value); setShowSortMenu(false) }} className={`content-header__dropdown-item ${sortBy === option.value ? 'content-header__dropdown-item--active' : ''}`}>{option.label}</button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* View toggle */}
              <div className="content-header__view-toggle">
                <button onClick={() => setViewMode('grid')} className={`content-header__view-btn ${viewMode === 'grid' ? 'content-header__view-btn--active' : ''}`}><Grid size={15} /></button>
                <button onClick={() => setViewMode('list')} className={`content-header__view-btn ${viewMode === 'list' ? 'content-header__view-btn--active' : ''}`}><List size={15} /></button>
              </div>

              {/* New Folder */}
              {activeNav !== 'trash' && (
                <div className="content-header__action">
                  {showNewFolderInput ? (
                    <div className="content-header__new-folder-form">
                      <input type="text" value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleCreateFolder(); if (e.key === 'Escape') { setShowNewFolderInput(false); setNewFolderName(''); } }}
                        placeholder="Folder name..." className="content-header__new-folder-input" autoFocus disabled={creatingFolder} />
                      <button onClick={handleCreateFolder} disabled={creatingFolder || !newFolderName.trim()} className="content-header__new-folder-confirm">
                        {creatingFolder ? '...' : 'Create'}
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => setShowNewFolderInput(true)} className="content-header__toolbar-btn" disabled={!selectedAccountId && selectedView !== 'omnidrive'}>
                      <FolderPlus size={14} /> New Folder
                    </button>
                  )}
                </div>
              )}

              {/* Upload */}
              {activeNav !== 'trash' && (
                <div className="content-header__action">
                  <label className={`content-header__toolbar-btn ${uploading ? 'content-header__toolbar-btn--uploading' : ''}`}>
                    <Upload size={14} /> {uploading ? 'Uploading...' : 'Upload'}
                    <input type="file" id="file-upload-main" style={{ display: 'none' }} onChange={uploadFile} />
                  </label>
                </div>
              )}

              {/* Sign out */}
              <button onClick={logout} className="content-header__signout">
                <LogOut size={14} /> Sign out
              </button>
            </div>
          </div>

          {/* Back button */}
          {breadcrumbStack.length > 0 && (
            <button onClick={() => {
              if (selectedView === 'omnidrive') {
                const newStack = pathStack.slice(0, -1)
                const parent = newStack[newStack.length - 1]
                if (parent) { setCurrentPath(parent.path); setCurrentPathName(parent.name) }
                else { setCurrentPath('/'); setCurrentPathName('All files') }
                setPathStack(newStack)
              } else {
                const newStack = folderStack.slice(0, -1)
                const parent = newStack[newStack.length - 1]
                if (parent) { setCurrentFolderId(parent.id); setCurrentFolderName(parent.name) }
                else { setCurrentFolderId('root'); setCurrentFolderName('All files') }
                setFolderStack(newStack)
              }
            }} className="content__back-btn">
              <ChevronLeft size={16} /> <span>Back</span>
            </button>
          )}

          {/* Content area */}
          <div className="content__body" onContextMenu={handleGridContextMenu}>
            {error && isAuthError ? (
              <div className="content__error">
                <Folder size={48} />
                <p>{error}</p>
                <div className="content__error-actions">
                  <p className="content__error-hint">Your session may have expired.</p>
                  <div className="content__error-buttons">
                    {(!failedProvider || failedProvider === 'google') && (
                      <button onClick={() => handleReconnect('google')} disabled={reconnecting !== null} className="content__retry-btn">
                        {reconnecting === 'google' ? 'Connecting...' : 'Reconnect Google Drive'}
                      </button>
                    )}
                    {(!failedProvider || failedProvider === 'microsoft') && (
                      <button onClick={() => handleReconnect('microsoft')} disabled={reconnecting !== null} className="content__retry-btn content__retry-btn--ms">
                        {reconnecting === 'microsoft' ? 'Connecting...' : 'Reconnect OneDrive'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {error && !isAuthError && (
                  <div className="content__error-banner">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="content__error-dismiss">×</button>
                  </div>
                )}
                {loading ? (
                  <div className="content__loading">
                    <Loader2 className="content__loader" size={24} />
                    <span>Loading files...</span>
                  </div>
                ) : sortedFiles.length === 0 ? (
                  <div className="content__empty">
                    <Folder size={64} />
                    <h2>No files found</h2>
                    <p>{accounts.length === 0 ? 'Connect a storage provider to see your files' : activeNav === 'trash' ? 'Trash is empty' : searchQuery ? 'No files match your search' : 'This folder is empty'}</p>
                  </div>
                ) : (
                  <div className={`content__grid ${viewMode === 'list' ? 'content__grid--list' : ''}`}>
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
      </div>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x} y={contextMenu.y} file={contextMenu.file}
          clipboardCount={clipboard ? clipboard.files.length : 0}
          onClose={closeContextMenu} onCut={handleCut} onCopy={handleCopy}
          onPaste={handlePaste} onRename={handleRename} onDelete={handleDelete}
          onDownload={handleDownload}
        />
      )}
    </div>
  )
}
