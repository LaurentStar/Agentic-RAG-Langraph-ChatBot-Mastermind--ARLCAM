import { z } from 'zod';

// Login request schema
export const LoginRequestSchema = z.object({
  user_name: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
});

export type LoginRequest = z.infer<typeof LoginRequestSchema>;

// Register request schema
export const RegisterRequestSchema = z.object({
  user_name: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  display_name: z.string().min(1, 'Display name is required'),
});

export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;

// User info schema (returned from login/session - no tokens)
export const UserInfoSchema = z.object({
  user_id: z.string(),
  user_name: z.string(),
  display_name: z.string(),
  player_type: z.string(),
});

export type UserInfo = z.infer<typeof UserInfoSchema>;

// Auth response schema (legacy - for backward compatibility)
export const AuthResponseSchema = z.object({
  access_token: z.string().optional(),
  refresh_token: z.string().optional(),
  user_id: z.string(),
  user_name: z.string(),
  display_name: z.string(),
  player_type: z.string(),
  expires_in: z.number().optional(),
});

export type AuthResponse = z.infer<typeof AuthResponseSchema>;

// Token refresh request (for service clients)
export const RefreshRequestSchema = z.object({
  refresh_token: z.string(),
});

export type RefreshRequest = z.infer<typeof RefreshRequestSchema>;

// OAuth provider types
export const OAuthProviderSchema = z.enum(['discord', 'slack', 'google']);
export type OAuthProvider = z.infer<typeof OAuthProviderSchema>;
