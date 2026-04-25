'use client';

import { useEffect, useState } from 'react';
import { getInvoices, getAccountingSummary } from '@/lib/api';
import { DollarSign, Receipt, TrendingUp, RefreshCw, CheckCircle, Clock, XCircle } from 'lucide-react';

interface Invoice {
  id: number;
  invoice_number: string;
  customer_id: number;
  total_amount: number;
  tax: number;
  status: string;
  created_at: string;
}

interface Summary {
  total_invoices: number;
  total_revenue: number;
  total_tax: number;
  paid_count: number;
  pending_count: number;
  cancelled_count: number;
}

const statusIcon: Record<string, React.ReactNode> = {
  paid: <CheckCircle className="w-3.5 h-3.5 text-green-500" />,
  pending: <Clock className="w-3.5 h-3.5 text-yellow-500" />,
  cancelled: <XCircle className="w-3.5 h-3.5 text-red-500" />,
  refunded: <XCircle className="w-3.5 h-3.5 text-gray-400" />,
};

const statusColor: Record<string, string> = {
  paid: 'bg-green-50 text-green-700',
  pending: 'bg-yellow-50 text-yellow-700',
  cancelled: 'bg-red-50 text-red-700',
  refunded: 'bg-gray-50 text-gray-600',
};

export default function AccountingPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    Promise.all([
      getInvoices(statusFilter ? { status: statusFilter } : {}),
      getAccountingSummary(),
    ])
      .then(([iRes, sRes]) => {
        setInvoices(iRes.data);
        setSummary(sRes.data);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Accounting</h1>
          <p className="text-sm text-gray-500 mt-1">Invoices and financial summary</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-green-50 border border-green-100 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <DollarSign className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium text-green-700">Total Revenue</span>
            </div>
            <div className="text-2xl font-bold text-green-800">
              Rs. {(summary.total_revenue || 0).toLocaleString()}
            </div>
            <div className="text-xs text-green-600 mt-1">
              Tax collected: Rs. {(summary.total_tax || 0).toLocaleString()}
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Receipt className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-medium text-blue-700">Total Invoices</span>
            </div>
            <div className="text-2xl font-bold text-blue-800">{summary.total_invoices}</div>
            <div className="text-xs text-blue-600 mt-1">
              {summary.paid_count} paid · {summary.pending_count} pending
            </div>
          </div>

          <div className="bg-purple-50 border border-purple-100 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-purple-600" />
              <span className="text-sm font-medium text-purple-700">Paid Invoices</span>
            </div>
            <div className="text-2xl font-bold text-purple-800">{summary.paid_count}</div>
            <div className="text-xs text-purple-600 mt-1">
              {summary.cancelled_count} cancelled
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 mb-5">
        {['', 'paid', 'pending', 'cancelled', 'refunded'].map((s) => (
          <button
            key={s || 'all'}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize transition-colors ${
              statusFilter === s
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-blue-300'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {/* Invoices table */}
      <div className="bg-white rounded-xl border border-gray-100 p-6">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
            Loading invoices...
          </div>
        ) : invoices.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
            No invoices found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500 font-semibold">
                  <th className="pb-3 pr-4">Invoice #</th>
                  <th className="pb-3 pr-4">Customer ID</th>
                  <th className="pb-3 pr-4 text-right">Amount (Rs.)</th>
                  <th className="pb-3 pr-4 text-right">Tax (Rs.)</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 pr-4 font-mono text-xs text-gray-600">
                      {inv.invoice_number}
                    </td>
                    <td className="py-3 pr-4 text-gray-500">#{inv.customer_id}</td>
                    <td className="py-3 pr-4 text-right font-medium text-gray-900">
                      {(inv.total_amount || 0).toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 text-right text-gray-500">
                      {(inv.tax || 0).toLocaleString()}
                    </td>
                    <td className="py-3 pr-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                          statusColor[inv.status] || 'bg-gray-50 text-gray-600'
                        }`}
                      >
                        {statusIcon[inv.status]}
                        {inv.status}
                      </span>
                    </td>
                    <td className="py-3 text-gray-500 text-xs">
                      {new Date(inv.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
