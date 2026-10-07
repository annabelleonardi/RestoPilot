import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarClock,
  MessageCircle,
  MessageSquare,
  PackageX,
  Percent,
  TrendingDown,
  Wallet,
} from "lucide-react";
import AlertList from "../components/alerts/AlertList";
import Card from "../components/layout/Card";
import KpiCard from "../components/kpi/KpiCard";
import ApprovalQueue from "../components/workqueue/ApprovalQueue";
import MenuPerformanceChart from "../components/charts/MenuPerformanceChart";
import SalesTrendChart from "../components/charts/SalesTrendChart";
import SupplierPriceChart from "../components/charts/SupplierPriceChart";
import { getJson } from "../api/client";
import {
  demoAlerts,
  demoKpis,
  demoMenuPerformance,
  demoPaymentsSummary,
  demoSalesTrend,
  demoSupplierPrices,
} from "../data/demoData";
import { formatCompactIDR } from "../lib/format";
import type {
  AlertItem,
  KpiSummary,
  MenuItemStat,
  PaymentsSummary,
  SalesPoint,
  SupplierPricePoint,
} from "../types";

function KpiLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="group relative block rounded-xl transition hover:-translate-y-0.5">
      {children}
      <span className="absolute right-3 top-3 text-[10px] font-medium uppercase tracking-wide text-slate-300 transition group-hover:text-emerald-600">
        View all →
      </span>
    </Link>
  );
}

export default function Dashboard() {
  const [kpis, setKpis] = useState<KpiSummary>(demoKpis);
  const [trend, setTrend] = useState<SalesPoint[]>(demoSalesTrend);
  const [menu, setMenu] = useState<MenuItemStat[]>(demoMenuPerformance);
  const [prices, setPrices] = useState<SupplierPricePoint[]>(demoSupplierPrices);
  const [alerts, setAlerts] = useState<AlertItem[]>(demoAlerts);
  const [payments, setPayments] = useState<PaymentsSummary>(demoPaymentsSummary);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getJson<KpiSummary>("/dashboard/summary", demoKpis).then(setKpis);
    getJson<SalesPoint[]>("/dashboard/sales-trend", demoSalesTrend).then(setTrend);
    getJson<MenuItemStat[]>("/dashboard/menu-performance", demoMenuPerformance).then(setMenu);
    getJson<SupplierPricePoint[]>("/dashboard/supplier-prices", demoSupplierPrices).then(setPrices);
    getJson<AlertItem[]>("/dashboard/alerts", demoAlerts).then(setAlerts);
    getJson<PaymentsSummary>("/dashboard/payments", demoPaymentsSummary).then(setPayments);
  }, [refreshKey]);

  const overdueCount = payments.payments.filter((p) => p.status === "overdue").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <KpiCard
          icon={<Wallet size={18} />}
          label="Daily Sales"
          value={formatCompactIDR(kpis.daily_sales_idr)}
          sub="Today · dine-in + delivery"
          tone="success"
        />
        <KpiCard
          icon={<TrendingDown size={18} />}
          label="COGS"
          value={formatCompactIDR(kpis.cogs_idr)}
          sub="Food cost today"
        />
        <KpiCard
          icon={<Percent size={18} />}
          label="Gross Margin"
          value={`${kpis.gross_margin_pct}%`}
          sub="Target 55%"
          tone={kpis.gross_margin_pct >= 55 ? "success" : "warning"}
        />
        <KpiLink to="/inventory">
          <KpiCard
            icon={<PackageX size={18} />}
            label="Low-Stock Alerts"
            value={String(kpis.low_stock_count)}
            sub="Items below reorder point"
            tone="danger"
          />
        </KpiLink>
        <KpiLink to="/suppliers">
          <KpiCard
            icon={<CalendarClock size={18} />}
            label="Due (7 days)"
            value={formatCompactIDR(payments.total_due_next_7_days)}
            sub={overdueCount > 0 ? `${overdueCount} payment${overdueCount > 1 ? "s" : ""} overdue` : "All on schedule"}
            tone={overdueCount > 0 ? "danger" : "default"}
          />
        </KpiLink>
        <KpiLink to="/reviews">
          <KpiCard
            icon={<MessageSquare size={18} />}
            label="Reviews"
            value={`${kpis.sentiment_score.toFixed(1)}★`}
            sub="Tap for the reply queue"
            tone="success"
          />
        </KpiLink>
      </div>

      <ApprovalQueue onChanged={() => setRefreshKey((k) => k + 1)} />

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="Sales vs COGS" subtitle="Last 14 days" className="xl:col-span-2">
          <SalesTrendChart data={trend} />
        </Card>
        <Card title="Alerts" subtitle="Actionable right now">
          <AlertList alerts={alerts} />
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Top Menu Items" subtitle="Units sold, last 7 days">
          <MenuPerformanceChart data={menu} />
        </Card>
        <Card title="Supplier Price Variance" subtitle="Current vs 30-day average per ingredient">
          <SupplierPriceChart data={prices} />
        </Card>
      </div>

      <Link
        to="/whatsapp"
        className="flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 transition hover:bg-emerald-100"
      >
        <span className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#25D366] text-white">
            <MessageCircle size={18} />
          </span>
          <span>
            <span className="block text-sm font-semibold text-slate-800">WhatsApp Copilot Demo</span>
            <span className="block text-xs text-slate-500">
              See the invoice → price audit → owner approval flow, end to end
            </span>
          </span>
        </span>
        <ArrowRight size={18} className="shrink-0 text-emerald-600" />
      </Link>
    </div>
  );
}
