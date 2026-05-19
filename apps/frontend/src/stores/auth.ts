import { create } from 'zustand';
import type { AuthSessionResponse } from '@/lib/types';
import { getSession, postRefresh, postLogout } from '@/services/authApi';

interface AuthStore {
  session: AuthSessionResponse | null;
  userId: string | null;
  isLoading: boolean;
  error: string | null;

  setSession: (session: AuthSessionResponse) => void;
  clearSession: () => void;
  checkSession: () => Promise<AuthSessionResponse>;
  refreshSession: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()((set) => ({
  session: null,
  userId: null,
  isLoading: false,
  error: null,

  setSession: (session) =>
    set({
      session,
      userId: session.user_id,
      error: null,
    }),

  clearSession: () =>
    set({
      session: null,
      userId: null,
      error: null,
    }),

  checkSession: async () => {
    set({ isLoading: true, error: null });
    try {
      const session = await getSession();
      set({
        session,
        userId: session.user_id,
        isLoading: false,
      });
      return session;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  refreshSession: async () => {
    try {
      const session = await postRefresh();
      set({
        session,
        userId: session.user_id,
      });
    } catch {
      set({ session: null, userId: null });
    }
  },

  logout: async () => {
    await postLogout();
    set({
      session: null,
      userId: null,
      error: null,
    });
  },
}));
