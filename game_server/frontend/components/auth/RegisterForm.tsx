'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/stores/authStore';
import { registerUser } from '@/lib/api/auth';
import { RegisterRequestSchema } from '@/types';
import { ROUTES } from '@/lib/constants';
import log from '@/lib/logger';

export function RegisterForm() {
  const router = useRouter();
  const { login, setLoading, setError, isLoading, error } = useAuthStore();
  
  const [userName, setUserName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [validationErrors, setValidationErrors] = useState<{
    user_name?: string;
    display_name?: string;
    password?: string;
  }>({});

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setValidationErrors({});

    // Validate with Zod
    const result = RegisterRequestSchema.safeParse({ 
      user_name: userName, 
      display_name: displayName,
      password 
    });
    
    if (!result.success) {
      const errors: typeof validationErrors = {};
      result.error.errors.forEach((err) => {
        const field = err.path[0] as keyof typeof validationErrors;
        errors[field] = err.message;
      });
      setValidationErrors(errors);
      return;
    }

    try {
      setLoading(true);
      log.debug('Attempting registration for:', userName);
      
      const response = await registerUser(result.data);
      login(response);
      
      log.info('Registration successful, redirecting to sessions');
      router.push(ROUTES.SESSIONS);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setError(message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Username"
        type="text"
        value={userName}
        onChange={(e) => setUserName(e.target.value)}
        placeholder="Choose a username"
        error={validationErrors.user_name}
        disabled={isLoading}
        autoComplete="username"
      />

      <Input
        label="Display Name"
        type="text"
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
        placeholder="How should we call you?"
        error={validationErrors.display_name}
        disabled={isLoading}
        autoComplete="name"
      />

      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Create a password"
        error={validationErrors.password}
        disabled={isLoading}
        autoComplete="new-password"
      />

      {error && (
        <div className="p-3 bg-coup-red/20 border border-coup-red rounded-lg text-coup-red text-sm">
          {error}
        </div>
      )}

      <Button
        type="submit"
        className="w-full"
        isLoading={isLoading}
      >
        Create Account
      </Button>
    </form>
  );
}
