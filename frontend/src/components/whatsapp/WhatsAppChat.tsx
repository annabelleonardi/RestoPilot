import { useEffect, useRef, useState } from "react";
import { Mic, RotateCcw, Send } from "lucide-react";
import type { ChatMessage } from "../../types";
import { postJson } from "../../api/client";
import { ReceiptImage, type ReceiptVariant } from "./InvoiceReceipt";

/* Scripted end-to-end flow (safe for presentations): invoice photo → OCR
 * parse → price audit → human-in-the-loop approval, plus the outbound daily
 * summary. Timings are simulated with a typing indicator.
 * Live mode instead calls POST /api/whatsapp/simulate and renders the real
 * AgentReply from the backend (offline fallback keeps the demo shareable). */
const SCRIPT: ChatMessage[] = [
  {
    id: 1, from: "owner", kind: "image", variant: "printed", time: "08:01",
    text: "📷 Foto nota — Toko Berkat Jaya #TBJ-2026-0413",
    caption: "Owner sends a supplier invoice photo — Toko Berkat Jaya. No app, no forms.",
  },
  {
    id: 2, from: "bot", kind: "card", time: "08:02",
    text: "🧾 Invoice parsed — Toko Berkat Jaya #TBJ-2026-0413\n• Beras Premium 50 kg × Rp14.200\n• Minyak Goreng 20 L × Rp17.500\n• Telur Ayam 10 kg × Rp28.500\nTotal: Rp1.345.000",
    caption: "OCR reads the bill — three line items, Rp1.345.000 total, logged with zero typing.",
  },
  {
    id: 3, from: "bot", kind: "card", time: "08:02",
    text: "🔺 Price alert — Beras Premium is +2.2% above your 30-day average.\n💡 Toko Sumber Rejeki (verified) offers Rp13.400/kg — saves Rp40.000 per 50 kg.",
    caption: "Every unit price is audited against the 30-day average, with cheaper verified suppliers.",
  },
  {
    id: 4, from: "bot", kind: "card", time: "08:03",
    text: "🛒 Draft purchase order: 50 kg Beras Premium from Toko Sumber Rejeki — Rp695.000 (harga terakhir Rp13.900/kg).\nReply ya to confirm, or no to keep Berkat Jaya.",
    caption: "A draft order is proposed — nothing is ever ordered without the owner's approval.",
  },
  {
    id: 5, from: "owner", kind: "text", time: "08:05", text: "ya",
    caption: "The owner approves by replying 'ya' — that's the whole flow.",
  },
  {
    id: 6, from: "bot", kind: "card", time: "08:05",
    text: "✅ PO dicatat — pembayaran masuk daftar tagihan di dashboard.",
    caption: "Order recorded — the payment now sits in the bills list on the dashboard.",
  },
  {
    id: 7, from: "owner", kind: "text", time: "08:12", text: "beli cabai 3 kg 150rb",
    caption: "Market runs have no invoices — the owner just types the purchase in plain Bahasa.",
  },
  {
    id: 8, from: "bot", kind: "card", time: "08:12",
    text: "✅ Cabai Merah 3 kg dicatat — Rp150.000 (±Rp50.000/kg). Stok diperbarui ya.\n\n⚠️ Harga naik 13.6% vs rata-rata 30 hari.\nSudah kusiapkan draft pesanan — approve di dashboard ya.",
    caption: "Same engine as invoices: per-unit price computed, stock updated, spike flagged.",
  },
  {
    id: 9, from: "owner", kind: "text", time: "08:13", text: "ya",
    caption: "Approves the draft right in chat — human-in-the-loop, zero friction.",
  },
  {
    id: 10, from: "bot", kind: "card", time: "08:13",
    text: "✅ Siap! Pesanan Cabai Merah disetujui — PO dicatat, pembayaran masuk daftar tagihan di dashboard.",
    caption: "Same HITL flow as the invoice spike — chat and dashboard stay in sync.",
  },
  {
    id: 11, from: "owner", kind: "voice", time: "08:15", text: "Voice note · 0:07",
    caption: "Hands full? The owner can just talk (transcription is mocked in this demo).",
  },
  {
    id: 12, from: "bot", kind: "card", time: "08:15",
    text: "🎤 Transcribed: “Bu, beras naik lagi jadi 14.200 per kilo, kata Toko Berkat Jaya. Stok cabai juga tinggal sedikit.”\n\nOke, aku catat ya — dari catatan harga kita, Beras Premium memang lagi naik. Nanti aku cek supplier verified yang lebih murah.",
    caption: "Voice notes are transcribed and flow through the same pipeline.",
  },
  {
    id: 13, from: "bot", kind: "voice", time: "08:21",
    text: "☀️ Daily summary · 0:28 — “Penjualan hari ini Rp4,28 juta, margin 59,5%. Cabai merah perlu di-reorder besok. Satu balasan ulasan menunggu persetujuan Anda.”",
    caption: "Every morning: a 30-second voice digest of sales, stock, and what needs attention.",
  },
];

interface AgentReply {
  reply_text: string;
  agent: string;
}

const LIVE_FALLBACK: AgentReply = {
  agent: "orchestrator",
  reply_text:
    "(Backend offline) Start uvicorn (app.main:app) and this chat will call the real /api/whatsapp/simulate endpoint.",
};

function nowLabel(): string {
  return new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

export default function WhatsAppChat() {
  const [live, setLive] = useState(false);
  const [visible, setVisible] = useState(0);
  const [typing, setTyping] = useState(false);
  const [liveMessages, setLiveMessages] = useState<ChatMessage[]>([]);
  const [liveBusy, setLiveBusy] = useState(false);
  const [input, setInput] = useState("");
  const started = useRef(false);
  const nextId = useRef(1000);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Autoplay the script once (guard against StrictMode double-invoke).
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    setVisible(1);
  }, []);

  // Reveal the next scripted message on a timer (scripted mode only).
  useEffect(() => {
    if (live || visible === 0 || visible >= SCRIPT.length) return;
    const next = SCRIPT[visible];
    const isBot = next.from === "bot";
    if (isBot) setTyping(true);
    const delay = isBot ? 1600 : 1000;
    const t = setTimeout(() => {
      setTyping(false);
      setVisible((v) => v + 1);
    }, delay);
    return () => clearTimeout(t);
  }, [visible, live]);

  // Keep the latest message in view.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [visible, typing, liveMessages, liveBusy]);

  const sendLive = async (opts: {
    kind: "text" | "image" | "voice";
    text: string;
    variant?: ReceiptVariant;
  }) => {
    if (liveBusy) return;
    const ownerMsg: ChatMessage = {
      id: nextId.current++,
      from: "owner",
      kind: opts.kind,
      text: opts.text,
      time: nowLabel(),
      variant: opts.variant,
    };
    setLiveMessages((m) => [...m, ownerMsg]);
    setLiveBusy(true);
    const body =
      opts.kind === "image"
        ? { message_type: "image", media_url: "demo-photo" }
        : opts.kind === "voice"
          ? { message_type: "audio", media_url: "demo-voice" }
          : { message_type: "text", text: opts.text };
    const reply = await postJson<AgentReply>("/whatsapp/simulate", body, LIVE_FALLBACK);
    setLiveMessages((m) => [
      ...m,
      { id: nextId.current++, from: "bot", kind: "card", text: reply.reply_text, time: nowLabel() },
    ]);
    setLiveBusy(false);
  };

  const submitInput = () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    void sendLive({ kind: "text", text });
  };

  const replay = () => {
    setLive(false);
    setLiveMessages([]);
    setVisible(1);
    setTyping(false);
  };

  const messages = live ? liveMessages : SCRIPT.slice(0, visible);

  return (
    <div className="w-[350px] max-w-full">
      {/* Mode toggle: scripted autoplay is the default (safe to present). */}
      <div className="mb-3 flex items-center justify-center gap-2">
        <button
          onClick={() => setLive(false)}
          className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
            !live ? "bg-[#075E54] text-white" : "border border-slate-200 bg-white text-slate-500"
          }`}
        >
          Demo script
        </button>
        <button
          onClick={() => setLive(true)}
          className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
            live ? "bg-[#075E54] text-white" : "border border-slate-200 bg-white text-slate-500"
          }`}
        >
          Live mode
        </button>
      </div>

      <div className="overflow-hidden rounded-[2.2rem] border-[10px] border-slate-800 bg-[#ECE5DD] shadow-2xl">
        <header className="flex items-center gap-3 bg-[#075E54] px-4 py-3 text-white">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20 text-sm font-bold">
            RP
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">RestoPilot Assistant</p>
            <p className="text-[11px] text-white/70">
              {live ? "live backend" : "online"}
            </p>
          </div>
        </header>

        <div ref={scrollRef} className="h-[440px] space-y-2 overflow-y-auto px-3 py-4">
          {messages.map((m) => (
            <Bubble key={m.id} msg={m} />
          ))}
          {(typing || (live && liveBusy)) && <TypingBubble />}
        </div>

        {live ? (
          <div className="space-y-2 px-3 pb-4">
            <div className="flex gap-2">
              <button
                onClick={() => void sendLive({ kind: "image", text: "📷 Foto nota — Toko Berkat Jaya #TBJ-2026-0413", variant: "printed" })}
                disabled={liveBusy}
                className="flex-1 rounded-full bg-white px-2 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
              >
                📷 Kirim foto nota
              </button>
              <button
                onClick={() => void sendLive({ kind: "image", text: "✍️ Nota tulisan tangan — Toko Berkat Jaya #TBJ-2026-0413", variant: "handwritten" })}
                disabled={liveBusy}
                className="flex-1 rounded-full bg-white px-2 py-1.5 text-[11px] font-medium text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
              >
                ✍️ Nota tulisan tangan
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => void sendLive({ kind: "voice", text: "Voice note · 0:07" })}
                disabled={liveBusy}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-[#075E54] shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
                aria-label="Send voice note"
              >
                <Mic size={16} />
              </button>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitInput()}
                placeholder="Try 'beli cabai 3 kg 150rb', 'ya', 'stok'…"
                className="flex-1 rounded-full bg-white px-4 py-2 text-sm text-slate-700 outline-none placeholder:text-slate-400"
              />
              <button
                onClick={submitInput}
                disabled={liveBusy}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-[#075E54] text-white transition hover:bg-[#0b6b60] disabled:opacity-50"
                aria-label="Send"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 pb-4">
            <div className="flex-1 rounded-full bg-white px-4 py-2 text-sm text-slate-400">
              Switch to Live mode to type
            </div>
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#075E54] text-white">
              <Mic size={16} />
            </span>
          </div>
        )}
      </div>

      <button
        onClick={replay}
        className="mx-auto mt-4 flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:bg-slate-50"
      >
        <RotateCcw size={14} /> Replay demo
      </button>
    </div>
  );
}

function Bubble({ msg }: { msg: ChatMessage }) {
  // Owner's phone POV: the owner's own messages sit right (green, outgoing),
  // the RestoPilot agent replies left (white, incoming) — like real WhatsApp.
  const mine = msg.from === "owner";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[85%] flex-col gap-0.5 ${mine ? "items-end" : "items-start"}`}>
        {msg.kind === "image" ? (
          <div className="relative max-w-[92%] overflow-hidden rounded-xl shadow-sm">
            <div className="flex items-center justify-center bg-gradient-to-br from-stone-300 via-stone-400 to-stone-500 px-5 py-4">
              <ReceiptImage variant={msg.variant ?? "printed"} className="h-60 w-auto drop-shadow-md" />
            </div>
            <span className="absolute bottom-1.5 right-2 rounded-full bg-black/40 px-1.5 py-0.5 text-[10px] text-white">
              {msg.time}
            </span>
          </div>
        ) : (
          <div
            className={`max-w-full rounded-xl px-3 py-2 text-[13px] leading-snug shadow-sm ${
              mine ? "rounded-br-sm bg-[#DCF8C6] text-slate-800" : "rounded-bl-sm bg-white text-slate-700"
            }`}
          >
            {msg.kind === "voice" ? (
              <span className="flex items-start gap-2">
                <Mic size={14} className="mt-0.5 shrink-0 text-[#075E54]" />
                <span className="whitespace-pre-line">{msg.text}</span>
              </span>
            ) : (
              <span className="whitespace-pre-line">{msg.text}</span>
            )}
            <span className="mt-1 block text-right text-[10px] text-slate-400">{msg.time}</span>
          </div>
        )}
        {msg.caption && (
          <span
            className={`px-1 text-[10.5px] italic leading-tight text-slate-500 ${
              mine ? "text-right" : "text-left"
            }`}
          >
            {msg.caption}
          </span>
        )}
      </div>
    </div>
  );
}

function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-xl rounded-bl-sm bg-white px-3 py-2.5 shadow-sm">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
