import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { storageApi } from '../api/client.js'
import {
  HardDrive,
  LogOut,
  Filter,
  ArrowUpDown,
  Grid,
  List,
  Upload,
  ChevronDown,
  Loader2,
  Folder,
  Search,
  ChevronRight,
} from 'lucide-react'
import { FileCard } from './FileCard.jsx'
import '../styles/ConnectedHomePage.css'

export function ConnectedHomePage() {
  const { user, isGoogleConnected, checkGoogleConnection } = useAuth()
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [sortBy, setSortBy] = useState('recent')
  const [filterBy, setFilterBy] = useState('all')
  const [currentFolderId, setCurrentFolderId] = useState('root')
  const [folderStack, setFolderStack] = useState([])
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [showSortMenu, setShowSortMenu] = useState(false)

  // Filter and sort options
  const filterOptions = [
    { value: 'all', label: 'All files' },
    { value: 'folder', label: 'Folders' },
    { value: 'image', label: 'Images' },
    { value: 'video', label: 'Videos' },
    { value: 'document', label: 'Documents' },
    { value: 'spreadsheet', label: 'Spreadsheets' },
    { value: 'presentation', label: 'Presentations' },
    { value: 'pdf', label: 'PDFs' },
  ]

  const sortOptions = [
    { value: 'recent', label: 'Recent' },
    { value: 'name', label: 'Name' },
    { value: 'size', label: 'Size' },
    { value: 'modified', label: 'Modified' },
  ]

  const fetchFiles = useCallback(async () => {
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

      // Fetch files from backend API
      const response = await storageApi.listFiles(googleAccount.account_id, currentFolderId)
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
  }, [isGoogleConnected, currentFolderId])

  useEffect(() => {
    fetchFiles()
  }, [fetchFiles])

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
      case 'modified':
        if (!a.modified_time && !b.modified_time) return 0
        if (!a.modified_time) return 1
        if (!b.modified_time) return -1
        return new Date(b.modified_time) - new Date(a.modified_time)
      case 'recent':
      default:
        if (!a.modified_time && !b.modified_time) return 0
        if (!a.modified_time) return 1
        if (!b.modified_time) return -1
        return new Date(b.modified_time) - new Date(a.modified_time)
    }
  })

  const handleNavigate = (folderId) => {
    const folder = files.find(f => f.id === folderId)
    if (folder) {
      setFolderStack(prev => [...prev, { id: currentFolderId, name: currentFolderId === 'root' ? 'All files' : folder.name }])
      setCurrentFolderId(folderId)
    }
  }

  const handleGoBack = () => {
    if (folderStack.length > 0) {
      const previous = folderStack[folderStack.length - 1]
      setFolderStack(prev => prev.slice(0, -1))
      setCurrentFolderId(previous.id)
    }
  }

  const handleOpenFile = (fileId) => {
    const file = files.find(f => f.id === fileId)
    if (file?.web_view_link) {
      window.open(file.web_view_link, '_blank')
    }
  }

  const handleFavoriteToggle = (fileId) => {
    // TODO: Implement favorite toggle
    console.log('Toggle favorite:', fileId)
  }

  const itemCount = sortedFiles.length
  const folderCount = sortedFiles.filter(f => f.is_folder).length
  const fileCount = itemCount - folderCount

  const breadcrumb = currentFolderId === 'root'
    ? [{ id: 'root', name: 'All files' }]
    : [...folderStack, { id: currentFolderId, name: files.find(f => f.id === currentFolderId)?.name || 'Folder' }]

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

        {/* Breadcrumbs */}
        <nav className="connected-home-page__breadcrumbs" aria-label="Folder navigation">
          <ol className="connected-home-page__breadcrumb-list">
            {breadcrumb.map((crumb, index) => (
              <li key={crumb.id} className="connected-home-page__breadcrumb-item">
                {index > 0 && (
                  <ChevronRight className="connected-home-page__breadcrumb-separator" size={14} />
                )}
                <button
                  onClick={() => index === breadcrumb.length - 1 ? null : index === breadcrumb.length - 2 ? handleGoBack() : setCurrentFolderId(crumb.id)}
                  className={`connected-home-page__breadcrumb-link ${index === breadcrumb.length - 1 ? 'connected-home-page__breadcrumb-link--current' : ''}`}
                  disabled={index === breadcrumb.length - 1}
                >
                  {crumb.name}
                </button>
              </li>
            ))}
          </ol>
        </nav>

        <div className="connected-home-page__actions">
          <button
            onClick={checkGoogleConnection}
            disabled={loading}
            className="connected-home-page__refresh"
            aria-label="Refresh connection"
          >
            <Loader2 className={`connected-home-page__refresh-icon ${loading ? 'connected-home-page__refresh-icon--spinning' : ''}`} size={16} />
          </button>
          <button
            onClick={() => { /* logout handled by auth context */ }}
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
              {itemCount} item{itemCount !== 1 ? 's' : ''} · sorted by {sortOptions.find(s => s.value === sortBy)?.label || 'recent'}
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
            <button className="connected-home-page__upload-btn">
              <Upload className="connected-home-page__upload-icon" size={16} />
              Upload
            </button>
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
              <h2>This folder is empty</h2>
              <p>Drag files here or click Upload to get started</p>
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
                  onNavigate={handleNavigate}
                  onOpen={handleOpenFile}
                  onFavoriteToggle={handleFavoriteToggle}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}