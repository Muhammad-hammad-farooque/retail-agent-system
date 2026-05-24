'use client';

import { useEffect, useState } from 'react';
import { getInvoices, getAccountingSummary, getPurchaseOrders, getPurchaseSummary } from '@/lib/api';
import {
  DollarSign, Receipt, TrendingUp, RefreshCw,
  ShoppingCart, PackageCheck, Banknote,
} from 'lucide-react';

interface Invoice {
  id: number;
  invoice_number: string;
  customer_id: number;
  total_amount: number;
  tax: number;
  status: string;
  created_at: string;
}

interface SalesSummary {
  total_invoices: number;
  total_revenue: number;
  total_tax: number;
  paid_count: number;
  pending_count: number;
  cancelled_count: number;
}

interface PurchaseOrder {
  id: number;
  order_number: string;
  product_id: number;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  supplier: string;
  status: string;
  created_at: string;
}

interface PurchaseSummary {
  total_purchases: number;
  total_spent: number;
  this_month_purchases: number;
  this_month_spent: number;
}


type Tab = 'sales' | 'purchases';

export default function AccountingPage() {
  const [tab, setTab] = useState<Tab>('sales');

  // Sales state
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [salesSummary, setSalesSummary] = useState<SalesSummary | null>(null);
  const [salesLoading, setSalesLoading] = useState(true);

  // Purchases state
  const [purchases, setPurchases] = useState<PurchaseOrder[]>([]);
  const [purchaseSummary, setPurchaseSummary] = useState<PurchaseSummary | null>(null);
  const [purchasesLoading, setPurchasesLoading] = useState(true);

  const loadSales = () => {
    setSalesLoading(true);
    Promise.all([
      getInvoices({}),
      getAccountingSummary(),
    ])
      .then(([iRes, sRes]) => {
        setInvoices(iRes.data);
        setSalesSummary(sRes.data);
      })
      .catch(() => {
        setInvoices([]);
        setSalesSummary(null);
      })
      .finally(() => setSalesLoading(false));
  };

  const loadPurchases = () => {
    setPurchasesLoading(true);
    Promise.all([
      getPurchaseOrders({ status: 'received', limit: 100 }),
      getPurchaseSummary(),
    ])
      .then(([poRes, sumRes]) => {
        setPurchases(poRes.data);
        setPurchaseSummary(sumRes.data);
      })
      .catch(() => {
        setPurchases([]);
        setPurchaseSummary(null);
      })
      .finally(() => setPurchasesLoading(false));
  };

  useEffect(() => { loadSales(); }, []);
  useEffect(() => { if (tab === 'purchases') loadPurchases(); }, [tab]);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Accounting</h1>
          <p className="text-sm text-gray-500 mt-1">Sales invoices and vendor purchases</p>
        </div>
        <button
          onClick={() => tab === 'sales' ? loadSales() : loadPurchases()}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab('sales')}
          className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'sales'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Sales / Invoices
        </button>
        <button
          onClick={() => setTab('purchases')}
          className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
            tab === 'purchases'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Purchases
        </button>
      </div>

      {/* ── SALES TAB ── */}
      {tab === 'sales' && (
        <>
          {salesSummary && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <div className="bg-green-50 border border-green-100 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <DollarSign className="w-5 h-5 text-green-600" />
                  <span className="text-sm font-medium text-green-700">Total Revenue</span>
                </div>
                <div className="text-2xl font-bold text-green-800">
                  Rs. {(salesSummary.total_revenue || 0).toLocaleString()}
                </div>
                <div className="text-xs text-green-600 mt-1">
                  Tax collected: Rs. {(salesSummary.total_tax || 0).toLocaleString()}
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Receipt className="w-5 h-5 text-blue-600" />
                  <span className="text-sm font-medium text-blue-700">Total Invoices</span>
                </div>
                <div className="text-2xl font-bold text-blue-800">{salesSummary.total_invoices}</div>
                <div className="text-xs text-blue-600 mt-1">
                  {salesSummary.paid_count} paid · {salesSummary.pending_count} pending
                </div>
              </div>

              <div className="bg-purple-50 border border-purple-100 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-5 h-5 text-purple-600" />
                  <span className="text-sm font-medium text-purple-700">Paid Invoices</span>
                </div>
                <div className="text-2xl font-bold text-purple-800">{salesSummary.paid_count}</div>
                <div className="text-xs text-purple-600 mt-1">
                  {salesSummary.cancelled_count} cancelled
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            {salesLoading ? (
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
                      <th className="pb-3">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {invoices.map((inv) => (
                      <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3 pr-4 font-mono text-xs text-gray-600">{inv.invoice_number}</td>
                        <td className="py-3 pr-4 text-gray-500">#{inv.customer_id}</td>
                        <td className="py-3 pr-4 text-right font-medium text-gray-900">
                          {(inv.total_amount || 0).toLocaleString()}
                        </td>
                        <td className="py-3 pr-4 text-right text-gray-500">
                          {(inv.tax || 0).toLocaleString()}
                        </td>
                        <td className="py-3 text-gray-500 text-xs">
                          {new Date(inv.created_at).toLocaleDateString('en-GB')}
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

      {/* ── PURCHASES TAB ── */}
      {tab === 'purchases' && (
        <>
          {purchaseSummary && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <div className="bg-orange-50 border border-orange-100 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Banknote className="w-5 h-5 text-orange-600" />
                  <span className="text-sm font-medium text-orange-700">Total Spent</span>
                </div>
                <div className="text-2xl font-bold text-orange-800">
                  Rs. {(purchaseSummary.total_spent || 0).toLocaleString()}
                </div>
                <div className="text-xs text-orange-600 mt-1">
                  All time vendor purchases
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <ShoppingCart className="w-5 h-5 text-blue-600" />
                  <span className="text-sm font-medium text-blue-700">Total Orders Received</span>
                </div>
                <div className="text-2xl font-bold text-blue-800">
                  {purchaseSummary.total_purchases}
                </div>
                <div className="text-xs text-blue-600 mt-1">
                  Completed purchase orders
                </div>
              </div>

              <div className="bg-teal-50 border border-teal-100 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <PackageCheck className="w-5 h-5 text-teal-600" />
                  <span className="text-sm font-medium text-teal-700">This Month</span>
                </div>
                <div className="text-2xl font-bold text-teal-800">
                  Rs. {(purchaseSummary.this_month_spent || 0).toLocaleString()}
                </div>
                <div className="text-xs text-teal-600 mt-1">
                  {purchaseSummary.this_month_purchases} orders this month
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-100 p-6">
            {purchasesLoading ? (
              <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
                Loading purchases...
              </div>
            ) : purchases.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 text-gray-400">
                <ShoppingCart className="w-8 h-8 mb-2 opacity-40" />
                <span className="text-sm">No received purchases yet.</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500 font-semibold">
                      <th className="pb-3 pr-4">Order #</th>
                      <th className="pb-3 pr-4">Product ID</th>
                      <th className="pb-3 pr-4">Supplier</th>
                      <th className="pb-3 pr-4 text-right">Qty</th>
                      <th className="pb-3 pr-4 text-right">Unit Cost (Rs.)</th>
                      <th className="pb-3 pr-4 text-right">Total (Rs.)</th>
                      <th className="pb-3">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {purchases.map((po) => (
                      <tr key={po.id} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3 pr-4 font-mono text-xs text-gray-600">{po.order_number}</td>
                        <td className="py-3 pr-4 text-gray-500">#{po.product_id}</td>
                        <td className="py-3 pr-4 text-gray-500 max-w-[140px] truncate">
                          {po.supplier || '—'}
                        </td>
                        <td className="py-3 pr-4 text-right font-medium text-gray-800">{po.quantity}</td>
                        <td className="py-3 pr-4 text-right text-gray-600">
                          {(po.unit_cost || 0).toLocaleString()}
                        </td>
                        <td className="py-3 pr-4 text-right font-semibold text-gray-900">
                          {(po.total_cost || 0).toLocaleString()}
                        </td>
                        <td className="py-3 text-xs text-gray-400">
                          {new Date(po.created_at).toLocaleDateString('en-GB')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-gray-200">
                      <td colSpan={5} className="pt-3 pr-4 text-xs font-semibold text-gray-500 uppercase">
                        Total Spent
                      </td>
                      <td className="pt-3 pr-4 text-right font-bold text-gray-900">
                        {purchases.reduce((s, p) => s + (p.total_cost || 0), 0).toLocaleString()}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
