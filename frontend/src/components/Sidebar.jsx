import { useState, useEffect } from 'react'
import {
  HardDrive, FolderOpen, Star, Users, Clock, Trash2,
  ChevronDown, ChevronUp, Plus, Upload
} from 'lucide-react'
import { storageApi } from '../api/client.js'
import '../styles/Sidebar.css'

const NAV_ITEMS = [
  { id: 'all', label: 'All files', icon: FolderOpen },
  { id: 'starred', label: 'Starred', icon: Star },
  { id: 'shared', label: 'Shared', icon: Users },
  { id: 'recent', label: 'Recent', icon: Clock },
  { id: 'trash', label: 'Trash', icon: Trash2 },
]

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  return `${size >= 10 ? Math.round(size) : size.toFixed(1)} ${units[i]}`
}

export function Sidebar({ activeNav, onNavChange, accounts }) {
  const [sourcesOpen, setSourcesOpen] = useState(true)
  const [quotas, setQuotas] = useState([])
  const [totalUsed, setTotalUsed] = useState(0)
  const [totalSpace, setTotalSpace] = useState(0)

  useEffect(() => {
    loadQuotas()
  }, [accounts])

  const loadQuotas = async () => {
    try {
      const summary = await storageApi.getQuotaSummary()
      setQuotas(summary.quotas || [])
      setTotalUsed(summary.total_used_space || 0)
      setTotalSpace(summary.total_space || 0)
    } catch {
      // Silently fail — quotas are non-critical
    }
  }

  const usagePercent = totalSpace > 0 ? (totalUsed / totalSpace) * 100 : 0

  const getProviderColor = (provider) => {
    return provider === 'google_drive' ? 'var(--accent)' : 'var(--accent-blue)'
  }

  const getProviderLabel = (provider) => {
    return provider === 'google_drive' ? 'Google Drive' : 'OneDrive'
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar__brand">
        <div className="sidebar__logo">
          <HardDrive size={20} />
        </div>
        <span className="sidebar__brand-name">OmniDrive</span>
      </div>

      {/* New upload button */}
      <div className="sidebar__upload-area">
        <label className="sidebar__upload-btn" htmlFor="file-upload-sidebar">
          <Plus size={16} />
          <span>New upload</span>
          <kbd className="sidebar__shortcut">⌘U</kbd>
        </label>
        <input type="file" id="file-upload-sidebar" style={{ display: 'none' }} onChange={() => {}} />
      </div>

      {/* Workspace nav */}
      <nav className="sidebar__nav">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon
          const isActive = activeNav === item.id
          return (
            <button
              key={item.id}
              className={`sidebar__nav-item ${isActive ? 'sidebar__nav-item--active' : ''}`}
              onClick={() => onNavChange(item.id)}
            >
              <Icon size={17} className="sidebar__nav-icon" />
              <span>{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* By Source */}
      <div className="sidebar__section">
        <button
          className="sidebar__section-header"
          onClick={() => setSourcesOpen(!sourcesOpen)}
        >
          <span>By Source</span>
          {sourcesOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {sourcesOpen && (
          <div className="sidebar__sources">
            {accounts.length === 0 ? (
              <p className="sidebar__sources-empty">No accounts connected</p>
            ) : (
              accounts.map(acc => {
                const quota = quotas.find(q => q.account_id === acc.account_id) || {}
                return (
                  <div key={acc.account_id} className="sidebar__source-item">
                    <div className="sidebar__source-info">
                      <span
                        className="sidebar__source-dot"
                        style={{ backgroundColor: getProviderColor(acc.provider) }}
                      />
                      <div className="sidebar__source-text">
                        <span className="sidebar__source-name">{getProviderLabel(acc.provider)}</span>
                        <span className="sidebar__source-email">{acc.display_name}</span>
                      </div>
                    </div>
                    <div className="sidebar__source-usage">
                      <span>{formatBytes(quota.used_space || 0)} / {formatBytes(quota.total_space || 0)}</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>

      {/* Storage summary bar */}
      <div className="sidebar__storage">
        <div className="sidebar__storage-header">
          <span>Storage</span>
          <span className="sidebar__storage-values">
            {formatBytes(totalUsed)} / {formatBytes(totalSpace)}
          </span>
        </div>
        <div className="sidebar__storage-bar">
          <div
            className="sidebar__storage-fill"
            style={{ width: `${Math.min(usagePercent, 100)}%` }}
          />
        </div>
      </div>
    </aside>
  )
}
