/* Demo dataset — mirrors backend/app/api/routes/dashboard.py so the
 * frontend can run standalone when shared with teammates. */
import type {
  AlertItem,
  ConfirmationItem,
  InventoryItem,
  KpiSummary,
  MenuItemStat,
  PaymentRow,
  PaymentsSummary,
  ReviewItem,
  SalesPoint,
  SupplierPricePoint,
  SupplierRow,
} from "../types";

export const demoKpis: KpiSummary = {
  daily_sales_idr: 4_280_000,
  cogs_idr: 1_733_000,
  gross_margin_pct: 59.5,
  low_stock_count: 2,
  pending_confirmations: 1,
  sentiment_score: 4.3,
  top_price_increases: [
    { ingredient: "Cabai Merah", current: 52_000, baseline: 44_000, spike_pct: 18.2 },
    { ingredient: "Beras Premium", current: 14_200, baseline: 13_889, spike_pct: 2.2 },
  ],
};

export const demoSalesTrend: SalesPoint[] = [
  { day: "Sep 22", revenue: 3_420_000, cogs: 1_402_000 },
  { day: "Sep 23", revenue: 3_180_000, cogs: 1_304_000 },
  { day: "Sep 24", revenue: 3_650_000, cogs: 1_497_000 },
  { day: "Sep 25", revenue: 3_310_000, cogs: 1_357_000 },
  { day: "Sep 26", revenue: 3_870_000, cogs: 1_587_000 },
  { day: "Sep 27", revenue: 4_120_000, cogs: 1_689_000 },
  { day: "Sep 28", revenue: 4_380_000, cogs: 1_796_000 },
  { day: "Sep 29", revenue: 3_550_000, cogs: 1_456_000 },
  { day: "Sep 30", revenue: 3_290_000, cogs: 1_349_000 },
  { day: "Oct 1", revenue: 3_780_000, cogs: 1_550_000 },
  { day: "Oct 2", revenue: 3_940_000, cogs: 1_615_000 },
  { day: "Oct 3", revenue: 4_050_000, cogs: 1_660_000 },
  { day: "Oct 4", revenue: 4_210_000, cogs: 1_726_000 },
  { day: "Oct 5", revenue: 4_280_000, cogs: 1_733_000 },
];

export const demoMenuPerformance: MenuItemStat[] = [
  { name: "Nasi Ayam Bakar", sold: 312, revenue: 6_864_000, margin_pct: 59.1, sentiment: 4.6 },
  { name: "Nasi Goreng Spesial", sold: 240, revenue: 6_000_000, margin_pct: 60.0, sentiment: 4.4 },
  { name: "Ayam Geprek", sold: 205, revenue: 4_715_000, margin_pct: 58.7, sentiment: 3.9 },
  { name: "Es Teh Jeruk", sold: 380, revenue: 3_040_000, margin_pct: 75.0, sentiment: 4.5 },
  { name: "Soto Ayam", sold: 98, revenue: 1_960_000, margin_pct: 60.0, sentiment: 4.1 },
];

export const demoSupplierPrices: SupplierPricePoint[] = [
  { ingredient: "Cabai Merah", current: 52_000, baseline: 44_000, spike_pct: 18.2 },
  { ingredient: "Beras Premium", current: 14_200, baseline: 13_889, spike_pct: 2.2 },
  { ingredient: "Telur Ayam", current: 28_500, baseline: 27_500, spike_pct: 3.6 },
  { ingredient: "Ayam Utuh", current: 39_000, baseline: 38_500, spike_pct: 1.3 },
  { ingredient: "Minyak Goreng", current: 17_500, baseline: 18_000, spike_pct: -2.8 },
];

export const demoInventory: InventoryItem[] = [
  { name: "Cabai Merah", stock: 3, unit: "kg", reorder_point: 5, supplier: "UD Pasar Segar" },
  { name: "Telur Ayam", stock: 4, unit: "kg", reorder_point: 6, supplier: "Toko Berkat Jaya" },
  { name: "Beras Premium", stock: 38, unit: "kg", reorder_point: 25, supplier: "Toko Sumber Rejeki" },
  { name: "Minyak Goreng", stock: 16, unit: "L", reorder_point: 10, supplier: "Toko Berkat Jaya" },
  { name: "Ayam Utuh", stock: 12, unit: "kg", reorder_point: 8, supplier: "UD Pasar Segar" },
  { name: "Kecap Manis", stock: 9, unit: "btl", reorder_point: 4, supplier: "Toko Berkat Jaya" },
];

export const demoSuppliers: SupplierRow[] = [
  { name: "Toko Berkat Jaya", ingredients: 4, avg_price_delta_pct: 4.1, status: "watch" },
  { name: "Toko Sumber Rejeki", ingredients: 3, avg_price_delta_pct: -3.2, status: "verified" },
  { name: "UD Pasar Segar", ingredients: 5, avg_price_delta_pct: 0.8, status: "verified" },
  { name: "UD Segar Makmur", ingredients: 2, avg_price_delta_pct: 0.0, status: "new" },
];

export const demoReviews: ReviewItem[] = [
  {
    id: 1, platform: "Google", customer: "Ibu Ratna", rating: 5,
    comment: "Ayam bakarnya juara, sambalnya pedas pas!", menu_item: "Nasi Ayam Bakar",
    sentiment: "positive", draft_reply: null,
  },
  {
    id: 2, platform: "GoFood", customer: "Dedi", rating: 4,
    comment: "Fast delivery, portion could be bigger.", menu_item: "Nasi Goreng Spesial",
    sentiment: "positive", draft_reply: null,
  },
  {
    id: 3, platform: "GoFood", customer: "Anonymous", rating: 2,
    comment: "Ayamnya agak keras hari ini 😞", menu_item: "Ayam Geprek",
    sentiment: "negative",
    draft_reply:
      "Terima kasih banyak for your feedback! We're sorry the chicken was tough that day — we've shared this with our kitchen team and hope to serve you better next time.",
  },
  {
    id: 4, platform: "Google", customer: "Kevin", rating: 3,
    comment: "Rasa oke tapi tunggu lama pas jam makan siang.", menu_item: null,
    sentiment: "neutral", draft_reply: null,
  },
  {
    id: 5, platform: "GrabFood", customer: "Sinta", rating: 5,
    comment: "Es teh jeruknya segar, harga bersahabat.", menu_item: "Es Teh Jeruk",
    sentiment: "positive", draft_reply: null,
  },
  {
    id: 6, platform: "Google", customer: "Pak Wishnu", rating: 4,
    comment: "Soto ayam kaldunya gurih. Recommended.", menu_item: "Soto Ayam",
    sentiment: "positive", draft_reply: null,
  },
];

export const demoPayments: PaymentRow[] = [
  { supplier: "Toko Berkat Jaya", description: "Invoice TBJ-2026-0413 — dry goods", amount: 1_345_000, due_date: "2026-10-13", status: "pending" },
  { supplier: "UD Pasar Segar", description: "Weekly fresh produce", amount: 850_000, due_date: "2026-10-05", status: "overdue" },
  { supplier: "Toko Sumber Rejeki", description: "PO-2026-0087 — Beras Premium 50 kg", amount: 670_000, due_date: "2026-10-10", status: "pending" },
];

export const demoPaymentsSummary: PaymentsSummary = {
  payments: demoPayments,
  total_due_next_7_days: 2_865_000,
};

export const demoConfirmations: ConfirmationItem[] = [
  {
    id: 1,
    action_type: "place_order",
    summary: "Order 50 kg Beras Premium from Toko Sumber Rejeki · Rp670,000",
    requested_via: "whatsapp",
    created_at: "2026-10-06T08:03:00",
  },
  {
    id: 2,
    action_type: "place_order",
    summary: "Order 10 kg Telur Ayam from Toko Berkat Jaya · Rp285,000",
    requested_via: "whatsapp",
    created_at: "2026-10-06T09:12:00",
  },
];

export const demoAlerts: AlertItem[] = [
  {
    level: "danger",
    title: "Cabai Merah below reorder point",
    detail: "3 kg left · reorder point 5 kg · UD Pasar Segar",
  },
  {
    level: "warning",
    title: "Beras Premium +2.2% vs 30-day average",
    detail: "Toko Sumber Rejeki offers Rp13,400/kg (−Rp800/kg)",
  },
  {
    level: "info",
    title: "1 review reply awaiting approval",
    detail: "GoFood · Ayam Geprek · 2★",
  },
];
