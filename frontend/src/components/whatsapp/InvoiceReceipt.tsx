/**
 * Invoice photo fixtures for the WhatsApp demo — hand-built inline SVGs, NOT
 * AI-generated images, so the visible text matches the OCR ground truth
 * (backend app/perception/ocr.py MOCK_INVOICE) line for line:
 *   Toko Berkat Jaya #TBJ-2026-0413 · Beras Premium 50 kg × Rp14.200 ·
 *   Minyak Goreng 20 L × Rp17.500 · Telur Ayam 10 kg × Rp28.500 · Total Rp1.345.000
 *
 * The printed thermal receipt and the handwritten nota render from the same
 * RECEIPT constant, so the two variants (used later as StepFun OCR accuracy
 * fixtures) can never drift apart.
 */

const RECEIPT = {
  supplier: "TOKO BERKAT JAYA",
  invoiceNo: "#TBJ-2026-0413",
  items: [
    { name: "Beras Premium", detail: "50 kg × Rp14.200" },
    { name: "Minyak Goreng", detail: "20 L × Rp17.500" },
    { name: "Telur Ayam", detail: "10 kg × Rp28.500" },
  ],
  total: "Rp1.345.000",
} as const;

const W = 264;
const INK = "#1e3a8a";

/** Paper outline with a torn thermal-receipt zigzag along the bottom edge. */
function paperPath(bottom: number): string {
  const teeth = 14;
  const inner = W - 16;
  let d = `M8 6 H${W - 8} V${bottom}`;
  for (let i = 0; i < teeth; i++) {
    const xMid = W - 8 - (i + 0.5) * (inner / teeth);
    const xEnd = W - 8 - (i + 1) * (inner / teeth);
    d += ` L${xMid} ${bottom + 9} L${xEnd} ${bottom}`;
  }
  return `${d} Z`;
}

export function PrintedReceiptSvg({ className }: { className?: string }) {
  return (
    <svg viewBox={`0 0 ${W} 344`} className={className} role="img" aria-label="Foto nota — Toko Berkat Jaya #TBJ-2026-0413">
      <path d={paperPath(318)} fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
      <text x={W / 2} y="38" textAnchor="middle" fontFamily="'Courier New', monospace" fontWeight="700" fontSize="15" fill="#1f2937">
        {RECEIPT.supplier}
      </text>
      <text x={W / 2} y="58" textAnchor="middle" fontFamily="'Courier New', monospace" fontSize="12" fill="#374151">
        {RECEIPT.invoiceNo}
      </text>
      <line x1="20" y1="72" x2={W - 20} y2="72" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5 4" />
      {RECEIPT.items.map((item, i) => (
        <g key={item.name} fontFamily="'Courier New', monospace" fontSize="11.5" fill="#111827">
          <text x="20" y={100 + i * 24}>{item.name}</text>
          <text x={W - 20} y={100 + i * 24} textAnchor="end">{item.detail}</text>
        </g>
      ))}
      <line x1="20" y1="180" x2={W - 20} y2="180" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5 4" />
      <text x="20" y="208" fontFamily="'Courier New', monospace" fontWeight="700" fontSize="14" fill="#111827">
        Total
      </text>
      <text x={W - 20} y="208" textAnchor="end" fontFamily="'Courier New', monospace" fontWeight="700" fontSize="14" fill="#111827">
        {RECEIPT.total}
      </text>
    </svg>
  );
}

export function HandwrittenReceiptSvg({ className }: { className?: string }) {
  return (
    <svg viewBox={`0 0 ${W} 344`} className={className} role="img" aria-label="Nota tulisan tangan — Toko Berkat Jaya #TBJ-2026-0413">
      <g transform={`rotate(-2 ${W / 2} 172)`}>
        <path d={paperPath(318)} fill="#fffdf4" stroke="#e7e5e4" strokeWidth="1" />
        <text x={W / 2} y="42" textAnchor="middle" fontFamily="'Segoe Script','Bradley Hand','Comic Sans MS',cursive" fontWeight="700" fontSize="17" fill={INK}>
          Toko Berkat Jaya
        </text>
        <text x={W / 2} y="66" textAnchor="middle" fontFamily="'Segoe Script','Bradley Hand','Comic Sans MS',cursive" fontSize="14" fill={INK}>
          {RECEIPT.invoiceNo}
        </text>
        {RECEIPT.items.map((item, i) => (
          <text key={item.name} x="24" y={104 + i * 30} fontFamily="'Segoe Script','Bradley Hand','Comic Sans MS',cursive" fontSize="14" fill={INK}>
            {item.name} — {item.detail}
          </text>
        ))}
        <text x="24" y="216" fontFamily="'Segoe Script','Bradley Hand','Comic Sans MS',cursive" fontWeight="700" fontSize="16" fill={INK}>
          Total {RECEIPT.total}
        </text>
        <path d="M22 224 Q 130 234 244 222" fill="none" stroke={INK} strokeWidth="1.5" strokeLinecap="round" />
      </g>
    </svg>
  );
}

export type ReceiptVariant = "printed" | "handwritten";

export function ReceiptImage({ variant, className }: { variant: ReceiptVariant; className?: string }) {
  return variant === "printed" ? (
    <PrintedReceiptSvg className={className} />
  ) : (
    <HandwrittenReceiptSvg className={className} />
  );
}
