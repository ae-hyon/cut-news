import React from 'react'
import { toCategoryLabel, toSubcategoryLabel } from '../../lib/constants'
import { formatDateLabel } from '../../lib/dateLabel'
import type { ArticleDetail } from '../../lib/types'

interface DetailScreenProps {
  article: ArticleDetail
  onBack: () => void
  onToggleScrap: (article: ArticleDetail) => void
  onEditPreference?: () => void
  onLogout?: () => void
  showPreferenceMismatchNotice?: boolean
}

export default function DetailScreen({ article, onBack, onToggleScrap, onEditPreference, onLogout, showPreferenceMismatchNotice = false }: DetailScreenProps) {
  return (
    <section className="screen detail-screen">
      <header className="pdf-topbar detail-topbar">
        <div className="brand-block static">
          <strong>Annoying Cap</strong>
          <span>{formatDateLabel()}</span>
        </div>
        <div className="detail-header-actions">
          <button className="profile-pill profile-pill-muted detail-profile-pill" type="button" aria-label="로그아웃" onClick={onLogout}>로그아웃</button>
          <button className="profile-pill detail-profile-pill" type="button" aria-label="관심 분야 편집" onClick={onEditPreference}>관심 분야 수정</button>
          <button className="detail-close-button" onClick={onBack} aria-label="상세 닫기">×</button>
        </div>
      </header>
      <article className="detail-article">
        <div className="detail-summary-card">
          <p>{article.summary}</p>
        </div>
        <div className="detail-meta-row">
          <span>{article.published_at}</span>
          <span>{toCategoryLabel(article.primary_category)} · {toSubcategoryLabel(article.subcategory)}</span>
        </div>
        {showPreferenceMismatchNotice && (
          <p className="screen-helper-text detail-preference-mismatch">
            이 기사는 현재 관심사 밖에 있지만, 저장하거나 원문으로 계속 확인할 수 있어요.
          </p>
        )}
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
