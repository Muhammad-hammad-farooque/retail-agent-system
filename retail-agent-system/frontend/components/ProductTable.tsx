'use client';

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

interface Props {
  products: Product[];
  loading?: boolean;
}

export default function ProductTable({ products, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-40 text-ash-500 text-sm">
        Loading products...
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-ash-500 text-sm">
        No products found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-ash-100 text-left text-xs uppercase text-ash-600 font-semibold">
            <th className="pb-3 pr-4">Name</th>
            <th className="pb-3 pr-4">SKU</th>
            <th className="pb-3 pr-4">Category</th>
            <th className="pb-3 pr-4 text-right">Price (Rs.)</th>
            <th className="pb-3 pr-4 text-right">Stock</th>
            <th className="pb-3 text-right">Reorder Level</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ash-100">
          {products.map((p) => (
            <tr key={p.id} className="hover:bg-ash-50 transition-colors">
              <td className="py-3 pr-4 font-medium text-ash-900">{p.name}</td>
              <td className="py-3 pr-4 text-ash-600 font-mono text-xs">{p.sku}</td>
              <td className="py-3 pr-4">
                <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-brand-50 text-brand-700">
                  {p.category}
                </span>
              </td>
              <td className="py-3 pr-4 text-right text-ash-700">
                {p.price.toLocaleString()}
              </td>
              <td className="py-3 pr-4 text-right">
                <span
                  className={`font-semibold ${
                    p.quantity <= p.reorder_level ? 'text-red-700' : 'text-emerald-700'
                  }`}
                >
                  {p.quantity}
                </span>
              </td>
              <td className="py-3 text-right text-ash-600">{p.reorder_level}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
