import { api } from '@/lib/api';
import type {
  ArchiveDateResponse,
  ArchiveMonthResponse,
  ArticleCard,
  ArticleDetail,
  FeedResponse,
  ScrapResponse,
} from '@/lib/types';
import type { BlockSize, NewsItem } from '@/types';

function blockSizeForIndex(index: number): BlockSize {
  if (index % 5 === 0) return 'large';
  if (index % 3 === 0) return 'small';
  return 'medium';
}

export function mapArticleToNewsItem(
  article: ArticleCard,
  index = 0,
): NewsItem {
  return {
    id: article.id,
    title: article.title,
    summary: article.summary,
    category: article.primary_category,
    sourceUrl: article.original_url,
    publishedAt: article.published_at,
    blockSize: blockSizeForIndex(index),
    isScrapped: article.is_scrapped,
  };
}

export function getMyFeed() {
  return api<FeedResponse>('/v1/me/feed');
}

export function getMyArticle(articleId: string) {
  return api<ArticleDetail>(`/v1/me/articles/${articleId}`);
}

export function getMyScraps() {
  return api<ScrapResponse>('/v1/me/scraps');
}

export function addMyScrap(articleId: string) {
  return api<{ user_id: string; article_id: string; scrapped: boolean }>(
    `/v1/me/scraps/${articleId}`,
    { method: 'PUT' },
  );
}

export function removeMyScrap(articleId: string) {
  return api<{ user_id: string; article_id: string; scrapped: boolean }>(
    `/v1/me/scraps/${articleId}`,
    { method: 'DELETE' },
  );
}

export function getMyArchiveMonth(month: string) {
  return api<ArchiveMonthResponse>(
    `/v1/me/archive?month=${encodeURIComponent(month)}`,
  );
}

export function getMyArchiveDate(date: string) {
  return api<ArchiveDateResponse>(`/v1/me/archive/${date}`);
}
