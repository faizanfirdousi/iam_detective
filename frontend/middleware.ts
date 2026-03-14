import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const COOKIE_NAME = 'iam_judge_auth';

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Always allow the login page and its API route
  if (
    pathname.startsWith('/login') ||
    pathname.startsWith('/api/auth') ||
    pathname.startsWith('/_next') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next();
  }

  // Check for auth cookie
  const authCookie = req.cookies.get(COOKIE_NAME);
  if (authCookie?.value === 'granted') {
    return NextResponse.next();
  }

  // Not authenticated — redirect to login
  const loginUrl = req.nextUrl.clone();
  loginUrl.pathname = '/login';
  loginUrl.search = '';
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
