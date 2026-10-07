import { useEffect, useState } from "react";
import Card from "../components/layout/Card";
import { getJson } from "../api/client";
import { demoPaymentsSummary, demoSuppliers } from "../data/demoData";
import { formatIDR, formatPct } from "../lib/format";
import type { PaymentsSummary, SupplierRow } from "../types";

const STATUS_STYLES: Record<SupplierRow["status"], string> = {
  verified: "bg-emerald-50 text-emerald-600",
  watch: "bg-amber-50 text-amber-600",
  new: "bg-slate-100 text-slate-500",
};

const PAYMENT_STYLES: Record<PaymentRow["status"], string> = {
  paid: "bg-emerald-50 text-emerald-600",
  pending: "bg-amber-50 text-amber-600",
  overdue: "bg-red-50 text-red-600",
};

type PaymentRow = PaymentsSummary["payments"][number];

export default function Suppliers() {
  const [rows, setRows] = useState<SupplierRow[]>(demoSuppliers);
  const [payments, setPayments] = useState<PaymentsSummary>(demoPaymentsSummary);

  useEffect(() => {
    getJson<SupplierRow[]>("/dashboard/suppliers", demoSuppliers).then(setRows);
    getJson<PaymentsSummary>("/dashboard/payments", demoPaymentsSummary).then(setPayments);
  }, []);

  const overdueCount = payments.payments.filter((p) => p.status === "overdue").length;

  return (
    <div className="space-y-6">
      <Card title="Suppliers" subtitle="30-day average price movement across their ingredients">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-3 pr-4 font-medium">Supplier</th>
                <th className="pb-3 pr-4 font-medium">Ingredients</th>
                <th className="pb-3 pr-4 font-medium">Avg price Δ (30d)</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.name} className="border-b border-slate-50 last:border-0">
                  <td className="py-3 pr-4 font-medium text-slate-700">{s.name}</td>
                  <td className="py-3 pr-4 text-slate-600">{s.ingredients}</td>
                  <td
                    className={`py-3 pr-4 font-medium ${
                      s.avg_price_delta_pct > 0 ? "text-red-500" : "text-emerald-600"
                    }`}
                  >
                    {formatPct(s.avg_price_delta_pct)}
                  </td>
                  <td className="py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${STATUS_STYLES[s.status]}`}
                    >
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Pending Supplier Payments"
        subtitle="Cash-flow view of what's owed and when"
      >
        <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg bg-slate-50 px-4 py-3">
          <span className="text-sm text-slate-500">Due in the next 7 days</span>
          <span className="text-base font-bold text-slate-800">
            {formatIDR(payments.total_due_next_7_days)}
          </span>
          {overdueCount > 0 && (
            <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-500">
              {overdueCount} overdue
            </span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="pb-3 pr-4 font-medium">Supplier</th>
                <th className="pb-3 pr-4 font-medium">Description</th>
                <th className="pb-3 pr-4 font-medium">Amount</th>
                <th className="pb-3 pr-4 font-medium">Due date</th>
                <th className="pb-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {payments.payments.map((p) => (
                <tr key={p.description} className="border-b border-slate-50 last:border-0">
                  <td className="py-3 pr-4 font-medium text-slate-700">{p.supplier}</td>
                  <td className="py-3 pr-4 text-slate-500">{p.description}</td>
                  <td className="py-3 pr-4 text-slate-600">{formatIDR(p.amount)}</td>
                  <td className="py-3 pr-4 text-slate-500">{p.due_date}</td>
                  <td className="py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${PAYMENT_STYLES[p.status]}`}
                    >
                      {p.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
