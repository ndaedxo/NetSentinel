import { ThreatType } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { Shield, MapPin, Filter } from "lucide-react";
import { getThreatColorClasses } from "@/utils";
import FilterBuilder from "./FilterBuilder";
import ExportButton from "./ExportButton";
import { useFilters } from "@/hooks/useFilters";
import { THREAT_FILTER_FIELDS, createFilterPreset, type FilterField } from "@/types/filter";
import { THREAT_EXPORT_COLUMNS } from "@/utils/export";
import { useState } from "react";

interface ThreatTableProps {
  threats: ThreatType[];
  showFilters?: boolean;
  compact?: boolean;
}

export default function ThreatTable({ threats, showFilters = true, compact = false }: ThreatTableProps) {
  const [showFilterBuilder, setShowFilterBuilder] = useState(false);

  // Default presets for threats
  const defaultPresets = [
    createFilterPreset('High Severity Threats', [
      { field: 'severity', operator: 'equals', value: 'high' }
    ], 'AND', 'Security'),
    createFilterPreset('Recent Threats', [
      { field: 'timestamp', operator: 'greater_than', value: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString() }
    ], 'AND', 'Time'),
    createFilterPreset('Critical & High', [
      { field: 'severity', operator: 'in', value: ['critical', 'high'] }
    ], 'AND', 'Security')
  ];

  const {
    filterState,
    filteredData,
    updateFilterState,
    applyFilters,
    clearFilters
  } = useFilters(threats, THREAT_FILTER_FIELDS, defaultPresets);

  return (
    <div className="card-dark p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Shield className="w-5 h-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-white">Recent Threats</h2>
          {filteredData.length !== threats.length && (
            <span className="px-2 py-1 bg-blue-500/20 text-blue-300 text-xs rounded-full">
              {filteredData.length} of {threats.length}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <ExportButton
            data={filteredData}
            columns={THREAT_EXPORT_COLUMNS}
            filename="threats"
            title="Threat Intelligence Report"
          />

          {showFilters && (
            <button
              onClick={() => setShowFilterBuilder(!showFilterBuilder)}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                showFilterBuilder || filterState.rootGroup.conditions.length > 0
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <Filter className="w-4 h-4" />
              <span>Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Builder */}
      {showFilters && showFilterBuilder && (
        <div className="mb-6">
          <FilterBuilder
            filterState={filterState}
            onFilterChange={updateFilterState}
            onApplyFilters={applyFilters}
            onClearFilters={clearFilters}
          />
        </div>
      )}

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
            {filteredData.map((threat) => (
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
