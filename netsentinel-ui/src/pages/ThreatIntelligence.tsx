import { useState } from "react";
import { Search, Filter, Shield, MapPin, Globe, Ban, CheckCircle, Download, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Header from "@/components/Header";
import { useApi } from "@/hooks";
import { ThreatType } from "@/types";
import { getThreatColorClasses } from "@/utils";
import ThreatDetailsModal from "@/components/ThreatDetailsModal";

export default function ThreatIntelligence() {
  const [selectedThreat, setSelectedThreat] = useState<ThreatType | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const { data: threats, refetch } = useApi<ThreatType[]>("/api/threats/all", 10000);


  const filteredThreats = threats?.filter((threat) => {
    const matchesSearch = threat.ip_address.includes(searchTerm) || 
                         threat.threat_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSeverity = severityFilter === "all" || threat.severity === severityFilter;
    return matchesSearch && matchesSeverity;
  }) || [];

  const handleBlockIP = async (ip: string) => {
    try {
      await fetch("/api/threats/block", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip_address: ip }),
      });
      refetch();
    } catch (error) {
      console.error("Failed to block IP:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <Header />
      
      <main className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gradient flex items-center space-x-3">
              <Shield className="w-8 h-8 text-blue-400" />
              <span>Threat Intelligence</span>
            </h1>
            <p className="text-slate-400 mt-2">Monitor and investigate detected threats</p>
          </div>
          <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors">
            <Download className="w-4 h-4" />
            <span className="text-sm font-medium">Export Report</span>
          </button>
        </div>

        {/* Filters */}
        <div className="card-dark p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search by IP address or threat type..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-slate-400" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-4 py-2 bg-slate-900/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>

        {/* Threat Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Threats</p>
                <p className="text-2xl font-bold text-white mt-1">{threats?.length || 0}</p>
              </div>
              <Shield className="w-8 h-8 text-blue-400" />
            </div>
          </div>
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Critical</p>
                <p className="text-2xl font-bold text-red-400 mt-1">
                  {threats?.filter(t => t.severity === "critical").length || 0}
                </p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
          </div>
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Blocked IPs</p>
                <p className="text-2xl font-bold text-green-400 mt-1">
                  {threats?.filter(t => t.is_blocked === 1).length || 0}
                </p>
              </div>
              <Ban className="w-8 h-8 text-green-400" />
            </div>
          </div>
          <div className="card-dark p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Countries</p>
                <p className="text-2xl font-bold text-cyan-400 mt-1">
                  {new Set(threats?.map(t => t.country_code).filter(Boolean)).size || 0}
                </p>
              </div>
              <Globe className="w-8 h-8 text-cyan-400" />
            </div>
          </div>
        </div>

        {/* Threats List */}
        <div className="card-dark">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="text-lg font-semibold text-white">All Threats</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="text-left text-xs font-medium text-slate-400 p-4">IP Address</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Country</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Threat Type</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Severity</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Score</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Status</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Time</th>
                  <th className="text-left text-xs font-medium text-slate-400 p-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {filteredThreats.map((threat) => (
                  <tr 
                    key={threat.id} 
                    className="hover:bg-slate-800/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedThreat(threat)}
                  >
                    <td className="p-4">
                      <div className="flex items-center space-x-2">
                        <MapPin className="w-3 h-3 text-slate-500" />
                        <span className="text-sm font-mono text-slate-300">{threat.ip_address}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-slate-400">{threat.country_code || "N/A"}</span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-slate-300">{threat.threat_type}</span>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getThreatColorClasses(threat.severity)}`}>
                        {threat.severity}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm font-semibold text-white">{threat.threat_score}</span>
                    </td>
                    <td className="p-4">
                      {threat.is_blocked === 1 ? (
                        <span className="inline-flex items-center space-x-1 text-red-400 text-sm">
                          <Ban className="w-3 h-3" />
                          <span>Blocked</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 text-green-400 text-sm">
                          <CheckCircle className="w-3 h-3" />
                          <span>Active</span>
                        </span>
                      )}
                    </td>
                    <td className="p-4">
                      <span className="text-xs text-slate-500">
                        {formatDistanceToNow(new Date(threat.created_at), { addSuffix: true })}
                      </span>
                    </td>
                    <td className="p-4">
                      {threat.is_blocked === 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleBlockIP(threat.ip_address);
                          }}
                          className="px-3 py-1 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-300 text-xs rounded transition-colors"
                        >
                          Block
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {selectedThreat && (
        <ThreatDetailsModal
          threat={selectedThreat}
          onClose={() => setSelectedThreat(null)}
          onBlock={handleBlockIP}
        />
      )}
    </div>
  );
}
