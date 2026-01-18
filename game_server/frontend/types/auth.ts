import { z } from 'zod';

// Login request schema
export const LoginRequestSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
});

export type LoginRequest = z.infer<typeof LoginRequestSchema>;

// Register request schema
export const RegisterRequestSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  display_name: z.string().min(1, 'Display name is required'),
});

export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;

// Auth response schema (from backend)
export const AuthResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string().default('bearer'),
  expires_in: z.number().optional(),
});

export type AuthResponse = z.infer<typeof AuthResponseSchema>;

// Token refresh request
export const RefreshRequestSchema = z.object({
  refresh_token: z.string(),
});

export type RefreshRequest = z.infer<typeof RefreshRequestSchema>;

// OAuth provider types
export const OAuthProviderSchema = z.enum(['discord', 'slack', 'google']);
export type OAuthProvider = z.infer<typeof OAuthProviderSchema>;
