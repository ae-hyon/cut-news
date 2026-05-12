import { api } from '../lib/api'
import type {
  ArticleDetail,
  AuthLogoutResponse,
  AuthSessionResponse,
  AuthStartResponse,
  Category,
  FeedResponse,
  HealthResponse,
  PreferenceMode,
  ScrapResponse,
  UserPreference,
} from '../lib/types'

export interface PreferencePayload {
  mode: PreferenceMode
  primary_categories: string[]
  subcategories: string[]
}

export function getHealth() {
  return api<HealthResponse>('/health')
}

export function getCategories() {
  return api<Category[]>('/v1/categories')
}

export function getAnonymousSession() {
  return api<AuthSessionResponse>('/v1/auth/session')
}

export function getUserSession(userId: string) {
  return api<AuthSessionResponse>(`/v1/auth/session?user_id=${userId}`)
}

export function getKakaoStart() {
  return api<AuthStartResponse>('/v1/auth/kakao/start')
}

export function postLogout() {
  return api<AuthLogoutResponse>('/v1/auth/logout', { method: 'POST' })
}

export function getUserPreference(userId: string) {
  return api<UserPreference>(`/v1/users/${userId}/preferences`)
}

export function saveUserPreference(userId: string, payload: PreferencePayload) {
  return api<UserPreference>(`/v1/users/${userId}/preferences`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function getUserFeed(userId: string) {
  return api<FeedResponse>(`/v1/users/${userId}/feed`)
}

export function getUserScraps(userId: string) {
  return api<ScrapResponse>(`/v1/users/${userId}/scraps`)
}

export function getArticleDetail(articleId: string, userId?: string | null) {
  const suffix = userId ? `?user_id=${userId}` : ''
  return api<ArticleDetail>(`/v1/articles/${articleId}${suffix}`)
}

export function addScrap(userId: string, articleId: string) {
  return api<void>(`/v1/users/${userId}/scraps/${articleId}`, { method: 'PUT' })
}

export function removeScrap(userId: string, articleId: string) {
  return api<void>(`/v1/users/${userId}/scraps/${articleId}`, { method: 'DELETE' })
}

