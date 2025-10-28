import Header from "@/components/Header";
import CustomDashboard from "@/components/CustomDashboard";
import { DashboardProvider } from "@/hooks/useDashboard";

export default function Dashboard() {
  return (
    <DashboardProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <Header />
        <main className="max-w-7xl mx-auto px-6 py-8">
          <CustomDashboard />
        </main>
      </div>
    </DashboardProvider>
  );
}
