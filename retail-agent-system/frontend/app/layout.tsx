import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider, themeInitScript } from '@/components/ThemeProvider';
import RetailCanvas from '@/components/RetailCanvas';

export const metadata: Metadata = {
  title: 'Retail Agent System',
  description: 'Intelligent Retail Store Automation powered by AI',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Applies the saved theme before first paint (no light/dark flash). */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body suppressHydrationWarning>
        <ThemeProvider>
          {/* Interactive retail-items background, shared by every page. */}
          <RetailCanvas />
          <div className="relative z-10">
            <AuthProvider>{children}</AuthProvider>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
