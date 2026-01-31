'use client';

import { useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import { getSession } from '@/lib/api/auth';
import { ROUTES } from '@/lib/constants';
import log from '@/lib/logger';

/**
 * OAuth Callback Page
 * 
 * This page handles the redirect from OAuth providers after successful authentication.
 * The backend has already set HTTP-only cookies with the tokens.
 * 
 * Flow:
 * 1. User completes OAuth with provider (Discord/Google/Slack)
 * 2. Backend sets cookies and redirects here
 * 3. This page fetches user info via /auth/session (cookies sent automatically)
 * 4. Updates Zustand store and redirects to /sessions
 */
export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, setError } = useAuthStore();
  const hasProcessed = useRef(false);

  const provider = searchParams.get('provider') || 'OAuth';

  useEffect(() => {
    // Prevent double processing in strict mode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    async function handleCallback() {
      log.debug(`Processing OAuth callback from ${provider}`);

      try {
        // Fetch user info - cookies are sent automatically
        const user = await getSession();

        if (user) {
          log.info(`OAuth login successful: ${user.display_name} via ${provider}`);
          login(user);
          router.push(ROUTES.SESSIONS);
        } else {
          log.error('OAuth callback: No user returned from session check');
          setError('Authentication failed. Please try again.');
          router.push(ROUTES.HOME);
        }
      } catch (error) {
        log.error('OAuth callback error:', error);
        setError('Authentication failed. Please try again.');
        router.push(ROUTES.HOME);
      }
    }

    handleCallback();
  }, [provider, login, setError, router]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-gradient-to-br from-coup-dark via-coup-darker to-black">
      <div className="text-center">
        {/* Loading spinner */}
        <div className="mb-6">
          <div className="w-16 h-16 border-4 border-coup-gold border-t-transparent rounded-full animate-spin mx-auto" />
        </div>
        
        {/* Status text */}
        <h1 className="text-2xl font-semibold text-white mb-2">
          Completing {provider} Login
        </h1>
        <p className="text-gray-400">
          Please wait while we set up your session...
        </p>
      </div>
    </main>
  );
}
