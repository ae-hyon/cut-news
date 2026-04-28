import React from 'react'
import NewsCard from '../common/NewsCard'
import type { ArticleCard } from '../../lib/types'

interface ScrapsScreenProps {
  scraps: ArticleCard[]
  onOpenArticle: (articleId: string) => void
  onToggleScrap: (article: ArticleCard) => void
}

export default function ScrapsScreen({ scraps, onOpenArticle, onToggleScrap }: ScrapsScreenProps) {
  return (
    <section className="screen list-screen scraps-screen">
      <div className="scraps-context-row">
        <span>저장한 뉴스</span>
        <strong>{scraps.length}개</strong>
      </div>
      {scraps.length === 0 ? <p className="empty-state">아직 스크랩한 기사가 없어요.</p> : (
        <div className="pdf-card-board scraps-card-board">
          {scraps.map((article, idx) => (
            <NewsCard
              key={article.id}
              article={article}
              index={idx}
              size={idx % 4 === 0 ? 'feature' : idx % 3 === 0 ? 'compact' : 'regular'}
              onOpenArticle={onOpenArticle}
              onToggleScrap={onToggleScrap}
              scrappedOverride={true}
            />
          ))}
        </div>
      )}
    </section>
  )
}
