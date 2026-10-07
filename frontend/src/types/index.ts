/* Shared types — shapes mirror backend/app/api/routes/dashboard.py responses. */

export interface PriceAlertItem {
  ingredient: string;
  current: number;
  baseline: number;
  spike_pct: number;
}

export interface KpiSummary {
  daily_sales_idr: number;
  cogs_idr: number;
  gross_margin_pct: number;
  low_stock_count: number;
  pending_confirmations: number;
  sentiment_score: number;
  top_price_increases?: PriceAlertItem[];
}

export interface SalesPoint {
  day: string;
  revenue: number;
  cogs: number;
}

export interface MenuItemStat {
  name: string;
  sold: number;
  revenue: number;
  margin_pct: number;
  sentiment: number;
}

export interface SupplierPricePoint {
  ingredient: string;
  current: number;
  baseline: number;
  spike_pct: number;
}

export interface InventoryItem {
  name: string;
  stock: number;
  unit: string;
  reorder_point: number;
  supplier: string;
}

export interface SupplierRow {
  name: string;
  ingredients: number;
  avg_price_delta_pct: number;
  status: "verified" | "watch" | "new";
}

export interface PaymentRow {
  supplier: string;
  description: string;
  amount: number;
  due_date: string;
  status: "pending" | "paid" | "overdue";
}

export interface ReviewItem {
  id: number;
  platform: string;
  customer: string;
  rating: number;
  comment: string;
  menu_item: string | null;
  sentiment: "positive" | "neutral" | "negative";
  draft_reply: string | null;
}

export interface AlertItem {
  level: "danger" | "warning" | "info";
  title: string;
  detail: string;
}

export interface ConfirmationItem {
  id: number;
  action_type: string;
  summary: string;
  requested_via: string;
  created_at: string;
}

export interface PaymentsSummary {
  payments: PaymentRow[];
  total_due_next_7_days: number;
}

export interface ChatMessage {
  id: number;
  from: "owner" | "bot";
  kind: "text" | "voice" | "card" | "image";
  text: string;
  time: string;
  /** For kind === "image": which invoice fixture to render. */
  variant?: "printed" | "handwritten";
  /** Optional plain-English caption under a scripted bubble (judge-readable). */
  caption?: string;
}
