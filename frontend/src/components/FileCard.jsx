import {
  Folder, Image, Video, Music, FileText, Table, Presentation, Archive, Code, File,
} from 'lucide-react'
import '../styles/FileCard.css'

const CATEGORY_ICONS = {
  folder: Folder, image: Image, video: Video, audio: Music,
  pdf: FileText, document: FileText, spreadsheet: Table,
  presentation: Presentation, archive: Archive, code: Code, other: File,
}

const CATEGORY_COLORS = {
  folder: '#eab308', image: '#22c55e', video: '#ef4444', audio: '#a855f7',
  pdf: '#ef4444', document: '#3b82f6', spreadsheet: '#22c55e',
  presentation: '#f97316', code: '#6366f1', archive: '#8b5cf6', other: '#6b7280',
}

export function FileCard({ file, viewMode = 'grid', providers = [], onOpen, onContextMenu }) {
  const category = file.category || 'other'
  const isFolder = file.is_folder
  const CategoryIcon = CATEGORY_ICONS[category] || CATEGORY_ICONS.other
  const accentColor = CATEGORY_COLORS[category] || CATEGORY_COLORS.other

  const hasGoogle = providers.includes('google')
  const hasOnedrive = providers.includes('onedrive')
  const isMerged = providers.length > 1

  let dotClass = 'file-card__dot--google'
  let dotTitle = 'Google Drive'
  if (isMerged) { dotClass = 'file-card__dot--merged'; dotTitle = 'Google Drive + OneDrive' }
  else if (hasOnedrive) { dotClass = 'file-card__dot--onedrive'; dotTitle = 'OneDrive' }

  const handleClick = (e) => {
    e.preventDefault(); e.stopPropagation()
    if (onOpen) onOpen(file)
  }

  const handleContextMenu = (e) => {
    e.preventDefault(); e.stopPropagation()
    if (onContextMenu) onContextMenu(e, file)
  }

  if (viewMode === 'list') {
    return (
      <div className="file-card file-card--list" onClick={handleClick} onContextMenu={handleContextMenu}>
        <div className={`file-card__dot ${dotClass}`} title={dotTitle} />
        <CategoryIcon size={20} className="file-card__list-icon" color="#8a8a8a" />
        <span className="file-card__list-name">{file.name}</span>
        <span className="file-card__list-meta">
          {isFolder && file.item_count != null ? `${file.item_count} items` : file.size_formatted || ''}
        </span>
        <span className="file-card__list-time">{file.modified_time_formatted || ''}</span>
      </div>
    )
  }

  return (
    <article className="file-card file-card--grid" onClick={handleClick} onContextMenu={handleContextMenu}>
      {/* Source dot */}
      <div className={`file-card__dot ${dotClass}`} title={dotTitle} />

      {/* Thumbnail */}
      <div className="file-card__preview">
        {category === 'image' && file.thumbnail_link ? (
          <img src={file.thumbnail_link} alt={file.name} loading="lazy" className="file-card__thumb-img" />
        ) : category === 'video' && file.thumbnail_link ? (
          <div className="file-card__thumb-video">
            <img src={file.thumbnail_link} alt={file.name} loading="lazy" className="file-card__thumb-img" />
            <div className="file-card__play-btn"><div className="file-card__play-triangle" /></div>
          </div>
        ) : (
          <div className="file-card__icon-area">
            <CategoryIcon size={36} strokeWidth={1.5} color="#8a8a8a" />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="file-card__footer">
        <span className="file-card__name" title={file.name}>{file.name}</span>
        <span className="file-card__meta">
          {isFolder && file.item_count != null
            ? `${file.item_count} item${file.item_count !== 1 ? 's' : ''}`
            : file.size_formatted || ''
          }
          {file.modified_time_formatted && <> · {file.modified_time_formatted}</>}
        </span>
      </div>
    </article>
  )
}
