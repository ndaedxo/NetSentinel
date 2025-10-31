import { X, MapPin, Clock, Shield, Ban, Download, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { getThreatModalColorClasses } from "@/utils";
import { ThreatType } from "@/types";

interface ThreatDetailsModalProps {
  threat: ThreatType;
  onClose: () => void;
  onBlock: (ip: string) => void;
}

export default function ThreatDetailsModal({ threat, onClose, onBlock }: ThreatDetailsModalProps) {

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-slate-900/95 backdrop-blur-sm border-b border-slate-700/50 p-6 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Shield className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-bold text-white">Threat Details</h2>
          </div>
          <button
            onClick={onClose}
            className="p-3 hover:bg-slate-800 rounded-lg transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Close threat details"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Severity Badge */}
          <div className="flex items-center justify-between">
            <span className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-semibold border ${getThreatModalColorClasses(threat.severity)}`}>
              <AlertTriangle className="w-4 h-4 mr-2" />
              {threat.severity.toUpperCase()} SEVERITY
            </span>
            <div className="flex items-center space-x-2">
              {threat.is_blocked === 0 ? (
                <button
                  onClick={() => {
                    onBlock(threat.ip_address);
                    onClose();
                  }}
                  className="flex items-center space-x-2 px-4 py-3 bg-red-600 hover:bg-red-500 rounded-lg transition-colors min-h-[44px]"
                >
                  <Ban className="w-4 h-4" />
                  <span className="text-sm font-medium">Block IP</span>
                </button>
              ) : (
                <span className="flex items-center space-x-2 px-4 py-2 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
                  <Ban className="w-4 h-4" />
                  <span>IP Blocked</span>
                </span>
              )}
              <button className="flex items-center space-x-2 px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors min-h-[44px]">
                <Download className="w-4 h-4" />
                <span className="text-sm font-medium">Export</span>
              </button>
            </div>
          </div>

          {/* Basic Info Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="card-dark p-4">
              <div className="flex items-center space-x-2 mb-2">
                <MapPin className="w-4 h-4 text-blue-400" />
                <p className="text-sm text-slate-400">IP Address</p>
              </div>
              <p className="text-lg font-mono font-semibold text-white">{threat.ip_address}</p>
            </div>
            <div className="card-dark p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Clock className="w-4 h-4 text-blue-400" />
                <p className="text-sm text-slate-400">First Seen</p>
              </div>
              <p className="text-lg font-semibold text-white">
                {formatDistanceToNow(new Date(threat.created_at), { addSuffix: true })}
              </p>
            </div>
            <div className="card-dark p-4">
              <p className="text-sm text-slate-400 mb-2">Country</p>
              <p className="text-lg font-semibold text-white">{threat.country_code || "Unknown"}</p>
            </div>
            <div className="card-dark p-4">
              <p className="text-sm text-slate-400 mb-2">Threat Score</p>
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-slate-700/50 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      threat.threat_score >= 80 ? "bg-red-500" :
                      threat.threat_score >= 60 ? "bg-orange-500" :
                      threat.threat_score >= 40 ? "bg-yellow-500" : "bg-blue-500"
                    }`}
                    style={{ width: `${threat.threat_score}%` }}
                  ></div>
                </div>
                <span className="text-lg font-semibold text-white">{threat.threat_score}</span>
              </div>
            </div>
          </div>

          {/* Threat Type */}
          <div className="card-dark p-4">
            <p className="text-sm text-slate-400 mb-2">Threat Type</p>
            <p className="text-lg font-semibold text-white">{threat.threat_type}</p>
          </div>

          {/* Description */}
          {threat.description && (
            <div className="card-dark p-4">
              <p className="text-sm text-slate-400 mb-2">Description</p>
              <p className="text-sm text-slate-300 leading-relaxed">{threat.description}</p>
            </div>
          )}

          {/* Honeypot Service */}
          {threat.honeypot_service && (
            <div className="card-dark p-4">
              <p className="text-sm text-slate-400 mb-2">Honeypot Service</p>
              <p className="text-sm text-slate-300">{threat.honeypot_service}</p>
            </div>
          )}

          {/* Timeline */}
          <div className="card-dark p-4">
            <p className="text-sm text-slate-400 mb-4">Event Timeline</p>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-blue-400 rounded-full mt-2"></div>
                <div className="flex-1">
                  <p className="text-sm text-white font-medium">Threat Detected</p>
                  <p className="text-xs text-slate-500">{new Date(threat.created_at).toLocaleString()}</p>
                </div>
              </div>
              {threat.is_blocked === 1 && (
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-red-400 rounded-full mt-2"></div>
                  <div className="flex-1">
                    <p className="text-sm text-white font-medium">IP Blocked</p>
                    <p className="text-xs text-slate-500">{new Date(threat.updated_at).toLocaleString()}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
