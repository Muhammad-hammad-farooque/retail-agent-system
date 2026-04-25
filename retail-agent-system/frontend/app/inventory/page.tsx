'use client';

import { useEffect, useState } from 'react';
import { getProducts, getCriticalStock } from '@/lib/api';
import ProductTable from '@/components/ProductTable';
import AlertBanner from '@/components/AlertBanner';
import { Package, AlertTriangle, RefreshCw } from 'lucide-react';

interface Product {
  id: number;
  name: string;
  sku: string;
  category: string;
  price: number;
  quantity: number;
  reorder_level: number;
  supplier: string;
}

const CATEGORIES = ['All', 'Electronics', 'Clothing', 'Food', 'Furniture', 'Cosmetics', 'Sports', 'Stationery'];

export default function InventoryPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [critical, setCritical] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'critical'>('all');
  const [category, setCategory] = useState('All');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const load = () => {
    setLoading(true);
    const params = {
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
      ...(category !== 'All' && { category }),
    };
    Promise.all([getProducts(params), getCriticalStock()])
      .then(([pRes, cRes]) => {
        setProducts(pRes.data);
        setCritical(cRes.data);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, category]);

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
          <p className="text-sm text-gray-500 mt-1">Manage products and stock levels</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <AlertBanner />

      {critical.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 mb-6 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          <div className="text-sm text-red-700">
            <span className="font-semibold">{critical.length} products</span> are below reorder level and need immediate attention.
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit mb-5">
        <button
          onClick={() => setActiveTab('all')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'all' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Package className="w-4 h-4" />
          All Products
        </button>
        <button
          onClick={() => setActiveTab('critical')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'critical' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Critical ({critical.length})
        </button>
      </div>

      {/* Category filter */}
      {activeTab === 'all' && (
        <div className="flex gap-2 flex-wrap mb-5">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => { setCategory(c); setPage(0); }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                category === c
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-blue-300'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 p-6">
        <ProductTable
          products={activeTab === 'all' ? products : critical}
          loading={loading}
        />

        {activeTab === 'all' && !loading && (
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
              disabled={products.length < PAGE_SIZE}
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
