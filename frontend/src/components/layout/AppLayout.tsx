import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  Smartphone,
  Star,
  Store,
  Truck,
  UtensilsCrossed,
} from "lucide-react";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/inventory", label: "Inventory", icon: Package, end: false },
  { to: "/suppliers", label: "Suppliers", icon: Truck, end: false },
  { to: "/menu", label: "Menu", icon: UtensilsCrossed, end: false },
  { to: "/reviews", label: "Reviews", icon: Star, end: false },
  { to: "/whatsapp", label: "WhatsApp Demo", icon: Smartphone, end: false },
] as const;

export default function AppLayout() {
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="flex min-h-screen bg-slate-100">
      {/* Sidebar (desktop) */}
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white md:flex">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#075E54] text-sm font-bold text-white">
            RP
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800">RestoPilot</p>
            <p className="text-[11px] text-slate-400">Operations Copilot</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-700"
                }`
              }
            >
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="m-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="flex items-center gap-2 text-sm font-semibold text-slate-700">
            <Store size={15} className="text-emerald-600" /> Warung Bu Sari
          </p>
          <p className="mt-0.5 text-[11px] text-slate-400">Demo tenant · Jakarta</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">RestoPilot Dashboard</p>
            <p className="text-sm font-semibold text-slate-800">{today}</p>
          </div>
          <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Mock data mode
          </span>
        </header>

        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2 md:hidden">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium ${
                  isActive ? "bg-emerald-50 text-emerald-700" : "text-slate-500"
                }`
              }
            >
              <Icon size={14} /> {label}
            </NavLink>
          ))}
        </nav>

        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
