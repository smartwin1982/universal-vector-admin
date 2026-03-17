/**
 * Auth state management
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/api';

interface AuthState {
  token: string | null;
  username: string | null;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      username: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        const { data } = await api.post('/api/auth/login', { username, password });
        set({
          token: data.access_token,
          username: data.username,
          isAuthenticated: true,
        });
        // Set default auth header
        api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
      },

      register: async (username: string, password: string) => {
        const { data } = await api.post('/api/auth/register', { username, password });
        set({
          token: data.access_token,
          username: data.username,
          isAuthenticated: true,
        });
        api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
      },

      logout: () => {
        set({ token: null, username: null, isAuthenticated: false });
        delete api.defaults.headers.common['Authorization'];
      },
    }),
    {
      name: 'uva-auth-store',
      onRehydrateStorage: () => (state) => {
        // Restore auth header on rehydration
        if (state?.token) {
          api.defaults.headers.common['Authorization'] = `Bearer ${state.token}`;
        }
      },
    }
  )
);
