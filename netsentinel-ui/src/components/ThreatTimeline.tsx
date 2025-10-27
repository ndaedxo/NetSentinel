import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface TimelineData {
  hour: string;
  count: number;
  severity: string;
}

interface ThreatTimelineProps {
  data: TimelineData[];
}

export default function ThreatTimeline({ data }: ThreatTimelineProps) {
  // Aggregate data by hour
  const aggregatedData = data.reduce((acc: any[], item) => {
    const existing = acc.find(d => d.hour === item.hour);
    if (existing) {
      existing[item.severity] = (existing[item.severity] || 0) + item.count;
      existing.total += item.count;
    } else {
      acc.push({
        hour: item.hour,
        [item.severity]: item.count,
        total: item.count,
      });
    }
    return acc;
  }, []);

  return (
    <div className="card-dark p-6">
      <h2 className="text-lg font-semibold text-white mb-4">Threat Timeline (Last 24 Hours)</h2>
      
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={aggregatedData}>
          <defs>
            <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#eab308" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
          <XAxis 
            dataKey="hour" 
            stroke="#64748b" 
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#64748b"
            style={{ fontSize: '12px' }}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#1e293b', 
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0'
            }}
          />
          <Area 
            type="monotone" 
            dataKey="critical" 
            stackId="1"
            stroke="#ef4444" 
            fill="url(#colorCritical)"
            strokeWidth={2}
          />
          <Area 
            type="monotone" 
            dataKey="high" 
            stackId="1"
            stroke="#f97316" 
            fill="url(#colorHigh)"
            strokeWidth={2}
          />
          <Area 
            type="monotone" 
            dataKey="medium" 
            stackId="1"
            stroke="#eab308" 
            fill="url(#colorMedium)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
