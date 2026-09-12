import { ReactNode } from 'react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  color: 'brand' | 'emerald' | 'amber' | 'red';
}

// Tinted surface + deep ink: reads light, still 7:1+ on every label.
const surfaceMap = {
  brand: 'bg-brand-50 border-brand-200',
  emerald: 'bg-emerald-50 border-emerald-200',
  amber: 'bg-amber-50 border-amber-200',
  red: 'bg-red-50 border-red-200',
};

const iconMap = {
  brand: 'bg-brand-100 text-brand-700',
  emerald: 'bg-emerald-100 text-emerald-700',
  amber: 'bg-amber-100 text-amber-700',
  red: 'bg-red-100 text-red-700',
};

// The value carries the hue; labels stay neutral so they never drop below AA.
const valueMap = {
  brand: 'text-brand-900',
  emerald: 'text-emerald-900',
  amber: 'text-amber-900',
  red: 'text-red-900',
};

export default function KpiCard({ title, value, subtitle, icon, color }: Props) {
  return (
    <div className={`rounded-xl border p-5 ${surfaceMap[color]}`}>
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-lg ${iconMap[color]}`}>{icon}</div>
      </div>
      <div className={`text-2xl font-bold mb-0.5 ${valueMap[color]}`}>{value}</div>
      <div className="text-sm font-medium text-ash-600">{title}</div>
      {subtitle && <div className="text-xs text-ash-600 mt-1">{subtitle}</div>}
    </div>
  );
}
