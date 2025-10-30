import { useState } from 'react';
import { PageLayout } from '@/components';
import CorrelationBuilder from '@/components/CorrelationBuilder';
import type { CorrelationDSL } from '@/types';

export default function Correlation() {
  const [dsl, setDsl] = useState<CorrelationDSL | null>(null);

  return (
    <PageLayout title="Correlation Builder" subtitle="Create advanced correlation and pattern rules">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <CorrelationBuilder onChange={setDsl} />
        </div>
        <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4">
          <h2 className="text-slate-200 text-sm font-semibold mb-3">Preview (DSL)</h2>
          <pre className="text-xs text-slate-300 bg-slate-800 border border-slate-700 rounded p-3 overflow-auto max-h-[480px]">{JSON.stringify(dsl, null, 2)}</pre>
        </div>
      </div>
    </PageLayout>
  );
}


