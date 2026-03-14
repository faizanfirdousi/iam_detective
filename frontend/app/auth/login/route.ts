import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const COOKIE_NAME = 'iam_judge_auth';
const VALID_USER = process.env.NEXT_PUBLIC_JUDGE_USER ?? 'judge';
const VALID_PASS = process.env.NEXT_PUBLIC_JUDGE_PASS ?? 'iam-detective-2026';

export async function POST(req: NextRequest) {
  const body = await req.json() as { username?: string; password?: string };

  if (body.username === VALID_USER && body.password === VALID_PASS) {
    const cookieStore = await cookies();
    cookieStore.set(COOKIE_NAME, 'granted', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24, // 24 hours
    });
    return NextResponse.json({ ok: true });
  }

  return NextResponse.json({ ok: false, error: 'Invalid credentials' }, { status: 401 });
}
