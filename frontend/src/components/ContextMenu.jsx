import { useEffect, useRef, useCallback } from 'react'
import { Pencil, Trash2, Download } from 'lucide-react'
import '../styles/ContextMenu.css'

export function ContextMenu({ x, y, file, onClose, onRename, onDelete, onDownload }) {
  const menuRef = useRef(null)
  const isFolder = file?.is_folder

  // Close on Escape
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }, [onClose])

  // Close on click outside
  const handleClickOutside = useCallback((e) => {
    if (menuRef.current && !menuRef.current.contains(e.target)) {
      onClose()
    }
  }, [onClose])

  // Close on scroll
  const handleScroll = useCallback(() => {
    onClose()
  }, [onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('scroll', handleScroll, true)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('scroll', handleScroll, true)
    }
  }, [handleKeyDown, handleClickOutside, handleScroll])

  // Adjust position to stay within viewport
  const adjustedX = Math.min(x, window.innerWidth - 180)
  const adjustedY = Math.min(y, window.innerHeight - 140)

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{ left: adjustedX, top: adjustedY }}
      role="menu"
      tabIndex={-1}
    >
      <div className="context-menu__header">
        <span className="context-menu__filename" title={file?.name}>
          {file?.name}
        </span>
      </div>

      <button
        className="context-menu__item"
        onClick={() => { onRename(file); onClose() }}
        role="menuitem"
      >
        <Pencil size={14} className="context-menu__icon" />
        <span>Rename</span>
      </button>

      {!isFolder && (
        <button
          className="context-menu__item"
          onClick={() => { onDownload(file); onClose() }}
          role="menuitem"
        >
          <Download size={14} className="context-menu__icon" />
          <span>Download</span>
        </button>
      )}

      <div className="context-menu__divider" />

      <button
        className="context-menu__item context-menu__item--danger"
        onClick={() => { onDelete(file); onClose() }}
        role="menuitem"
      >
        <Trash2 size={14} className="context-menu__icon" />
        <span>Delete</span>
      </button>
    </div>
  )
}
