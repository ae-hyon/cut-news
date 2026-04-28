import React from 'react'
import { toCategoryLabel } from '../../lib/constants'
import { formatDateLabel } from '../../lib/dateLabel'
import type { ArticleDetail } from '../../lib/types'

interface DetailScreenProps {
  article: ArticleDetail
  onBack: () => void
  onToggleScrap: (article: ArticleDetail) => void
}

export default function DetailScreen({ article, onBack, onToggleScrap }: DetailScreenProps) {
  return (
    <section className="screen detail-screen">
      <header className="pdf-topbar detail-topbar">
        <div className="brand-block static">
          <strong>Annoying Cap</strong>
          <span>{formatDateLabel()}</span>
        </div>
        <button className="detail-close-button" onClick={onBack} aria-label="상세 닫기">×</button>
      </header>
      <article className="detail-article">
        <div className="detail-summary-card">
          <p>{article.summary}</p>
        </div>
        <div className="detail-meta-row">
          <span>{article.published_at}</span>
          <span>{toCategoryLabel(article.primary_category)} · {article.subcategory}</span>
        </div>
        <h2>{article.title}</h2>
        <p className="detail-body-text">{article.content}</p>
        <div className="detail-action-row">
          <a className="detail-ghost-button" href={article.original_url} target="_blank" rel="noreferrer">원문 보기</a>
          <button className="detail-ghost-button" onClick={() => onToggleScrap(article)}>{article.is_scrapped ? '스크랩 해제' : '스크랩'}</button>
        </div>
      </article>
    </section>
  )
}
