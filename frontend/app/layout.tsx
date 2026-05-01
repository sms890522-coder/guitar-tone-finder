import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ToneScope AI',
  description: 'Upload guitar audio and get tone analysis with amp and effects recommendations.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
