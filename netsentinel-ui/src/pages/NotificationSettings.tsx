import { useEffect, useState } from 'react';
import { PageLayout } from '@/components';
import { getNotificationPreferences, updateNotificationPreferences, getChannelConfig, updateChannelConfig } from '@/services';
import type { NotificationPreferences, ChannelConfig } from '@/types';

export default function NotificationSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [prefs, setPrefs] = useState<NotificationPreferences>({ emailEnabled: false, smsEnabled: false, slackEnabled: false, severities: [], quietHours: undefined });
  const [channels, setChannels] = useState<ChannelConfig>({ email: { from: '' }, sms: { provider: 'twilio', fromNumber: '' }, slack: { webhookUrl: '', channel: '' } });

  useEffect(() => {
    let mounted = true;
    Promise.all([getNotificationPreferences(), getChannelConfig()]).then(([p, c]) => {
      if (!mounted) return;
      setPrefs(p);
      setChannels({
        email: { from: c.email?.from || '' },
        sms: { provider: (c.sms?.provider ?? 'twilio'), fromNumber: c.sms?.fromNumber || '' },
        slack: { webhookUrl: c.slack?.webhookUrl || '', channel: c.slack?.channel || '' },
      });
      setLoading(false);
    });
    return () => { mounted = false; };
  }, []);

  const toggleSeverity = (sev: string) => {
    setPrefs(prev => ({ ...prev, severities: prev.severities.includes(sev) ? prev.severities.filter(s => s !== sev) : [...prev.severities, sev] }));
  };

  const onSave = async () => {
    setSaving(true);
    await updateNotificationPreferences(prefs);
    await updateChannelConfig(channels);
    setSaving(false);
  };

  return (
    <PageLayout title="Notification Settings" subtitle="Configure channels and preferences">
      {loading ? (
        <div className="text-slate-400">Loading...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4">
            <h2 className="text-slate-200 text-sm font-semibold mb-3">Channels</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-slate-300 inline-flex items-center gap-2">
                  <span>Email</span>
                  <input data-testid="email-toggle" aria-label="Email" type="checkbox" checked={prefs.emailEnabled} onChange={(e) => setPrefs({ ...prefs, emailEnabled: e.target.checked })} />
                </label>
              </div>
              <div className="space-y-2">
                <label className="text-slate-400 text-xs">From address</label>
                <input className="w-full rounded bg-slate-800 border border-slate-700 px-2 py-1 text-slate-200" value={channels.email.from} onChange={(e) => setChannels({ ...channels, email: { ...channels.email, from: e.target.value } })} />
              </div>
              <div className="flex items-center justify-between pt-2">
                <label className="text-slate-300 inline-flex items-center gap-2">
                  <span>Slack</span>
                  <input data-testid="slack-toggle" aria-label="Slack" type="checkbox" checked={prefs.slackEnabled} onChange={(e) => setPrefs({ ...prefs, slackEnabled: e.target.checked })} />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input placeholder="Webhook URL" className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-slate-200" value={channels.slack.webhookUrl} onChange={(e) => setChannels({ ...channels, slack: { ...channels.slack, webhookUrl: e.target.value } })} />
                <input placeholder="Channel" className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-slate-200" value={channels.slack.channel} onChange={(e) => setChannels({ ...channels, slack: { ...channels.slack, channel: e.target.value } })} />
              </div>
              <div className="flex items-center justify-between pt-2">
                <label className="text-slate-300 inline-flex items-center gap-2">
                  <span>SMS</span>
                  <input data-testid="sms-toggle" aria-label="SMS" type="checkbox" checked={prefs.smsEnabled} onChange={(e) => setPrefs({ ...prefs, smsEnabled: e.target.checked })} />
                </label>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input placeholder="From Number" className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-slate-200" value={channels.sms.fromNumber} onChange={(e) => setChannels({ ...channels, sms: { ...channels.sms, fromNumber: e.target.value } })} />
              </div>
            </div>
          </section>

          <section className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4">
            <h2 className="text-slate-200 text-sm font-semibold mb-3">Preferences</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-slate-300 mb-2">Severities</label>
                <div className="flex gap-3 text-sm">
                  {['low','medium','high','critical'].map(s => (
                    <label key={s} className="inline-flex items-center gap-1 text-slate-300">
                      <input type="checkbox" checked={prefs.severities.includes(s)} onChange={() => toggleSeverity(s)} /> {s}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-slate-300 mb-2">Quiet Hours</label>
                <div className="grid grid-cols-2 gap-2">
                  <input type="time" className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-slate-200" value={prefs.quietHours?.start || ''} onChange={(e) => setPrefs({ ...prefs, quietHours: { ...(prefs.quietHours || { end: '' }), start: e.target.value } })} />
                  <input type="time" className="rounded bg-slate-800 border border-slate-700 px-2 py-1 text-slate-200" value={prefs.quietHours?.end || ''} onChange={(e) => setPrefs({ ...prefs, quietHours: { ...(prefs.quietHours || { start: '' }), end: e.target.value } })} />
                </div>
              </div>
              <button disabled={saving} onClick={onSave} className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-50">{saving ? 'Saving...' : 'Save Settings'}</button>
            </div>
          </section>
        </div>
      )}
    </PageLayout>
  );
}


