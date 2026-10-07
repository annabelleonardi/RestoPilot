import type { ReactNode } from "react";

interface KpiCardProps {
  icon: ReactNode;
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "warning" | "danger" | "success";
}

const TONES = {
  default: "bg-slate-50 text-slate-600",
  warning: "bg-amber-50 text-amber-600",
  danger: "bg-red-50 text-red-600",
  success: "bg-emerald-50 text-emerald-600",
};

export default function KpiCard({ icon, label, value, sub, tone = "default" }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div
        className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg ${TONES[tone]}`}
      >
        {icon}
      </div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-800">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}
