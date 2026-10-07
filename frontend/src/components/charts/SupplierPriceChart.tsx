import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SupplierPricePoint } from "../../types";

export default function SupplierPriceChart({ data }: { data: SupplierPricePoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
        <XAxis
          dataKey="ingredient"
          tick={{ fontSize: 11, fill: "#64748b" }}
          axisLine={false}
          tickLine={false}
          interval={0}
          angle={-14}
          textAnchor="end"
          height={56}
        />
        <YAxis
          tickFormatter={(v: number) => `${v}%`}
          tick={{ fontSize: 12, fill: "#64748b" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
        <Bar dataKey="spike_pct" name="Change vs 30-day avg" radius={[6, 6, 0, 0]} barSize={26}>
          {data.map((d) => (
            <Cell
              key={d.ingredient}
              fill={d.spike_pct >= 10 ? "#ef4444" : d.spike_pct > 0 ? "#f59e0b" : "#10b981"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
