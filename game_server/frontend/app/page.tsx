'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import Image from 'next/image';
import { LoginForm } from '@/components/auth/LoginForm';
import { Skeleton } from '@/components/ui/Skeleton';
import { ROUTES } from '@/lib/constants';

// Lazy load OAuth buttons (they may need external SDKs)
const OAuthButtons = dynamic(
  () => import('@/components/auth/OAuthButtons').then((mod) => mod.OAuthButtons),
  {
    loading: () => (
      <div className="space-y-3">
        <div className="relative py-2">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-600" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-coup-dark text-gray-400">Or continue with</span>
          </div>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    ),
    ssr: false,
  }
);

export default function StartPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        {/* Logo and Title */}
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <div className="w-20 h-20 bg-coup-gold/20 rounded-full flex items-center justify-center">
              <span className="text-4xl">👑</span>
            </div>
          </div>
          <h1 className="text-4xl font-bold text-coup-gold tracking-wide">
            COUP
          </h1>
          <p className="mt-2 text-gray-400">
            The Game of Deception
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-coup-purple/50 border border-gray-700 rounded-xl p-6 space-y-6">
          <div>
            <h2 className="text-xl font-semibold text-white mb-1">
              Welcome Back
            </h2>
            <p className="text-sm text-gray-400">
              Sign in to continue your quest for power
            </p>
          </div>

          <LoginForm />
          
          <OAuthButtons />
        </div>

        {/* Register Link */}
        <p className="text-center text-gray-400">
          Don&apos;t have an account?{' '}
          <Link 
            href={ROUTES.REGISTER} 
            className="text-coup-gold hover:underline font-medium"
          >
            Create one
          </Link>
        </p>
      </div>
    </main>
  );
}
