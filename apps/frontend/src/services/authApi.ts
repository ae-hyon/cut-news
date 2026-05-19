import { api } from '@/lib/api';
import type {
  AuthStartResponse,
  AuthSessionResponse,
  AuthLogoutResponse,
  UserPreference,
  PreferenceMode,
} from '@/lib/types';

export interface PreferencePayload {
  mode: PreferenceMode;
  primary_categories: string[];
  subcategories: string[];
}

export function getKakaoStart() {
  return api<AuthStartResponse>('/v1/auth/kakao/start');
}

export function getSession() {
  return api<AuthSessionResponse>('/v1/auth/session');
}

export function postRefresh() {
  return api<AuthSessionResponse>('/v1/auth/refresh', { method: 'POST' });
}

export function postLogout() {
  return api<AuthLogoutResponse>('/v1/auth/logout', { method: 'POST' });
}

export function saveUserPreference(userId: string, payload: PreferencePayload) {
  return api<UserPreference>(`/v1/users/${userId}/preferences`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}
