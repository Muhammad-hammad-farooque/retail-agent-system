'use client';

import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

interface Props {
  /** `pill` shows a label next to the icon; `icon` is a compact round button. */
  variant?: 'pill' | 'icon';
  className?: string;
}

export default function ThemeToggle({ variant = 'pill', className = '' }: Props) {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';
  const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';

  if (variant === 'icon') {
    return (
      <button
        type="button"
        onClick={toggle}
        aria-label={label}
        title={label}
        className={`glass grid h-10 w-10 place-items-center rounded-full border border-ash-200 text-ash-700 shadow-glass transition hover:scale-105 hover:text-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${className}`}
      >
        {isDark ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      role="switch"
      aria-checked={isDark}
      className={`group flex w-full items-center justify-between gap-3 rounded-xl border border-ash-200 bg-ash-50/60 px-3 py-2 text-sm font-medium text-ash-700 transition hover:border-brand-300 hover:text-ash-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${className}`}
    >
      <span className="flex items-center gap-2">
        {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        {isDark ? 'Dark green' : 'Light green'}
      </span>
      <span
        className={`relative h-5 w-9 rounded-full transition-colors ${
          isDark ? 'bg-brand-600' : 'bg-ash-300'
        }`}
        aria-hidden="true"
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
            isDark ? 'left-[18px]' : 'left-0.5'
          }`}
        />
      </span>
    </button>
  );
}
