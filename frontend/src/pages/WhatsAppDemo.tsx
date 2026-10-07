import { useState } from "react";
import { Send } from "lucide-react";
import Card from "../components/layout/Card";
import WhatsAppChat from "../components/whatsapp/WhatsAppChat";
import { postJson } from "../api/client";

const FLOW = [
  {
    step: "1",
    title: "Owner sends a photo",
    detail: "The invoice photo arrives on WhatsApp — no app to learn, no forms to fill.",
  },
  {
    step: "2",
    title: "OCR parses the bill",
    detail: "StepFun Vision extracts line items, quantities, and unit prices.",
  },
  {
    step: "3",
    title: "Price audit runs",
    detail: "Each unit cost is checked against the 30-day baseline; spikes are flagged.",
  },
  {
    step: "4",
    title: "Owner approves",
    detail: "A draft purchase order is proposed. Nothing is ordered without an explicit YES.",
  },
  {
    step: "5",
    title: "Everything is logged",
    detail: "Stock, price history, and supplier records update automatically.",
  },
];

interface SummaryReply {
  reply_text: string;
  agent: string;
}

const SUMMARY_FALLBACK: SummaryReply = {
  agent: "orchestrator",
  reply_text:
    "(Backend offline) The daily summary would be composed from agent reports and sent to the owner on WhatsApp.",
};

export default function WhatsAppDemo() {
  const [summary, setSummary] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const sendSummary = async () => {
    setSending(true);
    const res = await postJson<SummaryReply>(
      "/whatsapp/daily-summary",
      {},
      SUMMARY_FALLBACK
    );
    setSummary(res.reply_text);
    setSending(false);
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[auto_1fr]">
      <Card
        title="Live Scripted Demo"
        subtitle="The exact flow your customers would experience on WhatsApp"
      >
        <WhatsAppChat />
      </Card>

      <div className="space-y-6">
        <Card title="How the flow works" subtitle="Human-in-the-loop by design">
          <ol className="space-y-4">
            {FLOW.map((f) => (
              <li key={f.step} className="flex gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">
                  {f.step}
                </span>
                <span>
                  <span className="block text-sm font-semibold text-slate-700">{f.title}</span>
                  <span className="block text-xs text-slate-400">{f.detail}</span>
                </span>
              </li>
            ))}
          </ol>
        </Card>

        <Card
          title="Proactive Daily Summary"
          subtitle="The orchestrator doesn't just react — it pushes a digest to the owner"
        >
          <button
            onClick={sendSummary}
            disabled={sending}
            className="flex items-center gap-2 rounded-lg bg-[#075E54] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0b6b60] disabled:opacity-60"
          >
            <Send size={15} /> {sending ? "Sending..." : "Send daily summary"}
          </button>
          {summary && (
            <pre className="mt-4 whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-[13px] leading-relaxed text-slate-700">
              {summary}
            </pre>
          )}
        </Card>

        <Card title="Try it with the API" subtitle="Run the backend and replay any message">
          <p className="text-sm text-slate-500">
            With the backend running (
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">uvicorn app.main:app</code>
            ), POST to the simulate endpoint to get real agent replies:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-800 p-4 text-xs leading-relaxed text-slate-100">
            {`curl -X POST http://localhost:8000/api/whatsapp/simulate \\
  -H "Content-Type: application/json" \\
  -d '{"message_type": "text", "text": "stok"}'`}
          </pre>
        </Card>
      </div>
    </div>
  );
}
