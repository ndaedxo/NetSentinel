import { Activity, Shield, Ban, TrendingUp } from "lucide-react";
import Header from "@/components/Header";
import StatCard from "@/components/StatCard";
import ThreatTable from "@/components/ThreatTable";
import ThreatTimeline from "@/components/ThreatTimeline";
import SystemHealth from "@/components/SystemHealth";
import AlertFeed from "@/components/AlertFeed";
import { useApi } from "@/hooks";
import { DashboardMetrics, ThreatType, AlertType, SystemHealthService } from "@/types";

export default function Dashboard() {
  const { data: metrics } = useApi<DashboardMetrics>("/api/metrics", 5000);
  const { data: threats } = useApi<ThreatType[]>("/api/threats/recent", 10000);
  const { data: timeline } = useApi<any[]>("/api/threats/timeline", 30000);
  const { data: health } = useApi<{ services: SystemHealthService[] }>("/api/health", 15000);
  const { data: alerts } = useApi<AlertType[]>("/api/alerts/active", 10000);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <Header />
      
      <main className="p-6 space-y-6">
        {/* Status Banner */}
        <div className="card-dark p-4 bg-gradient-to-r from-green-500/10 to-blue-500/10 border-green-500/30">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-green-300">All Systems Operational</span>
            </div>
            <div className="flex items-center space-x-6 text-sm text-slate-400">
              <span>Uptime: 99.9%</span>
              <span>•</span>
              <span>Last Update: Just now</span>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="Total Events"
            value={metrics?.totalEvents || 0}
            icon={Activity}
            trend={{ value: "+12% today", isPositive: true }}
            color="blue"
          />
          <StatCard
            title="Active Threats"
            value={metrics?.activeThreats || 0}
            icon={Shield}
            trend={{ value: "+5 new", isPositive: false }}
            color="red"
          />
          <StatCard
            title="Blocked IPs"
            value={metrics?.blockedIps || 0}
            icon={Ban}
            trend={{ value: "+3 today", isPositive: true }}
            color="yellow"
          />
          <StatCard
            title="Detection Rate"
            value="98.5%"
            icon={TrendingUp}
            trend={{ value: "+0.2%", isPositive: true }}
            color="green"
          />
        </div>

        {/* Threat Timeline */}
        {timeline && timeline.length > 0 && (
          <ThreatTimeline data={timeline} />
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Threats - Takes 2 columns */}
          <div className="lg:col-span-2">
            {threats && threats.length > 0 ? (
              <ThreatTable threats={threats} />
            ) : (
              <div className="card-dark p-6">
                <p className="text-center text-slate-500">No recent threats detected</p>
              </div>
            )}
          </div>

          {/* System Health - Takes 1 column */}
          <div>
            {health && health.services ? (
              <SystemHealth services={health.services} />
            ) : (
              <div className="card-dark p-6">
                <p className="text-center text-slate-500">Loading system health...</p>
              </div>
            )}
          </div>
        </div>

        {/* Active Alerts Feed */}
        {alerts && alerts.length > 0 && (
          <AlertFeed alerts={alerts} />
        )}

        {/* Footer Info */}
        <div className="text-center text-xs text-slate-600 py-4">
          <p>Netsentinel Enterprise Security Platform v1.0 | Secure Operations Center</p>
        </div>
      </main>
    </div>
  );
}
