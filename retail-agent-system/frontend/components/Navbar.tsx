'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import ThemeToggle from '@/components/ThemeToggle';
import {
  LayoutDashboard, Package, Receipt, Bot, LogOut, Store,
  Users, MessageCircleWarning, ClipboardList, Truck, TrendingUp, Menu, X,
} from 'lucide-react';

const nav = [
  { href: '/dashboard',       label: 'Dashboard',       icon: LayoutDashboard },
  { href: '/sales',           label: 'Sales',            icon: TrendingUp },
  { href: '/inventory',       label: 'Inventory',        icon: Package },
  { href: '/accounting',      label: 'Accounting',       icon: Receipt },
  { href: '/agent',           label: 'AI Agent',         icon: Bot },
];

const navExtra = [
  { href: '/customers',       label: 'Customers',        icon: Users },
  { href: '/complaints',      label: 'Complaints',       icon: MessageCircleWarning },
  { href: '/purchase-orders', label: 'Purchase Orders',  icon: ClipboardList },
  { href: '/suppliers',       label: 'Suppliers',        icon: Truck },
];

function BrandMark() {
  return (
    <div className="flex items-center gap-3 px-1">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 text-white shadow-glow">
        <Store className="h-5 w-5" />
      </div>
      <span className="text-[17px] font-bold leading-tight tracking-tight text-ash-900">
        Retail Agent
        <span className="block text-[11px] font-medium uppercase tracking-[0.14em] text-brand-700">
          Powered by AI
        </span>
      </span>
    </div>
  );
}

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => setOpen(false), [pathname]);

  const linkClass = (href: string) =>
    `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200 ${
      pathname === href
        ? 'bg-gradient-to-r from-brand-600 to-brand-500 font-semibold text-white shadow-glow'
        : 'font-medium text-ash-600 hover:translate-x-0.5 hover:bg-brand-50 hover:text-ash-900'
    }`;

  const renderLink = ({ href, label, icon: Icon }: typeof nav[number]) => (
    <li key={href}>
      <Link href={href} className={linkClass(href)}>
        <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-110" />
        {label}
      </Link>
    </li>
  );

  return (
    <>
      {/* Mobile top bar */}
      <div className="glass fixed inset-x-0 top-0 z-40 flex h-14 items-center justify-between border-b border-ash-200 px-4 md:hidden">
        <BrandMark />
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          className="grid h-9 w-9 place-items-center rounded-lg text-ash-700 hover:bg-brand-50"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <button
          type="button"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 bg-ash-950/40 backdrop-blur-[2px] md:hidden"
        />
      )}

      {/* h-screen + own scroll: keeps the sidebar from stretching the page. */}
      <nav
        className={`glass fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col overflow-y-auto border-r border-ash-200 px-4 py-6 transition-transform duration-300 md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="mb-8 hidden md:block">
          <BrandMark />
        </div>
        <div className="h-10 md:hidden" aria-hidden="true" />

        <ul className="space-y-1">{nav.map(renderLink)}</ul>

        <div className="my-4 border-t border-ash-200" />
        <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-ash-500">
          Operations
        </p>

        <ul className="flex-1 space-y-1">{navExtra.map(renderLink)}</ul>

        <div className="mt-4 space-y-3 border-t border-ash-200 pt-4">
          <ThemeToggle />
          {user && (
            <div className="flex items-center justify-between gap-2 px-1">
              <div className="flex min-w-0 items-center gap-2.5">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-100 text-sm font-bold uppercase text-brand-800">
                  {user.username?.[0] ?? '?'}
                </span>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-ash-900">{user.username}</div>
                  <div className="text-[11px] uppercase tracking-wide text-ash-500">{user.role}</div>
                </div>
              </div>
              <button
                onClick={logout}
                aria-label="Logout"
                title="Logout"
                className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-ash-600 transition-colors hover:bg-red-50 hover:text-red-700"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </nav>
    </>
  );
}
