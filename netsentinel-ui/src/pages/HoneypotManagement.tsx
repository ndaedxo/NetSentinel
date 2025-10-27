import { Server, Activity, Clock, Users, BarChart3 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Header from "@/components/Header";
import { useApi } from "@/hooks";
import { HoneypotServiceType } from "@/types";

export default function HoneypotManagement() {
  const { data: honeypots, refetch } = useApi<HoneypotServiceType[]>("/api/honeypots", 5000);

  const handleToggleService = async (id: number, currentStatus: number) => {
    try {
      await fetch("/api/honeypots/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, is_active: currentStatus === 1 ? 0 : 1 }),
      });
      refetch();
    } catch (error) {
      console.error("Failed to toggle service:", error);
    }
  };

  const getStatusColor = (isActive: number) => {
    return isActive === 1 ? "bg-green-500" : "bg-slate-500";
  };

  const totalConnections = honeypots?.reduce((sum, h) => sum + h.connection_count, 0) || 0;
  const activeServices = honeypots?.filter(h => h.is_active === 1).length || 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <Header />
      
      <main className="p-6 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gradient flex items-center space-x-3">
            <Server className="w-8 h-8 text-blue-400" />
            <span>Honeypot Management</span>
          </h1>
          <p className="text-slate-400 mt-2">Monitor and configure honeypot services</p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card-dark p-6 bg-gradient-to-br from-blue-500/20 to-blue-600/10 border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Total Services</p>
              <Server className="w-5 h-5 text-blue-400" />
            </div>
            <p className="text-3xl font-bold text-white">{honeypots?.length || 0}</p>
          </div>
          <div className="card-dark p-6 bg-gradient-to-br from-green-500/20 to-green-600/10 border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Active Services</p>
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <p className="text-3xl font-bold text-white">{activeServices}</p>
          </div>
          <div className="card-dark p-6 bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 border-cyan-500/30">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-slate-400">Total Connections</p>
              <Users className="w-5 h-5 text-cyan-400" />
            </div>
            <p className="text-3xl font-bold text-white">{totalConnections.toLocaleString()}</p>
          </div>
        </div>

        {/* Service Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {honeypots?.map((honeypot) => (
            <div
              key={honeypot.id}
              className={`card-dark p-6 transition-all duration-300 hover:scale-[1.02] ${
                honeypot.is_active === 1 ? "border-green-500/30" : "border-slate-700/50"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${honeypot.is_active === 1 ? "bg-green-500/20" : "bg-slate-700/50"}`}>
                    <Server className={`w-5 h-5 ${honeypot.is_active === 1 ? "text-green-400" : "text-slate-400"}`} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">{honeypot.name}</h3>
                    <p className="text-xs text-slate-500">{honeypot.protocol}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleToggleService(honeypot.id, honeypot.is_active)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    honeypot.is_active === 1 ? "bg-green-600" : "bg-slate-600"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      honeypot.is_active === 1 ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              {/* Status */}
              <div className="flex items-center space-x-2 mb-4">
                <div className={`w-2 h-2 rounded-full ${getStatusColor(honeypot.is_active)} ${honeypot.is_active === 1 ? "animate-pulse" : ""}`}></div>
                <span className={`text-sm font-medium ${honeypot.is_active === 1 ? "text-green-400" : "text-slate-400"}`}>
                  {honeypot.is_active === 1 ? "Active" : "Inactive"}
                </span>
              </div>

              {/* Metrics */}
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-slate-400">Port</span>
                  </div>
                  <span className="text-sm font-mono font-semibold text-white">{honeypot.port}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <Users className="w-4 h-4 text-cyan-400" />
                    <span className="text-sm text-slate-400">Connections</span>
                  </div>
                  <span className="text-sm font-semibold text-white">{honeypot.connection_count}</span>
                </div>
                {honeypot.last_connection_at && (
                  <div className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-yellow-400" />
                      <span className="text-sm text-slate-400">Last Activity</span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {formatDistanceToNow(new Date(honeypot.last_connection_at), { addSuffix: true })}
                    </span>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="mt-4 pt-4 border-t border-slate-700/50">
                <button className="w-full py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors text-sm font-medium text-slate-300">
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
