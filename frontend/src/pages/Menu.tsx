import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import Card from "../components/layout/Card";
import MenuPerformanceChart from "../components/charts/MenuPerformanceChart";
import { getJson } from "../api/client";
import { demoMenuPerformance } from "../data/demoData";
import { formatCompactIDR } from "../lib/format";
import type { MenuItemStat } from "../types";

export default function Menu() {
  const [items, setItems] = useState<MenuItemStat[]>(demoMenuPerformance);

  useEffect(() => {
    getJson<MenuItemStat[]>("/dashboard/menu-performance", demoMenuPerformance).then(setItems);
  }, []);

  return (
    <div className="space-y-6">
      <Card title="Units Sold" subtitle="Last 7 days">
        <MenuPerformanceChart data={items} />
      </Card>

      <Card title="Menu Profitability" subtitle="Margin and review sentiment per item">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-3 pr-4 font-medium">Item</th>
                <th className="pb-3 pr-4 font-medium">Sold (7d)</th>
                <th className="pb-3 pr-4 font-medium">Revenue</th>
                <th className="pb-3 pr-4 font-medium">Margin</th>
                <th className="pb-3 font-medium">Sentiment</th>
              </tr>
            </thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.name} className="border-b border-slate-50 last:border-0">
                  <td className="py-3 pr-4 font-medium text-slate-700">{m.name}</td>
                  <td className="py-3 pr-4 text-slate-600">{m.sold}</td>
                  <td className="py-3 pr-4 text-slate-600">{formatCompactIDR(m.revenue)}</td>
                  <td
                    className={`py-3 pr-4 font-medium ${
                      m.margin_pct >= 60
                        ? "text-emerald-600"
                        : m.margin_pct >= 55
                          ? "text-slate-600"
                          : "text-amber-600"
                    }`}
                  >
                    {m.margin_pct}%
                  </td>
                  <td className="py-3">
                    <span className="flex items-center gap-0.5">
                      {Array.from({ length: 5 }, (_, i) => (
                        <Star
                          key={i}
                          size={13}
                          className={i < Math.round(m.sentiment) ? "fill-amber-400 text-amber-400" : "text-slate-200"}
                        />
                      ))}
                      <span className="ml-1.5 text-xs text-slate-400">{m.sentiment.toFixed(1)}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
