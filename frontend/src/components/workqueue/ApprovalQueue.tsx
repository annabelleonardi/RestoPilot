import { useEffect, useState } from "react";
import { Check, Clock, X } from "lucide-react";
import Card from "../layout/Card";
import { getJson, postJson } from "../../api/client";
import { demoConfirmations } from "../../data/demoData";
import type { ConfirmationItem } from "../../types";

interface ApprovalQueueProps {
  /** Notifies the parent so KPI counts (pending confirmations) can refresh. */
  onChanged?: () => void;
}

export default function ApprovalQueue({ onChanged }: ApprovalQueueProps) {
  const [items, setItems] = useState<ConfirmationItem[]>(demoConfirmations);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    getJson<ConfirmationItem[]>("/confirmations", demoConfirmations).then(setItems);
  }, []);

  const decide = async (id: number, action: "approve" | "reject") => {
    setBusyId(id);
    await postJson(`/confirmations/${id}/${action}`, {}, { id, status: action });
    setItems((list) => list.filter((c) => c.id !== id));
    setBusyId(null);
    onChanged?.();
  };

  return (
    <Card
      title="Needs your approval"
      subtitle="Draft orders from price alerts — nothing is ordered without your YES"
    >
      {items.length === 0 ? (
        <p className="text-sm text-slate-400">You're all caught up.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((c) => (
            <li
              key={c.id}
              className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50/60 p-4 sm:flex-row sm:items-center"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-slate-800">{c.summary}</p>
                <p className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-400">
                  <Clock size={12} />
                  {new Date(c.created_at).toLocaleString("en-GB", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 capitalize">
                    via {c.requested_via}
                  </span>
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => decide(c.id, "approve")}
                  disabled={busyId === c.id}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60 sm:flex-none"
                >
                  <Check size={14} /> Approve
                </button>
                <button
                  onClick={() => decide(c.id, "reject")}
                  disabled={busyId === c.id}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-500 transition hover:bg-slate-50 disabled:opacity-60 sm:flex-none"
                >
                  <X size={14} /> Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
