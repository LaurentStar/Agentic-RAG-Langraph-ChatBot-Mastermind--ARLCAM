'use client';

import Link from 'next/link';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { ROUTES } from '@/lib/constants';

export default function RegisterPage() {
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

        {/* Register Card */}
        <div className="bg-coup-purple/50 border border-gray-700 rounded-xl p-6 space-y-6">
          <div>
            <h2 className="text-xl font-semibold text-white mb-1">
              Create Account
            </h2>
            <p className="text-sm text-gray-400">
              Join the game and begin your rise to power
            </p>
          </div>

          <RegisterForm />
        </div>

        {/* Login Link */}
        <p className="text-center text-gray-400">
          Already have an account?{' '}
          <Link 
            href={ROUTES.HOME} 
            className="text-coup-gold hover:underline font-medium"
          >
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
