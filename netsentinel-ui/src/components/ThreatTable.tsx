import { ThreatType } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { Shield, MapPin } from "lucide-react";
import { getThreatColorClasses } from "@/utils";

interface ThreatTableProps {
  threats: ThreatType[];
}

export default function ThreatTable({ threats }: ThreatTableProps) {

  return (
    <div className="card-dark p-6">
      <div className="flex items-center space-x-2 mb-4">
        <Shield className="w-5 h-5 text-blue-400" />
        <h2 className="text-lg font-semibold text-white">Recent Threats</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700/50">
              <th className="text-left text-xs font-medium text-slate-400 pb-3 px-2">IP Address</th>
              <th className="text-left text-xs font-medium text-slate-400 pb-3 px-2">Threat Type</th>
              <th className="text-left text-xs font-medium text-slate-400 pb-3 px-2">Severity</th>
              <th className="text-left text-xs font-medium text-slate-400 pb-3 px-2">Score</th>
              <th className="text-left text-xs font-medium text-slate-400 pb-3 px-2">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/30">
            {threats.map((threat) => (
              <tr key={threat.id} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-2">
                  <div className="flex items-center space-x-2">
                    {threat.country_code && <MapPin className="w-3 h-3 text-slate-500" />}
                    <span className="text-sm font-mono text-slate-300">{threat.ip_address}</span>
                  </div>
                </td>
                <td className="py-3 px-2">
                  <span className="text-sm text-slate-400">{threat.threat_type}</span>
                </td>
                <td className="py-3 px-2">
                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getThreatColorClasses(threat.severity)}`}>
                    {threat.severity}
                  </span>
                </td>
                <td className="py-3 px-2">
                  <span className="text-sm font-semibold text-white">{threat.threat_score}</span>
                </td>
                <td className="py-3 px-2">
                  <span className="text-xs text-slate-500">
                    {formatDistanceToNow(new Date(threat.created_at), { addSuffix: true })}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
