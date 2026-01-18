import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const protectedRoutes = ['/sessions', '/profile', '/game'];

// Routes that are only accessible when NOT authenticated
const authRoutes = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Check for auth token in cookies
  // Note: In a real app, you'd validate the JWT here
  const token = request.cookies.get('access_token')?.value;
  
  // For client-side auth (localStorage), we check a flag cookie
  // This is set by the client after successful login
  const isAuthenticatedFlag = request.cookies.get('is_authenticated')?.value === 'true';
  
  const isAuthenticated = !!token || isAuthenticatedFlag;

  // Check if trying to access protected route without auth
  const isProtectedRoute = protectedRoutes.some(route => 
    pathname.startsWith(route)
  );

  if (isProtectedRoute && !isAuthenticated) {
    const url = request.nextUrl.clone();
    url.pathname = '/';
    url.searchParams.set('redirect', pathname);
    return NextResponse.redirect(url);
  }

  // Check if trying to access auth routes while authenticated
  const isAuthRoute = authRoutes.some(route => 
    pathname.startsWith(route)
  );

  if (isAuthRoute && isAuthenticated) {
    const url = request.nextUrl.clone();
    url.pathname = '/sessions';
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all routes except static files and API routes
    '/((?!api|_next/static|_next/image|favicon.ico|images|icons|audio|animations|fonts).*)',
  ],
};
