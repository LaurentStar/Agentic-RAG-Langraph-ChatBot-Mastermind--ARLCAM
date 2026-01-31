import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { UserInfo } from '@/types';
import { STORAGE_KEYS } from '@/lib/constants';
import { getSession, logoutUser } from '@/lib/api/auth';
import log from '@/lib/logger';

interface AuthState {
  // State
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isHydrated: boolean;
  error: string | null;

  // Actions
  setUser: (user: UserInfo | null) => void;
  setLoading: (loading: boolean) => void;
  setHydrated: (hydrated: boolean) => void;
  setError: (error: string | null) => void;
  login: (user: UserInfo) => void;
  logout: () => Promise<void>;
  checkSession: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      isLoading: true,  // Start loading until session checked
      isHydrated: false,
      error: null,

      // Actions
      setUser: (user) => {
        set({ user, isAuthenticated: !!user });
      },

      setLoading: (isLoading) => set({ isLoading }),

      setHydrated: (isHydrated) => set({ isHydrated }),

      setError: (error) => {
        if (error) {
          log.error('Auth error:', error);
        }
        set({ error, isLoading: false });
      },

      login: (user) => {
        log.info('User logged in:', user.display_name);
        set({
          user,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
      },

      logout: async () => {
        try {
          await logoutUser();
        } catch (e) {
          log.warn('Logout API call failed:', e);
        }
        log.info('User logged out');
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      checkSession: async () => {
        log.debug('Checking session with server');
        set({ isLoading: true });
        
        try {
          const user = await getSession();
          set({
            user,
            isAuthenticated: !!user,
            isLoading: false,
          });
          
          if (user) {
            log.debug('Session valid for:', user.display_name);
          }
        } catch (error) {
          log.error('Session check failed:', error);
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: STORAGE_KEYS.AUTH,
      partialize: (state) => ({
        // Only persist user info for quick UI hydration
        // Actual auth is validated via cookie on checkSession
        user: state.user,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
      },
    }
  )
);

// Selector hooks for common use cases
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useUser = () => useAuthStore((state) => state.user);
export const useAuthError = () => useAuthStore((state) => state.error);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);

// Legacy compatibility
export const usePlayer = () => useAuthStore((state) => state.user);
