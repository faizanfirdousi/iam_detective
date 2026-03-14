import { NextRequest, NextResponse } from 'next/server';

const COOKIE_NAME = 'iam_judge_auth';
const VALID_USER = process.env.JUDGE_USER ?? 'judge';
const VALID_PASS = process.env.JUDGE_PASS ?? 'iam-detective-2026';

export async function POST(req: NextRequest) {
  const body = await req.json() as { username?: string; password?: string };

  if (body.username === VALID_USER && body.password === VALID_PASS) {
    const res = NextResponse.json({ ok: true });
    res.cookies.set(COOKIE_NAME, 'granted', {
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24, // 24 hours
    });
    return res;
  }

  return NextResponse.json({ ok: false, error: 'Invalid credentials' }, { status: 401 });
}
