'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  LayoutDashboard, Package, Receipt, Bot, LogOut, Store,
  Users, MessageCircleWarning, ClipboardList, Truck,
} from 'lucide-react';

const nav = [
  { href: '/dashboard',       label: 'Dashboard',       icon: LayoutDashboard },
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

  const linkClass = (href: string) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      pathname === href
        ? 'bg-blue-700 text-white'
        : 'text-blue-200 hover:bg-blue-800 hover:text-white'
    }`;

  return (
    <nav className="bg-blue-900 text-white w-64 min-h-screen flex flex-col px-4 py-6">
      <div className="flex items-center gap-2 mb-8">
        <Store className="w-7 h-7 text-blue-300" />
        <span className="text-lg font-bold leading-tight">
          Retail Agent<br />
          <span className="text-xs font-normal text-blue-300">Powered by AI</span>
        </span>
      </div>

      <ul className="space-y-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <li key={href}>
            <Link href={href} className={linkClass(href)}>
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          </li>
        ))}
      </ul>

      <div className="my-4 border-t border-blue-800" />
      <p className="text-xs text-blue-400 px-3 mb-2 uppercase tracking-wider">Operations</p>

      <ul className="flex-1 space-y-1">
        {navExtra.map(({ href, label, icon: Icon }) => (
          <li key={href}>
            <Link href={href} className={linkClass(href)}>
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          </li>
        ))}
      </ul>

      {user && (
        <div className="border-t border-blue-700 pt-4 mt-4">
          <div className="text-xs text-blue-300 mb-1">{user.role.toUpperCase()}</div>
          <div className="text-sm font-medium mb-3">{user.username}</div>
          <button
            onClick={logout}
            className="flex items-center gap-2 text-sm text-blue-300 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
