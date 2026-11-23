import { ReactNode } from 'react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  color: 'brand' | 'emerald' | 'amber' | 'red';
}

// Glass card + a soft coloured wash. Colours resolve through CSS variables /
// dark-mode overrides, so each card reads correctly in both themes.
const surfaceMap = {
  brand: 'border-brand-200/80 from-brand-100/70',
  emerald: 'border-emerald-200 from-emerald-100/80 dark:from-emerald-500/15',
  amber: 'border-amber-200 from-amber-100/80 dark:from-amber-500/15',
  red: 'border-red-200 from-red-100/80 dark:from-red-500/15',
};

const iconMap = {
  brand: 'bg-brand-600 text-white',
  emerald: 'bg-emerald-600 text-white',
  amber: 'bg-amber-500 text-white',
  red: 'bg-red-500 text-white',
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
    <div
      className={`glass group relative overflow-hidden rounded-2xl border bg-gradient-to-br to-transparent p-5 shadow-glass transition-all duration-300 hover:-translate-y-1 hover:shadow-glow animate-fade-up ${surfaceMap[color]}`}
    >
      <div className="mb-4 flex items-start justify-between">
        <div className={`rounded-xl p-2.5 shadow-sm transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-3 ${iconMap[color]}`}>
          {icon}
        </div>
      </div>
      <div className={`mb-0.5 text-2xl font-bold tracking-tight ${valueMap[color]}`}>{value}</div>
      <div className="text-sm font-medium text-ash-600">{title}</div>
      {subtitle && <div className="mt-1 text-xs text-ash-500">{subtitle}</div>}
    </div>
  );
}
