import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import Card from "../components/layout/Card";
import SentimentDonut from "../components/charts/SentimentDonut";
import { getJson } from "../api/client";
import { demoReviews } from "../data/demoData";
import type { ReviewItem } from "../types";

const SENTIMENT_STYLES = {
  positive: "bg-emerald-50 text-emerald-600",
  neutral: "bg-slate-100 text-slate-500",
  negative: "bg-red-50 text-red-500",
};

export default function Reviews() {
  const [reviews, setReviews] = useState<ReviewItem[]>(demoReviews);
  const [decisions, setDecisions] = useState<Record<number, "approved" | "dismissed">>({});

  useEffect(() => {
    getJson<ReviewItem[]>("/dashboard/reviews", demoReviews).then(setReviews);
  }, []);

  // TODO(MVP): wire to POST /api/confirmations/{id}/approve|reject so the
  // approved reply is actually sent from the WhatsApp channel.
  const decide = (id: number, value: "approved" | "dismissed") =>
    setDecisions((d) => ({ ...d, [id]: value }));

  return (
    <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
      <Card title="Sentiment Split" subtitle="Last 30 days across all platforms">
        <SentimentDonut reviews={reviews} />
      </Card>

      <Card title="Customer Reviews" subtitle="Draft replies require owner approval before sending">
        <div className="space-y-4">
          {reviews.map((r) => (
            <div key={r.id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-700">{r.customer}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                  {r.platform}
                </span>
                {r.menu_item && (
                  <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-600">
                    {r.menu_item}
                  </span>
                )}
                <span
                  className={`ml-auto rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${SENTIMENT_STYLES[r.sentiment]}`}
                >
                  {r.sentiment}
                </span>
              </div>

              <div className="mt-1.5 flex items-center gap-0.5">
                {Array.from({ length: 5 }, (_, i) => (
                  <Star
                    key={i}
                    size={13}
                    className={i < r.rating ? "fill-amber-400 text-amber-400" : "text-slate-200"}
                  />
                ))}
              </div>

              <p className="mt-2 text-sm text-slate-600">{r.comment}</p>

              {r.draft_reply && decisions[r.id] === undefined && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p className="text-xs font-semibold text-amber-700">
                    Draft reply — awaiting your approval
                  </p>
                  <p className="mt-1 text-sm text-slate-600">{r.draft_reply}</p>
                  <div className="mt-2.5 flex gap-2">
                    <button
                      onClick={() => decide(r.id, "approved")}
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-700"
                    >
                      Approve &amp; Send
                    </button>
                    <button
                      onClick={() => decide(r.id, "dismissed")}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-50"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )}

              {r.draft_reply && decisions[r.id] && (
                <p className="mt-3 text-xs font-medium text-emerald-600">
                  {decisions[r.id] === "approved"
                    ? "Reply approved and queued to send"
                    : "Draft dismissed"}
                </p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
