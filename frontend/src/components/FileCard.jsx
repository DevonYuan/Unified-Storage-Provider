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
  Star,
  Star as StarFilled,
  HardDrive,
  Globe,
} from 'lucide-react'

function getCategoryIcon(category) {
  const icons = {
    folder: <Folder className="file-card__category-icon" size={48} />,
    image: <Image className="file-card__category-icon" size={48} />,
    video: <Video className="file-card__category-icon" size={48} />,
    audio: <Music className="file-card__category-icon" size={48} />,
    pdf: <FileText className="file-card__category-icon" size={48} />,
    document: <FileText className="file-card__category-icon" size={48} />,
    spreadsheet: <Table className="file-card__category-icon" size={48} />,
    presentation: <Presentation className="file-card__category-icon" size={48} />,
    archive: <Archive className="file-card__category-icon" size={48} />,
    code: <Code className="file-card__category-icon" size={48} />,
    other: <File className="file-card__category-icon" size={48} />,
  }
  return icons[category] || icons.other
}

export function FileCard({
  file,
  viewMode = 'grid',
  isFavorite = false,
  onFavoriteToggle,
  onNavigate,
  onOpen,
}) {
  const category = file.category
  const isFolder = file.is_folder
  const CategoryIcon = getCategoryIcon(category)

  const handleClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (isFolder && onNavigate) {
      onNavigate(file.id)
    } else if (!isFolder && onOpen) {
      onOpen(file.id)
    }
  }

  const handleFavoriteClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (onFavoriteToggle) {
      onFavoriteToggle(file.id)
    }
  }

  if (viewMode === 'list') {
    return (
      <div
        className="file-card file-card--list"
        onClick={handleClick}
      >
        <div className="file-card__origin" title="Google Drive" />
        <div className="file-card__icon-wrapper">
          <CategoryIcon size={24} />
        </div>
        <div className="file-card__info">
          <h3 className="file-card__name" title={file.name}>{file.name}</h3>
          <div className="file-card__meta">
            <span>{file.size_formatted || (isFolder ? `${file.item_count ?? 0} items` : '—')}</span>
            <span>{file.modified_time_formatted || '—'}</span>
          </div>
        </div>
        <button
          onClick={handleFavoriteClick}
          className={`file-card__favorite ${isFavorite ? 'file-card__favorite--active' : ''}`}
          aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          {isFavorite ? <StarFilled className="file-card__star-icon" size={16} /> : <Star className="file-card__star-icon" size={16} />}
        </button>
      </div>
    )
  }

  return (
    <article
      className="file-card file-card--grid"
      onClick={handleClick}
    >
      {/* Origin indicator - top left */}
      <div className="file-card__origin" title="Google Drive" />

      {/* Favorite star - top right */}
      <button
        onClick={handleFavoriteClick}
        className={`file-card__favorite ${isFavorite ? 'file-card__favorite--active' : ''}`}
        aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
      >
        {isFavorite ? <StarFilled className="file-card__star-icon" size={16} /> : <Star className="file-card__star-icon" size={16} />}
      </button>

      {/* Card content */}
      <div className="file-card__content">
        {isFolder ? (
          // Folder: icon centered
          <div className="file-card__icon-wrapper">
            <CategoryIcon size={64} />
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
            <CategoryIcon size={64} />
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