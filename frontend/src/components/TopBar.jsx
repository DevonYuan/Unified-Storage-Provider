import { Search, Bell, ChevronRight } from 'lucide-react'
import '../styles/TopBar.css'

export function TopBar({ breadcrumbStack, currentName, onNavigateRoot, onNavigateBreadcrumb, searchQuery, onSearchChange }) {
  return (
    <header className="topbar">
      {/* Breadcrumb */}
      <div className="topbar__breadcrumb">
        <button
          className="topbar__breadcrumb-item topbar__breadcrumb-item--home"
          onClick={onNavigateRoot}
        >
          Home
        </button>
        {breadcrumbStack.map((crumb, i) => (
          <span key={crumb.id || crumb.path} className="topbar__breadcrumb-segment">
            <ChevronRight size={12} className="topbar__breadcrumb-sep" />
            <button
              className={`topbar__breadcrumb-item ${i === breadcrumbStack.length - 1 ? 'topbar__breadcrumb-item--current' : ''}`}
              onClick={() => onNavigateBreadcrumb(i)}
            >
              {crumb.name}
            </button>
          </span>
        ))}
      </div>

      {/* Search */}
      <div className="topbar__search">
        <Search size={14} className="topbar__search-icon" />
        <input
          type="text"
          className="topbar__search-input"
          placeholder="Search files..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <kbd className="topbar__search-kbd">⌘K</kbd>
      </div>

      {/* Right actions */}
      <div className="topbar__actions">
        <button className="topbar__action-btn" aria-label="Notifications">
          <Bell size={17} />
        </button>
        <button className="topbar__avatar" aria-label="User menu">
          <span>U</span>
        </button>
      </div>
    </header>
  )
}
