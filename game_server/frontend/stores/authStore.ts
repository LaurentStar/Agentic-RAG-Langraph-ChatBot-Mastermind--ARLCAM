import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Player, AuthResponse, LoginRequest } from '@/types';
import { STORAGE_KEYS } from '@/lib/constants';
import log from '@/lib/logger';

interface AuthState {
  // State
  accessToken: string | null;
  refreshToken: string | null;
  player: Player | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setTokens: (accessToken: string, refreshToken: string) => void;
  setPlayer: (player: Player) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  login: (response: AuthResponse, player?: Player) => void;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      accessToken: null,
      refreshToken: null,
      player: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      setTokens: (accessToken, refreshToken) => {
        log.debug('Setting tokens');
        set({ 
          accessToken, 
          refreshToken, 
          isAuthenticated: true,
          error: null,
        });
      },

      setPlayer: (player) => {
        log.debug('Setting player:', player.display_name);
        set({ player });
      },

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => {
        if (error) {
          log.error('Auth error:', error);
        }
        set({ error, isLoading: false });
      },

      login: (response, player) => {
        log.info('User logged in');
        set({
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
          player: player || null,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      },

      logout: () => {
        log.info('User logged out');
        set({
          accessToken: null,
          refreshToken: null,
          player: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: STORAGE_KEYS.AUTH,
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        player: state.player,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// Selector hooks for common use cases
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const usePlayer = () => useAuthStore((state) => state.player);
export const useAuthError = () => useAuthStore((state) => state.error);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
