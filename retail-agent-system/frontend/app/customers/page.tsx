'use client';

import { useEffect, useState } from 'react';
import { getCustomers } from '@/lib/api';
import { Users, Star, RefreshCw, Search } from 'lucide-react';

interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string;
  loyalty_points: number;
  total_spent: number;
  is_active: boolean;
  created_at: string;
}

const PAGE_SIZE = 20;

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);

  const load = (q = query, p = page) => {
    setLoading(true);
    getCustomers({ skip: p * PAGE_SIZE, limit: PAGE_SIZE, ...(q && { search: q }) })
      .then((res) => setCustomers(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [query, page]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setQuery(search);
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="text-sm text-gray-500 mt-1">Customer profiles and loyalty points</p>
        </div>
        <button
          onClick={() => load()}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name..."
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Search
        </button>
        {query && (
          <button
            type="button"
            onClick={() => { setSearch(''); setQuery(''); setPage(0); }}
            className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Clear
          </button>
        )}
      </form>

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-400 text-sm">Loading customers...</div>
        ) : customers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-400">
            <Users className="w-8 h-8 mb-2 opacity-40" />
            <span className="text-sm">No customers found.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase text-gray-500 font-semibold">
                  <th className="pb-3 pr-4">ID</th>
                  <th className="pb-3 pr-4">Name</th>
                  <th className="pb-3 pr-4">Email</th>
                  <th className="pb-3 pr-4">Phone</th>
                  <th className="pb-3 pr-4 text-right">Total Spent</th>
                  <th className="pb-3 pr-4 text-right">
                    <span className="flex items-center justify-end gap-1">
                      <Star className="w-3 h-3" /> Points
                    </span>
                  </th>
                  <th className="pb-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {customers.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-3 pr-4 text-gray-400 text-xs">#{c.id}</td>
                    <td className="py-3 pr-4 font-medium text-gray-900">{c.name}</td>
                    <td className="py-3 pr-4 text-gray-500">{c.email || '—'}</td>
                    <td className="py-3 pr-4 text-gray-500">{c.phone || '—'}</td>
                    <td className="py-3 pr-4 text-right font-medium text-gray-800">
                      Rs. {(c.total_spent || 0).toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 text-right">
                      <span className="inline-flex items-center gap-1 text-yellow-700 font-semibold">
                        <Star className="w-3 h-3 text-yellow-500 fill-yellow-400" />
                        {c.loyalty_points ?? 0}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        c.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>
                        {c.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-50">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="text-sm text-gray-500 hover:text-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>
            <span className="text-xs text-gray-400">Page {page + 1}</span>
            <button
              disabled={customers.length < PAGE_SIZE}
              onClick={() => setPage((p) => p + 1)}
              className="text-sm text-gray-500 hover:text-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
