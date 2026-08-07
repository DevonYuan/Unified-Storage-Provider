import { useEffect, useRef, useCallback } from 'react'
import { Pencil, Trash2, Download, Scissors, Copy, ClipboardPaste } from 'lucide-react'
import '../styles/ContextMenu.css'

export function ContextMenu({ x, y, file, clipboardCount, onClose, onRename, onDelete, onDownload, onCut, onCopy, onPaste }) {
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
    // Defer mousedown listener so the right-click that opened the menu
    // doesn't immediately dismiss it via click-outside detection.
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside)
    }, 0)
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('scroll', handleScroll, true)
    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
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
      {file ? (
        <>
          <div className="context-menu__header">
            <span className="context-menu__filename" title={file.name}>
              {file.name}
            </span>
          </div>

          <button
            className="context-menu__item"
            onClick={() => { onCut(file); onClose() }}
            role="menuitem"
          >
            <Scissors size={14} className="context-menu__icon" />
            <span>Cut</span>
          </button>

          <button
            className="context-menu__item"
            onClick={() => { onCopy(file); onClose() }}
            role="menuitem"
          >
            <Copy size={14} className="context-menu__icon" />
            <span>Copy</span>
          </button>

          <div className="context-menu__divider" />

          {clipboardCount > 0 && (
            <button
              className="context-menu__item"
              onClick={() => { onPaste(); onClose() }}
              role="menuitem"
            >
              <ClipboardPaste size={14} className="context-menu__icon" />
              <span>Paste ({clipboardCount})</span>
            </button>
          )}

          <button
            className="context-menu__item"
            onClick={() => { onRename(file); onClose() }}
            role="menuitem"
          >
            <Pencil size={14} className="context-menu__icon" />
            <span>Rename</span>
          </button>

          <button
            className="context-menu__item"
            onClick={() => { onDownload(file); onClose() }}
            role="menuitem"
          >
            <Download size={14} className="context-menu__icon" />
            <span>{isFolder ? 'Download as ZIP' : 'Download'}</span>
          </button>

          <div className="context-menu__divider" />

          <button
            className="context-menu__item context-menu__item--danger"
            onClick={() => { onDelete(file); onClose() }}
            role="menuitem"
          >
            <Trash2 size={14} className="context-menu__icon" />
            <span>Delete</span>
          </button>
        </>
      ) : (
        /* Empty-area right-click — paste only */
        <button
          className="context-menu__item"
          onClick={() => { onPaste(); onClose() }}
          role="menuitem"
        >
          <ClipboardPaste size={14} className="context-menu__icon" />
          <span>Paste ({clipboardCount})</span>
        </button>
      )}
    </div>
  )
}
