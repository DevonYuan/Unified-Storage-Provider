import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { storageApi } from '../api/client.js'
import {
  HardDrive,
  LogOut,
  Filter,
  ArrowUpDown,
  Grid,
  List,
  ChevronDown,
  Loader2,
  Folder,
  Upload,
} from 'lucide-react'
import { FileCard } from './FileCard.jsx'
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
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [showSortMenu, setShowSortMenu] = useState(false)

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

  const fetchFiles = async () => {
    if (!isGoogleConnected) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      // Get the first Google Drive account
      const accountsResponse = await storageApi.listStorageAccounts()
      const accounts = accountsResponse.storage_accounts || []
      const googleAccount = accounts.find(acc => acc.provider === 'google_drive')

      if (!googleAccount) {
        setError('No Google Drive account connected')
        setLoading(false)
        return
      }

      // Fetch files from backend API (root folder only for MVP)
      const response = await storageApi.listFiles(googleAccount.account_id, 'root')
      const fileItems = response.items || []

      // Transform API response to match FileCard expectations
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
      })))
    } catch (err) {
      console.error('Failed to fetch files:', err)
      setError('Failed to load files from Google Drive')
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
      // Get the first Google Drive account
      const accountsResponse = await storageApi.listStorageAccounts()
      const accounts = accountsResponse.storage_accounts || []
      const googleAccount = accounts.find(acc => acc.provider === 'google_drive')

      if (!googleAccount) {
        setUploadError('No Google Drive account connected')
        return
      }

      // Upload file to backend API (root folder only for MVP)
      const uploadedFile = await storageApi.uploadFile(googleAccount.account_id, file, 'root')

      // Add the uploaded file to the beginning of the list
      setFiles(prev => [uploadedFile, ...prev])

      // Reset file input
      fileInput.value = ''
    } catch (err) {
      console.error('Failed to upload file:', err)
      setUploadError('Failed to upload file')
    } finally {
      setUploading(false)
    }
  }

  useEffect(() => {
    fetchFiles()
  }, [isGoogleConnected])

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
            <h1 className="connected-home-page__title">All files</h1>
            <p className="connected-home-page__subtitle">
              {itemCount} item{itemCount !== 1 ? 's' : ''} · sorted by {sortBy === 'recent' ? 'recent' : sortBy === 'name' ? 'name' : 'size'}
            </p>
          </div>

          {/* Controls */}
          <div className="connected-home-page__controls">
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
        <div className="connected-home-page__content">
          {loading ? (
            <div className="connected-home-page__loading">
              <Loader2 className="connected-home-page__loader" size={24} />
              <span>Loading files...</span>
            </div>
          ) : error ? (
            <div className="connected-home-page__error">
              <Folder className="connected-home-page__error-icon" size={48} />
              <p>{error}</p>
              <button onClick={fetchFiles} className="connected-home-page__retry-btn">Retry</button>
            </div>
          ) : sortedFiles.length === 0 ? (
            <div className="connected-home-page__empty">
              <Folder className="connected-home-page__empty-icon" size={64} />
              <h2>No files found</h2>
              <p>Connect Google Drive to see your files</p>
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
                  onOpen={(fileId) => handleOpenFile(fileId, sortedFiles)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

// Handle opening file/folder - moved inside component
function handleOpenFile(fileId, files) {
  const file = files.find(f => f.id === fileId)
  if (file?.web_view_link) {
    window.open(file.web_view_link, '_blank')
  }
}