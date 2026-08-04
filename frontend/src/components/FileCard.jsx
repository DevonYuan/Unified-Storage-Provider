import {
  Folder,
  Image,
  Video,
  Music,
  FileText,
  Table,
  Presentation,
  Archive,
  Code,
  File,
} from 'lucide-react'
import '../styles/FileCard.css'

function getCategoryIcon(category) {
  const icons = {
    folder: Folder,
    image: Image,
    video: Video,
    audio: Music,
    pdf: FileText,
    document: FileText,
    spreadsheet: Table,
    presentation: Presentation,
    archive: Archive,
    code: Code,
    other: File,
  }
  return icons[category] || icons.other
}

export function FileCard({
  file,
  viewMode = 'grid',
  providers = ['google'],
  onOpen,
}) {
  const category = file.category
  const isFolder = file.is_folder
  const CategoryIcon = getCategoryIcon(category)

  // Determine origin indicator class
  const isMerged = providers.length > 1
  const hasGoogle = providers.includes('google')
  const hasOnedrive = providers.includes('onedrive')

  let originClass = 'file-card__origin--google'
  let originTitle = 'Google Drive'
  if (isMerged) {
    originClass = 'file-card__origin--merged'
    originTitle = 'Google Drive + OneDrive (merged)'
  } else if (hasOnedrive) {
    originClass = 'file-card__origin--onedrive'
    originTitle = 'OneDrive'
  }

  const handleClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (onOpen) {
      onOpen(file)
    }
  }

  const iconSize = viewMode === 'list' ? 24 : 64
  const contentClass = viewMode === 'list' ? 'file-card__content--list' : 'file-card__content'

  return (
    <article
      className={`file-card ${viewMode === 'list' ? 'file-card--list' : 'file-card--grid'}`}
      onClick={handleClick}
    >
      {/* Origin indicator - top left */}
      <div
        className={`file-card__origin ${originClass}`}
        title={originTitle}
      />

      {/* Card content */}
      <div className={contentClass}>
        {isFolder ? (
          // Folder: icon centered
          <div className="file-card__icon-wrapper">
            <CategoryIcon className="file-card__category-icon" size={iconSize} />
          </div>
        ) : file.category === 'image' && file.thumbnail_link ? (
          // Image: thumbnail top half
          <div className="file-card__thumbnail">
            <img
              src={file.thumbnail_link}
              alt={file.name}
              loading="lazy"
            />
          </div>
        ) : (
          // Other files: icon centered
          <div className="file-card__icon-wrapper">
            <CategoryIcon className="file-card__category-icon" size={iconSize} />
          </div>
        )}

        {/* File/Folder info */}
        <div className="file-card__info">
          <h3 className="file-card__name" title={file.name}>{file.name}</h3>
          <div className="file-card__meta">
            {file.size_formatted && !isFolder && (
              <span className="file-card__size">{file.size_formatted}</span>
            )}
            {isFolder && file.item_count !== null && file.item_count !== undefined && (
              <span className="file-card__count">{file.item_count} item{file.item_count !== 1 ? 's' : ''}</span>
            )}
            {file.modified_time_formatted && (
              <span className="file-card__time">{file.modified_time_formatted}</span>
            )}
          </div>
        </div>
      </div>
    </article>
  )
}