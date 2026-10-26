import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'indigo';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subtext,
  icon,
  variant = 'default',
}) => {
  const valueColors = {
    default: 'text-slate-100',
    success: 'text-emerald-400',
    indigo: 'text-indigo-400',
  };

  return (
    <div className="py-4 space-y-1">
      <div className="flex items-center space-x-1.5 text-slate-500">
        {icon && <span className="opacity-70">{icon}</span>}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <div className={`text-2xl font-bold tabular-nums ${valueColors[variant]}`}>{value}</div>
      {subtext && <p className="text-xs text-slate-600">{subtext}</p>}
    </div>
  );
};
