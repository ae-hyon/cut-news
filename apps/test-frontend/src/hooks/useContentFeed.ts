import React from 'react'
import type { ArticleCard, ArticleDetail, FeedResponse } from '../lib/types'
import { addScrap, getArticleDetail, getUserFeed, getUserScraps, removeScrap } from '../services/backendApi'

function updateArticleCard<T extends ArticleCard>(article: T, articleId: string, nextScrapped: boolean): T {
  if (article.id !== articleId) return article
  return { ...article, is_scrapped: nextScrapped }
}

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

  const applyScrapState = React.useCallback((articleId: string, nextScrapped: boolean) => {
    setFeed((currentFeed) => currentFeed ? {
      ...currentFeed,
      blocks: currentFeed.blocks.map((block) => ({
        ...block,
        articles: block.articles.map((article) => updateArticleCard(article, articleId, nextScrapped)),
      })),
    } : currentFeed)

    setScraps((currentScraps) => {
      const withoutArticle = currentScraps.filter((article) => article.id !== articleId)
      if (!nextScrapped) return withoutArticle

      const fromFeed = feed?.blocks.flatMap((block) => block.articles).find((article) => article.id === articleId)
      const fromSelectedArticle = selectedArticle?.id === articleId ? selectedArticle : null
      const sourceArticle = fromSelectedArticle ?? fromFeed
      if (!sourceArticle) return withoutArticle

      return [{ ...sourceArticle, is_scrapped: true }, ...withoutArticle]
    })

    setSelectedArticle((currentArticle) => currentArticle && currentArticle.id === articleId
      ? { ...currentArticle, is_scrapped: nextScrapped }
      : currentArticle)
  }, [feed, selectedArticle])

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
    applyScrapState,
    toggleScrap,
  }
}

export type ContentFeedState = ReturnType<typeof useContentFeed>
