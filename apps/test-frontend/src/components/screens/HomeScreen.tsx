import React from 'react'
import NewsCard from '../common/NewsCard'
import type { ArticleCard, FeedResponse, UserPreference } from '../../lib/types'

interface HomeScreenProps {
  preference: UserPreference | null
  feed: FeedResponse | null
  onOpenArticle: (articleId: string) => void
  onToggleScrap: (article: ArticleCard) => void
}

export default function HomeScreen({ preference, feed, onOpenArticle, onToggleScrap }: HomeScreenProps) {
  const articles = (feed?.blocks.flatMap((block) => block.articles) ?? []).slice(0, 6)
  const modeLabel = preference?.mode === 'narrow' ? '깊게 보기' : '전체'

  return (
    <section className="screen home-screen">
      <div className="home-filter-row">
        <span>{modeLabel}</span>
        <button>선택</button>
      </div>
      {!articles.length ? (
        <div className="empty-state">관심사를 선택하면 뉴스가 표시됩니다.</div>
      ) : (
        <div className="pdf-card-board home-card-board">
          {articles.map((article, index) => (
            <NewsCard
              key={`${article.id}-${index}`}
              article={article}
              index={index}
              size={index === 1 || index === 4 ? 'feature' : index === 3 ? 'compact' : 'regular'}
              onOpenArticle={onOpenArticle}
              onToggleScrap={onToggleScrap}
            />
          ))}
        </div>
      )}
    </section>
  )
}
