export type SessionState = 'anonymous' | 'authenticated' | 'onboarded';
export type AuthProvider = 'none' | 'demo' | 'kakao';
export type PreferenceMode = 'wide' | 'narrow';

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export interface AuthStartResponse {
  provider: 'kakao';
  state: string;
  authorization_url: string;
}

export interface UserPreferenceSnapshot {
  mode: PreferenceMode;
  primary_categories: string[];
  subcategories: string[];
}

export interface AuthSessionResponse {
  user_id: string | null;
  session_state: SessionState;
  onboarding_completed: boolean;
  authenticated: boolean;
  auth_provider: AuthProvider;
  provider_subject?: string | null;
  preference: UserPreferenceSnapshot | null;
}

export interface AuthLogoutResponse {
  ok: boolean;
}

export interface Subcategory {
  id?: number;
  slug: string;
  name: string;
  description: string;
  category_slug?: string;
}

export interface Category {
  id?: number;
  slug: string;
  name: string;
  description: string;
  subcategories: Subcategory[];
}

export interface UserPreference {
  user_id: string;
  mode: PreferenceMode;
  primary_categories: string[];
  subcategories: string[];
  onboarding_completed: boolean;
}

export interface ArticleCard {
  id: string;
  title: string;
  summary: string;
  primary_category: string;
  subcategory: string;
  published_at: string;
  original_url: string;
  is_scrapped: boolean;
}

export interface ArticleDetail extends ArticleCard {
  content: string;
}

export interface FeedBlock {
  key: string;
  title: string;
  weight: number;
  articles: ArticleCard[];
}

export interface FeedResponse {
  user_id: string;
  snapshot_id: number;
  feed_date: string;
  status: string;
  read_count: number;
  total_count: number;
  mode: PreferenceMode;
  blocks: FeedBlock[];
}

export interface ScrapResponse {
  user_id: string;
  items: ArticleCard[];
}

export interface ArchiveDay {
  date: string;
  snapshot_id: number;
  status: string;
  has_feed: boolean;
  count: number;
  total_count: number;
  read_count: number;
  first_viewed_at: string | null;
  completed_at: string | null;
}

export interface ArchiveMonthResponse {
  user_id: string;
  month: string;
  days: ArchiveDay[];
}

export interface ArchiveDateResponse {
  user_id: string;
  date: string;
  snapshot_id: number;
  status: string;
  read_count: number;
  total_count: number;
  items: ArticleCard[];
}
