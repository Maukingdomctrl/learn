import type {Metadata} from 'next';
import { Plus_Jakarta_Sans, Fraunces, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['400', '500', '600', '700'],
});

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['600', '700'],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500', '600'],
});

export const metadata: Metadata = {
  title: 'Learn — Key Facts Engine',
  description: 'Deterministic rule-based fact discovery and study card engine for ICSE study sheets (Classes 1–10).',
  openGraph: {
    title: 'Learn — Key Facts Engine',
    description: 'Deterministic rule-based fact discovery and study card engine for ICSE study sheets (Classes 1–10).',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Learn — Key Facts Engine',
    description: 'Deterministic rule-based fact discovery and study card engine for ICSE study sheets (Classes 1–10).',
  },
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en" className={`${jakarta.variable} ${fraunces.variable} ${jetbrainsMono.variable}`}>
      <body suppressHydrationWarning className="font-sans antialiased bg-[#F8FAFC] text-[#0F172A]">{children}</body>
    </html>
  );
}
