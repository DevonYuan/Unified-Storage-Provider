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
  onOpen,
}) {
  const category = file.category
  const isFolder = file.is_folder
  const CategoryIcon = getCategoryIcon(category)

  const handleClick = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isFolder && onOpen) {
      onOpen(file.id)
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
      <div className="file-card__origin" title="Google Drive" />

      {/* Card content */}
      <div className={contentClass}>
        {isFolder ? (
          // Folder: icon centered
          <div className="file-card__icon-wrapper">
            <CategoryIcon size={iconSize} />
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
            <CategoryIcon size={iconSize} />
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