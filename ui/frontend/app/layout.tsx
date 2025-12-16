import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CI Failure Agent Dashboard',
  description: 'Real-time monitoring for AI agents',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
