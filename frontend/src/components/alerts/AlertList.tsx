import { AlertTriangle, Info, XCircle } from "lucide-react";
import type { AlertItem } from "../../types";

const ICONS = {
  danger: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const COLORS = {
  danger: "bg-red-50 text-red-500",
  warning: "bg-amber-50 text-amber-500",
  info: "bg-sky-50 text-sky-500",
};

export default function AlertList({ alerts }: { alerts: AlertItem[] }) {
  return (
    <ul className="space-y-3">
      {alerts.map((a) => {
        const Icon = ICONS[a.level];
        return (
          <li key={a.title} className="flex items-start gap-3">
            <span
              className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${COLORS[a.level]}`}
            >
              <Icon size={16} />
            </span>
            <div>
              <p className="text-sm font-medium text-slate-700">{a.title}</p>
              <p className="text-xs text-slate-400">{a.detail}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
