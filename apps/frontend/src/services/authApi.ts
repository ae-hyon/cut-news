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
  return api<AuthStartResponse>('/v1/auth/oauth/kakao/authorization', {
    method: 'POST',
  });
}

export function getSession() {
  return api<AuthSessionResponse>('/v1/me');
}

export function postRefresh() {
  return api<AuthSessionResponse>('/v1/auth/token/refresh', { method: 'POST' });
}

export function postLogout() {
  return api<AuthLogoutResponse>('/v1/auth/session', { method: 'DELETE' });
}

export function saveUserPreference(payload: PreferencePayload) {
  return api<UserPreference>('/v1/me/preference', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function updateUserPreference(payload: PreferencePayload) {
  return api<UserPreference>('/v1/me/preference', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
