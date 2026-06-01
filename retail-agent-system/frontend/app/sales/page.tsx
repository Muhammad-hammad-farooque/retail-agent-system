'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts';
import {
  getSalesToday, getDailyRevenue, getRecentTransactions,
  getCategoryRevenue, getKpis, getTopProducts, getProfitSummary,
} from '@/lib/api';
import {
  TrendingUp, DollarSign, ShoppingBag, RefreshCw,
  Receipt, TrendingDown, Package,
} from 'lucide-react';

interface SalesToday   { count: number; revenue: number }
interface DailyPoint   { date: string; label: string; revenue: number; count: number }
interface Transaction  { invoice_number: string; customer_id: number | null; net_amount: number; tax: number; payment_method: string; created_at: string }
interface CategoryRev  { category: string; revenue: number; profit: number }
interface Kpis         { monthly_revenue_pkr: number; weekly_revenue_pkr: number }
interface TopProduct   { name: string; category: string; units_sold: number; revenue: number }
interface ProfitSummary { today_profit: number; avg_order_value: number; payment_breakdown: { method: string; count: number; revenue: number }[] }

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#f97316','#84cc16'];
const PIE_COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6'];

const PAYMENT_METHODS = ['All', 'Cash', 'Card', 'Online'];
const DAY_OPTIONS = [
  { label: 'Last 7 days',  value: 7 },
  { label: 'Last 14 days', value: 14 },
  { label: 'Last 30 days', value: 30 },
];
const PERIOD_OPTIONS = [
  { label: 'Today', value: 'today' as const },
  { label: 'This Week', value: 'week' as const },
  { label: 'This Month', value: 'month' as const },
];

export default function SalesDashboardPage() {
  const [salesToday,    setSalesToday]    = useState<SalesToday | null>(null);
  const [daily,         setDaily]         = useState<DailyPoint[]>([]);
  const [transactions,  setTransactions]  = useState<Transaction[]>([]);
  const [categories,    setCategories]    = useState<CategoryRev[]>([]);
  const [kpis,          setKpis]          = useState<Kpis | null>(null);
  const [topProducts,   setTopProducts]   = useState<TopProduct[]>([]);
  const [profitSummary, setProfitSummary] = useState<ProfitSummary | null>(null);
  const [loading,       setLoading]       = useState(true);
  const [syncing,       setSyncing]       = useState(false);
  const [lastUpdated,   setLastUpdated]   = useState('');

  // Filter / period state
  const [dayRange,      setDayRange]      = useState(7);
  const [topPeriod,     setTopPeriod]     = useState<'today' | 'week' | 'month'>('week');
  const [payFilter,     setPayFilter]     = useState('All');

  const loadBase = useCallback(() =>
    Promise.all([
      getSalesToday(),
      getRecentTransactions(payFilter === 'All' ? undefined : payFilter),
      getCategoryRevenue(),
      getKpis(),
      getProfitSummary(),
    ]).then(([st, rt, cr, kp, ps]) => {
      setSalesToday(st.data);
      setTransactions(rt.data);
      setCategories(cr.data);
      setKpis(kp.data);
      setProfitSummary(ps.data);
    }),
  [payFilter]);

  const loadDaily = useCallback(() =>
    getDailyRevenue(dayRange).then(r => setDaily(r.data)),
  [dayRange]);

  const loadTopProducts = useCallback(() =>
    getTopProducts(topPeriod).then(r => setTopProducts(r.data)),
  [topPeriod]);

  const loadAll = useCallback((isInitial = false) => {
    if (isInitial) setLoading(true);
    else setSyncing(true);
    Promise.all([loadBase(), loadDaily(), loadTopProducts()])
      .catch(() => {})
      .finally(() => {
        setLoading(false);
        setSyncing(false);
        setLastUpdated(new Date().toLocaleTimeString());
      });
  }, [loadBase, loadDaily, loadTopProducts]);

  // Full reload on mount + silent background refresh every 30s
  useEffect(() => {
    loadAll(true);
    const interval = setInterval(() => loadAll(false), 30_000);
    return () => clearInterval(interval);
  }, [loadAll]);

  // Reload only transactions when payment filter changes
  useEffect(() => {
    getRecentTransactions(payFilter === 'All' ? undefined : payFilter)
      .then(r => setTransactions(r.data))
      .catch(() => {});
  }, [payFilter]);

  // Reload only daily chart when day range changes
  useEffect(() => {
    loadDaily().catch(() => {});
  }, [loadDaily]);

  // Reload only top products when period changes
  useEffect(() => {
    loadTopProducts().catch(() => {});
  }, [loadTopProducts]);

  const kpiCards = [
    {
      label: 'Sales Today',
      value: salesToday?.count ?? 0,
      sub: `Rs. ${(salesToday?.revenue ?? 0).toLocaleString()} revenue`,
      icon: ShoppingBag,
      bg: 'bg-blue-50 border-blue-100',
      text: 'text-blue-700',
      val: 'text-blue-800',
    },
    {
      label: 'Today Revenue',
      value: `Rs. ${(salesToday?.revenue ?? 0).toLocaleString()}`,
      sub: 'Paid invoices only',
      icon: DollarSign,
      bg: 'bg-green-50 border-green-100',
      text: 'text-green-700',
      val: 'text-green-800',
    },
    {
      label: 'Today Profit',
      value: `Rs. ${(profitSummary?.today_profit ?? 0).toLocaleString()}`,
      sub: 'After cost deduction',
      icon: TrendingDown,
      bg: 'bg-emerald-50 border-emerald-100',
      text: 'text-emerald-700',
      val: 'text-emerald-800',
    },
    {
      label: 'Avg Order Value',
      value: `Rs. ${(profitSummary?.avg_order_value ?? 0).toLocaleString()}`,
      sub: 'Today\'s invoices',
      icon: Receipt,
      bg: 'bg-indigo-50 border-indigo-100',
      text: 'text-indigo-700',
      val: 'text-indigo-800',
    },
    {
      label: 'Weekly Revenue',
      value: `Rs. ${(kpis?.weekly_revenue_pkr ?? 0).toLocaleString()}`,
      sub: 'Last 7 days',
      icon: TrendingUp,
      bg: 'bg-purple-50 border-purple-100',
      text: 'text-purple-700',
      val: 'text-purple-800',
    },
    {
      label: 'Monthly Revenue',
      value: `Rs. ${(kpis?.monthly_revenue_pkr ?? 0).toLocaleString()}`,
      sub: 'This month',
      icon: Receipt,
      bg: 'bg-orange-50 border-orange-100',
      text: 'text-orange-700',
      val: 'text-orange-800',
    },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sales Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Live sales overview</p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                  syncing ? 'bg-blue-400 animate-pulse' : 'bg-green-400'
                }`}
              />
              <span className="text-xs text-gray-400">
                {syncing ? 'Syncing…' : `Updated ${lastUpdated}`}
              </span>
            </div>
          )}
          <button
            onClick={() => loadAll(false)}
            disabled={syncing}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors disabled:opacity-40"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="bg-gray-100 rounded-xl h-28 animate-pulse" />)}
        </div>
      ) : (
        <>
          {/* KPI Cards — 6 cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
            {kpiCards.map(({ label, value, sub, icon: Icon, bg, text, val }) => (
              <div key={label} className={`${bg} border rounded-xl p-5`}>
                <div className="flex items-center gap-2 mb-3">
                  <Icon className={`w-5 h-5 ${text}`} />
                  <span className={`text-sm font-medium ${text}`}>{label}</span>
                </div>
                <div className={`text-xl font-bold ${val}`}>{value}</div>
                <div className={`text-xs ${text} mt-1 opacity-80`}>{sub}</div>
              </div>
            ))}
          </div>

          {/* Row 2: Daily Revenue + Payment Method Pie */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Daily Revenue with day-range dropdown */}
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-gray-800">Daily Revenue</h2>
                <select
                  value={dayRange}
                  onChange={e => setDayRange(Number(e.target.value))}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-300"
                >
                  {DAY_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              {daily.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={daily} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v) => [`Rs. ${(v as number ?? 0).toLocaleString()}`, 'Revenue']} />
                    <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Payment Method Pie */}
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Payment Methods</h2>
              {!profitSummary?.payment_breakdown?.length ? (
                <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={profitSummary.payment_breakdown}
                      dataKey="revenue"
                      nameKey="method"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ method, percent }) => `${method} ${((percent ?? 0) * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {profitSummary.payment_breakdown.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => `Rs. ${(v as number ?? 0).toLocaleString()}`} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Row 3: Category Revenue + Top Products */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Category Revenue horizontal bar */}
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Revenue by Category</h2>
              {categories.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={categories} layout="vertical" margin={{ top: 4, right: 8, left: 60, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                    <YAxis dataKey="category" type="category" tick={{ fontSize: 10 }} width={55} />
                    <Tooltip formatter={(v) => [`Rs. ${(v as number ?? 0).toLocaleString()}`, 'Revenue']} />
                    <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                      {categories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Top Selling Products */}
            <div className="bg-white rounded-xl border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-gray-500" />
                  <h2 className="text-base font-semibold text-gray-800">Top Selling Products</h2>
                </div>
                <select
                  value={topPeriod}
                  onChange={e => setTopPeriod(e.target.value as 'today' | 'week' | 'month')}
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-300"
                >
                  {PERIOD_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              {topProducts.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No sales in this period</div>
              ) : (
                <div className="space-y-3 overflow-y-auto max-h-[220px]">
                  {topProducts.map((p, i) => {
                    const maxRevenue = topProducts[0]?.revenue || 1;
                    const pct = (p.revenue / maxRevenue) * 100;
                    return (
                      <div key={i}>
                        <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
                          <span className="font-medium text-gray-800 truncate max-w-[55%]">{p.name}</span>
                          <span className="text-gray-500">{p.units_sold} units · Rs. {p.revenue.toLocaleString()}</span>
                        </div>
                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Recent Transactions with payment method filter */}
          <div className="bg-white rounded-xl border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-gray-800">Recent Transactions</h2>
              <div className="flex gap-1">
                {PAYMENT_METHODS.map(m => (
                  <button
                    key={m}
                    onClick={() => setPayFilter(m)}
                    className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                      payFilter === m
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'text-gray-500 border-gray-200 hover:border-blue-300 hover:text-blue-600'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
            {transactions.length === 0 ? (
              <div className="flex items-center justify-center h-24 text-gray-400 text-sm">No transactions found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500 font-semibold">
                      <th className="pb-3 pr-4">Invoice #</th>
                      <th className="pb-3 pr-4">Customer</th>
                      <th className="pb-3 pr-4 text-right">Amount (Rs.)</th>
                      <th className="pb-3 pr-4 text-right">Tax (Rs.)</th>
                      <th className="pb-3 pr-4">Payment</th>
                      <th className="pb-3">Date & Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {transactions.map((t, i) => (
                      <tr key={i} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3 pr-4 font-mono text-xs text-gray-600">{t.invoice_number}</td>
                        <td className="py-3 pr-4 text-gray-500">
                          {t.customer_id ? `#${t.customer_id}` : 'Walk-in'}
                        </td>
                        <td className="py-3 pr-4 text-right font-semibold text-gray-900">
                          {(t.net_amount || 0).toLocaleString()}
                        </td>
                        <td className="py-3 pr-4 text-right text-gray-500">
                          {(t.tax || 0).toLocaleString()}
                        </td>
                        <td className="py-3 pr-4">
                          <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs">
                            {t.payment_method || 'Cash'}
                          </span>
                        </td>
                        <td className="py-3 text-xs text-gray-400">
                          {t.created_at ? new Date(t.created_at).toLocaleDateString('en-GB') + ' ' + new Date(t.created_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
