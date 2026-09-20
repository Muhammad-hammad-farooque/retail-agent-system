'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LayoutDashboard, Package, Receipt, Bot, LogOut, Store,
  Users, MessageCircleWarning, ClipboardList, Truck, TrendingUp,
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

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Chrome recedes: neutral by default, colour only on the one active item.
  const linkClass = (href: string) =>
    `relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
      pathname === href
        ? 'bg-brand-50 text-brand-800 font-semibold'
        : 'text-ash-600 font-medium hover:bg-ash-100 hover:text-ash-900'
    }`;

  const renderLink = ({ href, label, icon: Icon }: typeof nav[number]) => (
    <li key={href}>
      <Link href={href} className={linkClass(href)}>
        {pathname === href && (
          <span
            className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-full bg-brand-600"
            aria-hidden="true"
          />
        )}
        <Icon className="w-4 h-4" />
        {label}
      </Link>
    </li>
  );

  return (
    // h-screen + own scroll: with min-h-screen the nav's content could grow
    // taller than the viewport, stretching the flex row and forcing the whole
    // document to scroll on short windows.
    <nav className="bg-white border-r border-ash-200 w-64 shrink-0 h-screen sticky top-0 overflow-y-auto flex flex-col px-4 py-6">
      <div className="flex items-center gap-2.5 mb-8 px-1">
        <Store className="w-7 h-7 text-brand-600 shrink-0" />
        <span className="text-lg font-bold leading-tight text-ash-800">
          Retail Agent<br />
          <span className="text-xs font-normal text-ash-600">Powered by AI</span>
        </span>
      </div>

      <ul className="space-y-1">{nav.map(renderLink)}</ul>

      <div className="my-4 border-t border-ash-200" />
      <p className="text-xs text-ash-600 px-3 mb-2 uppercase tracking-wider">Operations</p>

      <ul className="flex-1 space-y-1">{navExtra.map(renderLink)}</ul>

      {user && (
        <div className="border-t border-ash-200 pt-4 mt-4 px-1">
          <div className="text-xs text-ash-600 mb-1 uppercase tracking-wide">{user.role}</div>
          <div className="text-sm font-medium text-ash-800 mb-3">{user.username}</div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-sm text-ash-600 hover:text-brand-700 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
