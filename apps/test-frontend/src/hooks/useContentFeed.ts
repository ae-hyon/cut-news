import React from 'react'
import type { ArticleCard, ArticleDetail, FeedResponse } from '../lib/types'
import { addScrap, getArticleDetail, getUserFeed, getUserScraps, removeScrap } from '../services/backendApi'

export function useContentFeed() {
  const [feed, setFeed] = React.useState<FeedResponse | null>(null)
  const [scraps, setScraps] = React.useState<ArticleCard[]>([])
  const [selectedArticle, setSelectedArticle] = React.useState<ArticleDetail | null>(null)

  const clearContent = React.useCallback(() => {
    setFeed(null)
    setScraps([])
    setSelectedArticle(null)
  }, [])

  const loadContent = React.useCallback(async (userId: string) => {
    const [feedData, scrapsData] = await Promise.all([
      getUserFeed(userId),
      getUserScraps(userId),
    ])
    setFeed(feedData)
    setScraps(scrapsData.items || [])
    return { feed: feedData, scraps: scrapsData.items || [] }
  }, [])

  const openArticle = React.useCallback(async (articleId: string, userId?: string | null) => {
    const detail = await getArticleDetail(articleId, userId)
    setSelectedArticle(detail)
    return detail
  }, [])

  const refreshSelectedArticle = React.useCallback(async (articleId: string, userId?: string | null) => {
    const detail = await getArticleDetail(articleId, userId)
    setSelectedArticle(detail)
    return detail
  }, [])

  const toggleScrap = React.useCallback(async (userId: string, article: ArticleCard | ArticleDetail) => {
    if (article.is_scrapped) await removeScrap(userId, article.id)
    else await addScrap(userId, article.id)
  }, [])

  return {
    feed,
    scraps,
    selectedArticle,
    setSelectedArticle,
    clearContent,
    loadContent,
    openArticle,
    refreshSelectedArticle,
    toggleScrap,
  }
}

export type ContentFeedState = ReturnType<typeof useContentFeed>
