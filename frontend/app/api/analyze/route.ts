import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const maxDuration = 60;

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_URL || 'https://guitar-tone-finder-api.onrender.com';
  const formData = await request.formData();

  const response = await fetch(`${backendUrl}/analyze`, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(data, { status: response.status });
  }

  return NextResponse.json(data);
}
