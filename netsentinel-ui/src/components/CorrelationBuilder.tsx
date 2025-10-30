import type { CorrelationDSL } from '@/types';
import { useState } from 'react';

interface RuleCondition {
  field: string;
  op: string;
  value: string;
}

interface Group {
  id: string;
  type: 'AND' | 'OR';
  conditions: RuleCondition[];
}


const fields = ['ip', 'country', 'threat_type', 'severity', 'port', 'service'];
const ops = ['equals', 'not_equals', 'contains', 'starts_with', 'gt', 'lt'];

export default function CorrelationBuilder({ onChange }:{ onChange?: (dsl: CorrelationDSL) => void }) {
  const [groups, setGroups] = useState<Group[]>([
    { id: 'g1', type: 'AND', conditions: [{ field: 'severity', op: 'equals', value: 'critical' }] },
  ]);

  const update = (next: Group[]) => {
    setGroups(next);
    onChange?.(serialize(next));
  };

  const addGroup = () => update([...groups, { id: `g${groups.length+1}`, type: 'AND', conditions: [] }]);
  const addCondition = (gid: string) => update(groups.map(g => g.id === gid ? { ...g, conditions: [...g.conditions, { field: 'ip', op: 'equals', value: '' }] } : g));
  const removeCondition = (gid: string, idx: number) => update(groups.map(g => g.id === gid ? { ...g, conditions: g.conditions.filter((_, i) => i !== idx) } : g));

  const serialize = (gs: Group[]): CorrelationDSL => ({
    type: 'correlation_rule',
    groups: gs.map(g => ({ type: g.type, conditions: g.conditions })),
  });

  return (
    <div className="space-y-4">
      {groups.map((g) => (
        <div key={g.id} className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-3">
            <label className="text-slate-300 text-sm">Group Logic</label>
            <select className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200" value={g.type} onChange={(e) => update(groups.map(x => x.id === g.id ? { ...x, type: e.target.value as Group['type'] } : x))}>
              <option value="AND">AND</option>
              <option value="OR">OR</option>
            </select>
            <button className="ml-auto px-2 py-1 text-xs rounded bg-slate-800 border border-slate-700 hover:bg-slate-700" onClick={() => addCondition(g.id)}>Add Condition</button>
          </div>
          <div className="space-y-2">
            {g.conditions.length === 0 && (
              <div className="text-slate-500 text-sm">No conditions. Add one to start.</div>
            )}
            {g.conditions.map((c, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                <select className="col-span-3 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200" value={c.field} onChange={(e) => update(groups.map(x => x.id === g.id ? { ...x, conditions: x.conditions.map((y, i) => i === idx ? { ...y, field: e.target.value } : y) } : x))}>
                  {fields.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
                <select className="col-span-3 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200" value={c.op} onChange={(e) => update(groups.map(x => x.id === g.id ? { ...x, conditions: x.conditions.map((y, i) => i === idx ? { ...y, op: e.target.value } : y) } : x))}>
                  {ops.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
                <input className="col-span-5 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200" placeholder="value" value={c.value} onChange={(e) => update(groups.map(x => x.id === g.id ? { ...x, conditions: x.conditions.map((y, i) => i === idx ? { ...y, value: e.target.value } : y) } : x))} />
                <button className="col-span-1 px-2 py-1 text-xs rounded bg-slate-800 border border-slate-700 hover:bg-slate-700" onClick={() => removeCondition(g.id, idx)}>X</button>
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="flex gap-2">
        <button className="px-3 py-2 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700" onClick={addGroup}>Add Group</button>
      </div>
    </div>
  );
}


