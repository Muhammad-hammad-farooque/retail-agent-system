'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import ThemeToggle from '@/components/ThemeToggle';
import UserMenu from '@/components/UserMenu';
import { CalendarDays, ChevronRight, Clock } from 'lucide-react';

const TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/sales': 'Sales',
  '/inventory': 'Inventory',
  '/accounting': 'Accounting',
  '/agent': 'AI Agent',
  '/customers': 'Customers',
  '/complaints': 'Complaints',
  '/purchase-orders': 'Purchase Orders',
  '/suppliers': 'Suppliers',
};

export default function Topbar() {
  const pathname = usePathname();
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  const title = TITLES[pathname] ?? 'Retail Agent';

  return (
    <header className="glass sticky top-0 z-30 hidden h-14 shrink-0 items-center justify-between border-b border-ash-200/70 px-6 md:flex">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm">
        <span className="text-ash-500">Store</span>
        <ChevronRight className="h-3.5 w-3.5 text-ash-400" />
        <span className="font-semibold text-ash-900">{title}</span>
      </nav>

      <div className="flex items-center gap-4">
        {now && (
          <div className="hidden items-center gap-4 text-xs font-medium text-ash-600 lg:flex">
            <span className="flex items-center gap-1.5">
              <CalendarDays className="h-3.5 w-3.5 text-brand-600" />
              {now.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-brand-600" />
              {now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
            </span>
          </div>
        )}
        <ThemeToggle variant="icon" className="!h-9 !w-9" />
        <div className="border-l border-ash-200 pl-3">
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
