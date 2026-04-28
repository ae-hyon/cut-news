import React from 'react'
import { CARD_TONES, toCategoryLabel } from '../../lib/constants'
import type { ArticleCard } from '../../lib/types'

interface NewsCardProps {
  article: ArticleCard
  index?: number
  onOpenArticle: (articleId: string) => void
  onToggleScrap: (article: ArticleCard) => void
  scrappedOverride?: boolean | null
  size?: 'regular' | 'feature' | 'compact'
}

export default function NewsCard({ article, index = 0, onOpenArticle, onToggleScrap, scrappedOverride = null, size = 'regular' }: NewsCardProps) {
  const tone = CARD_TONES[index % CARD_TONES.length]
  const scrapped = scrappedOverride ?? article.is_scrapped

  return (
    <article className={`news-card ${tone} size-${size}`}>
      <button className="card-scrap" onClick={() => onToggleScrap(article)}>{scrapped ? '저장됨' : '스크랩'}</button>
      <button className="card-body-button" onClick={() => onOpenArticle(article.id)} aria-label={`${article.title} 상세 보기`}>
        <span>{toCategoryLabel(article.primary_category)}</span>
        <strong>{article.title}</strong>
        <em>{article.summary}</em>
      </button>
    </article>
  )
}
