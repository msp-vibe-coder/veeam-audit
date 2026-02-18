import { Routes, Route } from "react-router-dom";
import Sidebar from "@/components/layout/Sidebar";
import Dashboard from "@/pages/Dashboard";
import Sites from "@/pages/Sites";
import SiteDetail from "@/pages/SiteDetail";
import Trends from "@/pages/Trends";
import Issues from "@/pages/Issues";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />

      {/* Main content area with sidebar offset */}
      <main className="flex-1 lg:ml-64">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/sites" element={<Sites />} />
            <Route path="/sites/:code" element={<SiteDetail />} />
            <Route path="/trends" element={<Trends />} />
            <Route path="/issues" element={<Issues />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
