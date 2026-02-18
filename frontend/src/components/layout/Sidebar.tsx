import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Building2,
  TrendingUp,
  AlertTriangle,
  FileSpreadsheet,
  Settings,
  ShieldCheck,
  Menu,
  X,
} from "lucide-react";
import clsx from "clsx";
import ThemeToggle from "./ThemeToggle";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/sites", icon: Building2, label: "Sites" },
  { to: "/trends", icon: TrendingUp, label: "Trends" },
  { to: "/issues", icon: AlertTriangle, label: "Issues" },
  { to: "/reports", icon: FileSpreadsheet, label: "Reports" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 rounded-lg bg-gray-900 p-2 text-gray-300
                   lg:hidden shadow-lg"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-800",
          "bg-gray-900 transition-transform duration-200 ease-in-out",
          "lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Close button for mobile */}
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute right-3 top-4 rounded-lg p-1 text-gray-400
                     hover:text-gray-200 lg:hidden"
          aria-label="Close navigation"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Logo area */}
        <div className="flex items-center gap-3 border-b border-gray-800 px-6 py-5">
          <ShieldCheck className="h-8 w-8 text-emerald-500" />
          <div>
            <h1 className="text-lg font-bold text-white">Veeam Audit</h1>
            <p className="text-xs text-gray-500">Backup Dashboard</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium",
                  "transition-colors duration-150",
                  isActive
                    ? "bg-emerald-600/10 text-emerald-400"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200",
                )
              }
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Bottom section */}
        <div className="border-t border-gray-800 px-3 py-4">
          <ThemeToggle />
        </div>
      </aside>
    </>
  );
}
