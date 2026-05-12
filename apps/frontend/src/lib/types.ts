export type SessionState = 'anonymous' | 'authenticated' | 'onboarded'
export type AuthProvider = 'none' | 'demo' | 'kakao'
export type PreferenceMode = 'wide' | 'narrow'

export interface HealthResponse {
  status: string
  app: string
  version: string
}

export interface AuthStartResponse {
  provider: 'kakao'
  state: string
  authorization_url: string
}

export interface AuthSessionResponse {
  user_id: string | null
  session_state: SessionState
  onboarding_completed: boolean
  authenticated: boolean
  auth_provider: AuthProvider
  provider_subject?: string | null
}

export interface AuthLogoutResponse {
  ok: boolean
}

export interface Subcategory {
  id?: number
  slug: string
  name: string
  description: string
  category_slug?: string
}

export interface Category {
  id?: number
  slug: string
  name: string
  description: string
  subcategories: Subcategory[]
}

export interface UserPreference {
  user_id: string
  mode: PreferenceMode
  primary_categories: string[]
  subcategories: string[]
  onboarding_completed: boolean
}

export interface ArticleCard {
  id: string
  title: string
  summary: string
  primary_category: string
  subcategory: string
  published_at: string
  original_url: string
  is_scrapped: boolean
}

export interface ArticleDetail extends ArticleCard {
  content: string
}

export interface FeedBlock {
  key: string
  title: string
  weight: number
  articles: ArticleCard[]
}

export interface FeedResponse {
  user_id: string
  mode: PreferenceMode
  blocks: FeedBlock[]
}

export interface ScrapResponse {
  user_id: string
  items: ArticleCard[]
}

export interface ArchiveDay {
  date: string
  count?: number
  items: ArticleCard[]
}

export interface ArchiveMonthResponse {
  user_id: string
  month: string
  days: ArchiveDay[]
}

export interface ArchiveDateResponse {
  user_id: string
  date: string
  items: ArticleCard[]
}
