import { useEffect, useState } from "react";
import Card from "../components/layout/Card";
import { getJson } from "../api/client";
import { demoInventory } from "../data/demoData";
import type { InventoryItem } from "../types";

export default function Inventory() {
  const [items, setItems] = useState<InventoryItem[]>(demoInventory);

  useEffect(() => {
    getJson<InventoryItem[]>("/dashboard/inventory", demoInventory).then(setItems);
  }, []);

  return (
    <Card
      title="Stock Levels"
      subtitle="Reorder point = avg daily usage × (lead time + 2-day safety buffer)"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
              <th className="pb-3 pr-4 font-medium">Ingredient</th>
              <th className="pb-3 pr-4 font-medium">In stock</th>
              <th className="pb-3 pr-4 font-medium">Reorder point</th>
              <th className="pb-3 pr-4 font-medium">Supplier</th>
              <th className="pb-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => {
              const low = it.stock <= it.reorder_point;
              return (
                <tr key={it.name} className="border-b border-slate-50 last:border-0">
                  <td className="py-3 pr-4 font-medium text-slate-700">{it.name}</td>
                  <td className="py-3 pr-4 text-slate-600">
                    {it.stock} {it.unit}
                  </td>
                  <td className="py-3 pr-4 text-slate-500">
                    {it.reorder_point} {it.unit}
                  </td>
                  <td className="py-3 pr-4 text-slate-500">{it.supplier}</td>
                  <td className="py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        low ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-600"
                      }`}
                    >
                      {low ? "Low stock" : "Healthy"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
