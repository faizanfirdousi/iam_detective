import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// NOTE: Edge Runtime can only inline process.env at build time for non-NEXT_PUBLIC vars.
// We use NEXT_PUBLIC_ prefix here so they are available in the Edge middleware.
// These are demo credentials — not sensitive.
const VALID_USER = process.env.NEXT_PUBLIC_JUDGE_USER ?? "judge";
const VALID_PASS = process.env.NEXT_PUBLIC_JUDGE_PASS ?? "iam-detective-2026";

export function middleware(req: NextRequest) {
  const basicAuth = req.headers.get('authorization');

  if (basicAuth && basicAuth.startsWith('Basic ')) {
    const authValue = basicAuth.slice(6); // strip 'Basic '
    try {
      const decoded = atob(authValue);
      const colonIndex = decoded.indexOf(':');
      if (colonIndex !== -1) {
        const user = decoded.slice(0, colonIndex);
        const pwd = decoded.slice(colonIndex + 1);
        if (user === VALID_USER && pwd === VALID_PASS) {
          return NextResponse.next();
        }
      }
    } catch {
      // Invalid base64 — fall through to 401
    }
  }

  return new NextResponse('Authentication required.', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="IAM Detective"',
    },
  });
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
