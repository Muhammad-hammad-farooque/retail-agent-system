'use client';

import { useEffect, useState } from 'react';
import { getPurchaseOrders, updatePOStatus } from '@/lib/api';
import { ClipboardList, RefreshCw, CheckCircle, XCircle, Clock, Send, PackageCheck } from 'lucide-react';

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

const STATUS_FILTERS = ['', 'pending', 'approved', 'rejected', 'sent_to_vendor', 'received'];

const statusStyle: Record<string, string> = {
  pending:        'bg-yellow-50 text-yellow-700',
  approved:       'bg-blue-50 text-blue-700',
  rejected:       'bg-red-50 text-red-700',
  sent_to_vendor: 'bg-purple-50 text-purple-700',
  received:       'bg-green-50 text-green-700',
};

const statusIcon: Record<string, React.ReactNode> = {
  pending:        <Clock className="w-3.5 h-3.5 text-yellow-500" />,
  approved:       <CheckCircle className="w-3.5 h-3.5 text-blue-500" />,
  rejected:       <XCircle className="w-3.5 h-3.5 text-red-500" />,
  sent_to_vendor: <Send className="w-3.5 h-3.5 text-purple-500" />,
  received:       <PackageCheck className="w-3.5 h-3.5 text-green-500" />,
};

export default function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [updating, setUpdating] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    getPurchaseOrders(statusFilter ? { status: statusFilter } : {})
      .then((res) => setOrders(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleAction = async (id: number, action: 'approved' | 'rejected' | 'received') => {
    if (action === 'rejected') {
      const reason = window.prompt('Enter rejection reason:');
      if (!reason) return;
    }
    setUpdating(id);
    try {
      const res = await updatePOStatus(id, action);
      const { status, email_sent } = res.data;
      setOrders((prev) => prev.map((o) => (o.id === id ? { ...o, status } : o)));
      if (email_sent) alert(`PO approved and vendor email sent successfully.`);
    } catch {
      alert('Failed to update purchase order.');
    } finally {
      setUpdating(null);
    }
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Purchase Orders</h1>
          <p className="text-sm text-gray-500 mt-1">Approve orders to automatically email the vendor</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap mb-5">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s || 'all'}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium capitalize transition-colors ${
              statusFilter === s
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:border-blue-300'
            }`}
          >
            {s ? s.replace('_', ' ') : 'All'}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-400 text-sm">Loading orders...</div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-400">
            <ClipboardList className="w-8 h-8 mb-2 opacity-40" />
            <span className="text-sm">No purchase orders found.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500 font-semibold">
                  <th className="pb-3 pr-4">Order #</th>
                  <th className="pb-3 pr-4">Product ID</th>
                  <th className="pb-3 pr-4 text-right">Qty</th>
                  <th className="pb-3 pr-4 text-right">Total (Rs.)</th>
                  <th className="pb-3 pr-4">Supplier</th>
                  <th className="pb-3 pr-4">Date</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {orders.map((o) => (
                  <tr key={o.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 pr-4 font-mono text-xs text-gray-600">{o.order_number}</td>
                    <td className="py-3 pr-4 text-gray-500">#{o.product_id}</td>
                    <td className="py-3 pr-4 text-right font-medium text-gray-800">{o.quantity}</td>
                    <td className="py-3 pr-4 text-right font-semibold text-gray-900">
                      {(o.total_cost || 0).toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 text-gray-500 max-w-[120px] truncate">{o.supplier || '—'}</td>
                    <td className="py-3 pr-4 text-xs text-gray-400">
                      {new Date(o.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                        statusStyle[o.status] || 'bg-gray-50 text-gray-600'
                      }`}>
                        {statusIcon[o.status]}
                        {o.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="py-3">
                      {o.status === 'pending' && (
                        <div className="flex gap-2">
                          <button
                            disabled={updating === o.id}
                            onClick={() => handleAction(o.id, 'approved')}
                            className="px-2.5 py-1 text-xs bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            disabled={updating === o.id}
                            onClick={() => handleAction(o.id, 'rejected')}
                            className="px-2.5 py-1 text-xs bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 transition-colors"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                      {o.status === 'sent_to_vendor' && (
                        <button
                          disabled={updating === o.id}
                          onClick={() => handleAction(o.id, 'received')}
                          className="px-2.5 py-1 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                          Mark Received
                        </button>
                      )}
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
