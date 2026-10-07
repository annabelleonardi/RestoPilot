import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ReviewItem } from "../../types";

const COLORS = { positive: "#10b981", neutral: "#f59e0b", negative: "#ef4444" } as const;

/** Real sentiment split + average rating, computed from the reviews the page
 * fetched (backend) or the offline demo fallback — never hardcoded. */
export default function SentimentDonut({ reviews }: { reviews: ReviewItem[] }) {
  const count = (sentiment: ReviewItem["sentiment"]) =>
    reviews.filter((r) => r.sentiment === sentiment).length;
  const DIST = [
    { name: "Positive", value: count("positive"), color: COLORS.positive },
    { name: "Neutral", value: count("neutral"), color: COLORS.neutral },
    { name: "Negative", value: count("negative"), color: COLORS.negative },
  ];
  const avg = reviews.length
    ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
    : 0;

  return (
    <div>
      <div className="relative">
        <ResponsiveContainer width="100%" height={210}>
          <PieChart>
            <Pie data={DIST} dataKey="value" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={3} strokeWidth={0}>
              {DIST.map((d) => (
                <Cell key={d.name} fill={d.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-slate-800">{avg.toFixed(1)}★</span>
          <span className="text-xs text-slate-400">
            {reviews.length} review{reviews.length === 1 ? "" : "s"}
          </span>
        </div>
      </div>
      <div className="mt-2 flex justify-center gap-4 text-xs text-slate-500">
        {DIST.map((d) => (
          <span key={d.name} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
            {d.name} ({d.value})
          </span>
        ))}
      </div>
    </div>
  );
}
