import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import { adminAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const DEFAULTS = { genuine: 0.75, suspicious: 0.45 };

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

export default function CommandCenter() {
  const { user } = useAuth();

  const [thresholds, setThresholds] = useState(DEFAULTS);
  const [draft, setDraft] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // 'saved' | 'error'
  const [adminStats, setAdminStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    adminAPI.getThresholds()
      .then(r => { setThresholds(r.data); setDraft(r.data); })
      .catch(() => {});

    adminAPI.getStats()
      .then(r => setAdminStats(r.data))
      .catch(() => {})
      .finally(() => setLoadingStats(false));
  }, []);

  const isDirty = draft.genuine !== thresholds.genuine || draft.suspicious !== thresholds.suspicious;

  const handleSave = async () => {
    if (draft.suspicious >= draft.genuine) return;
    setSaving(true);
    setSaveStatus(null);
    try {
      const r = await adminAPI.updateThresholds(draft);
      setThresholds(r.data);
      setDraft(r.data);
      setSaveStatus('saved');
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  const handleReset = () => { setDraft(thresholds); setSaveStatus(null); };

  const fakeZoneWidth = Math.round(draft.suspicious * 100);
  const suspZoneWidth = Math.round((draft.genuine - draft.suspicious) * 100);
  const genuineZoneWidth = Math.round((1 - draft.genuine) * 100);

  return (
    <div className="font-body-md text-on-surface antialiased bg-background min-h-screen">
      <div className="fixed top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary-container/20 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-[-5%] left-[-5%] w-[400px] h-[400px] bg-secondary-container/20 rounded-full blur-[100px] pointer-events-none -z-10" />

      <Sidebar user={user} />

      <header className="fixed top-0 right-0 left-72 h-20 z-40 bg-white/40 backdrop-blur-xl border-b border-white/20 shadow-sm flex items-center justify-between px-8">
        <div className="flex items-center gap-6 flex-1">
          <h2 className="hidden md:block font-headline-md text-headline-md text-primary font-bold">Command Center</h2>
          <div className="relative w-80">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40">search</span>
            <input className="w-full bg-white/20 border border-white/40 focus:ring-primary/20 focus:border-primary/40 rounded-full pl-11 pr-4 py-2 text-body-md outline-none" placeholder="Search records..." />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-white/30 rounded-full transition-colors relative">
            <span className="material-symbols-outlined text-on-surface-variant">notifications</span>
            <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border-2 border-white" />
          </button>
        </div>
      </header>

      <main className="ml-72 pt-28 px-8 pb-16 space-y-6">

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total Verified', value: loadingStats ? '—' : adminStats?.total_verifications ?? 0, icon: 'fact_check', color: 'text-primary' },
            { label: 'Genuine', value: loadingStats ? '—' : adminStats?.by_status?.GENUINE ?? 0, icon: 'verified', color: 'text-emerald-600' },
            { label: 'Suspicious', value: loadingStats ? '—' : adminStats?.by_status?.SUSPICIOUS ?? 0, icon: 'warning', color: 'text-amber-500' },
            { label: 'Fake', value: loadingStats ? '—' : adminStats?.by_status?.FAKE ?? 0, icon: 'dangerous', color: 'text-red-500' },
          ].map(s => (
            <div key={s.label} className="glass-card rounded-[28px] p-6 inner-glow">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[10px] uppercase tracking-[0.3em] text-on-surface-variant/60 font-bold">{s.label}</p>
                <span className={`material-symbols-outlined ${s.color}`} style={{ fontVariationSettings: "'FILL' 1" }}>{s.icon}</span>
              </div>
              <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* ── Confidence Threshold Tuning Panel ── */}
        <div className="glass-card rounded-[32px] p-8 inner-glow">
          <div className="flex items-start justify-between mb-8">
            <div>
              <p className="text-[11px] uppercase tracking-[0.35em] text-primary font-bold mb-1">ML Model Configuration</p>
              <h3 className="text-xl font-bold text-on-surface">Confidence Threshold Tuning</h3>
              <p className="text-sm text-on-surface-variant/70 mt-1">
                Adjust where the model draws the line between Genuine, Suspicious, and Fake verdicts.
                Changes apply immediately to all future verifications.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <AnimatePresence>
                {saveStatus === 'saved' && (
                  <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-emerald-600 bg-emerald-50 border border-emerald-200 px-4 py-2 rounded-full text-sm font-semibold">
                    <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                    Saved
                  </motion.div>
                )}
                {saveStatus === 'error' && (
                  <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 px-4 py-2 rounded-full text-sm font-semibold">
                    <span className="material-symbols-outlined text-base">error</span>
                    Failed to save
                  </motion.div>
                )}
              </AnimatePresence>
              {isDirty && (
                <button onClick={handleReset}
                  className="px-4 py-2 rounded-full border border-outline-variant/50 text-sm font-semibold text-on-surface-variant hover:bg-white/40 transition-colors">
                  Reset
                </button>
              )}
              <button onClick={handleSave} disabled={saving || !isDirty || draft.suspicious >= draft.genuine}
                className={`px-6 py-2 rounded-full text-sm font-bold transition-all shadow-sm ${
                  isDirty && draft.suspicious < draft.genuine
                    ? 'bg-primary text-white shadow-primary/20 hover:shadow-lg hover:shadow-primary/30'
                    : 'bg-outline-variant/30 text-on-surface-variant/40 cursor-not-allowed'
                }`}>
                {saving ? 'Saving…' : 'Apply Changes'}
              </button>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            {/* Left: sliders */}
            <div className="space-y-8">

              {/* Genuine slider */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                    <span className="text-sm font-bold text-on-surface">Genuine Threshold</span>
                  </div>
                  <span className="text-xl font-bold text-emerald-600 tabular-nums">{(draft.genuine * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0" max="100" step="1"
                  value={Math.round(draft.genuine * 100)}
                  onChange={e => {
                    const val = clamp(parseInt(e.target.value) / 100, draft.suspicious + 0.01, 1.0);
                    setDraft(d => ({ ...d, genuine: Math.round(val * 100) / 100 }));
                  }}
                  className="w-full h-2 rounded-full appearance-none cursor-pointer accent-emerald-500"
                  style={{ background: `linear-gradient(to right, #10b981 ${draft.genuine * 100}%, #e5e7eb ${draft.genuine * 100}%)` }}
                />
                <p className="text-xs text-on-surface-variant/60 mt-2">
                  Documents scoring ≥ <strong>{(draft.genuine * 100).toFixed(0)}%</strong> confidence will be marked <span className="text-emerald-600 font-semibold">GENUINE</span>
                </p>
              </div>

              {/* Suspicious slider */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" />
                    <span className="text-sm font-bold text-on-surface">Suspicious Threshold</span>
                  </div>
                  <span className="text-xl font-bold text-amber-500 tabular-nums">{(draft.suspicious * 100).toFixed(0)}%</span>
                </div>
                <input type="range" min="0" max="100" step="1"
                  value={Math.round(draft.suspicious * 100)}
                  onChange={e => {
                    const val = clamp(parseInt(e.target.value) / 100, 0.01, draft.genuine - 0.01);
                    setDraft(d => ({ ...d, suspicious: Math.round(val * 100) / 100 }));
                  }}
                  className="w-full h-2 rounded-full appearance-none cursor-pointer accent-amber-500"
                  style={{ background: `linear-gradient(to right, #f59e0b ${draft.suspicious * 100}%, #e5e7eb ${draft.suspicious * 100}%)` }}
                />
                <p className="text-xs text-on-surface-variant/60 mt-2">
                  Documents scoring ≥ <strong>{(draft.suspicious * 100).toFixed(0)}%</strong> but below Genuine will be <span className="text-amber-500 font-semibold">SUSPICIOUS</span>
                </p>
              </div>

              {draft.suspicious >= draft.genuine && (
                <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-2xl px-4 py-3">
                  <span className="material-symbols-outlined text-base">warning</span>
                  Suspicious threshold must be lower than Genuine threshold.
                </div>
              )}
            </div>

            {/* Right: zone visualizer */}
            <div className="flex flex-col justify-center gap-6">
              <p className="text-[11px] uppercase tracking-[0.3em] text-on-surface-variant/60 font-bold">Confidence Zone Preview</p>

              {/* Band chart */}
              <div className="rounded-2xl overflow-hidden flex h-14 shadow-sm border border-white/60">
                <motion.div layout className="flex items-center justify-center text-xs font-bold text-white bg-red-500 overflow-hidden"
                  style={{ width: `${fakeZoneWidth}%`, minWidth: fakeZoneWidth > 5 ? undefined : 0 }}
                  title={`FAKE: 0–${(draft.suspicious * 100).toFixed(0)}%`}>
                  {fakeZoneWidth > 8 && 'FAKE'}
                </motion.div>
                <motion.div layout className="flex items-center justify-center text-xs font-bold text-white bg-amber-500 overflow-hidden"
                  style={{ width: `${suspZoneWidth}%`, minWidth: suspZoneWidth > 5 ? undefined : 0 }}
                  title={`SUSPICIOUS: ${(draft.suspicious * 100).toFixed(0)}–${(draft.genuine * 100).toFixed(0)}%`}>
                  {suspZoneWidth > 12 && 'SUSPICIOUS'}
                </motion.div>
                <motion.div layout className="flex items-center justify-center text-xs font-bold text-white bg-emerald-500 overflow-hidden"
                  style={{ width: `${genuineZoneWidth}%`, minWidth: genuineZoneWidth > 5 ? undefined : 0 }}
                  title={`GENUINE: ${(draft.genuine * 100).toFixed(0)}–100%`}>
                  {genuineZoneWidth > 8 && 'GENUINE'}
                </motion.div>
              </div>

              {/* Zone labels */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'FAKE', range: `0 – ${(draft.suspicious * 100).toFixed(0)}%`, color: 'bg-red-50 border-red-200 text-red-700', dot: 'bg-red-500' },
                  { label: 'SUSPICIOUS', range: `${(draft.suspicious * 100).toFixed(0)} – ${(draft.genuine * 100).toFixed(0)}%`, color: 'bg-amber-50 border-amber-200 text-amber-700', dot: 'bg-amber-500' },
                  { label: 'GENUINE', range: `${(draft.genuine * 100).toFixed(0)} – 100%`, color: 'bg-emerald-50 border-emerald-200 text-emerald-700', dot: 'bg-emerald-500' },
                ].map(z => (
                  <div key={z.label} className={`rounded-2xl border p-3 ${z.color}`}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className={`w-2 h-2 rounded-full ${z.dot}`} />
                      <span className="text-[10px] font-bold uppercase tracking-wider">{z.label}</span>
                    </div>
                    <p className="text-sm font-semibold tabular-nums">{z.range}</p>
                  </div>
                ))}
              </div>

              {/* Active config chip */}
              <div className="flex items-center gap-2 text-xs text-on-surface-variant/60 bg-white/60 border border-white/60 rounded-2xl px-4 py-3">
                <span className="material-symbols-outlined text-sm text-primary">info</span>
                <span>
                  Currently active: Genuine ≥ <strong>{(thresholds.genuine * 100).toFixed(0)}%</strong> · Suspicious ≥ <strong>{(thresholds.suspicious * 100).toFixed(0)}%</strong>
                  {isDirty && <span className="ml-1 text-amber-600 font-semibold">(unsaved changes)</span>}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Network overview card */}
        <div className="glass-card rounded-[32px] overflow-hidden relative min-h-[260px] inner-glow">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(177,156,217,0.18),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(178,238,185,0.14),transparent_35%)]" />
          <div className="relative z-10 p-8 h-full flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <div>
                <span className="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider mb-2 inline-block">System Status</span>
                <h3 className="text-xl font-bold text-primary mb-2">Verification Pipeline Active</h3>
                <p className="text-sm text-on-surface-variant/80 max-w-md">
                  CertSentinel is running OCR + image forensics + ML classification on every submitted certificate in real-time.
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-primary">v1.0.0</p>
                <p className="text-xs font-bold uppercase text-on-surface-variant/60">Model Version</p>
              </div>
            </div>
            <div className="flex gap-4 mt-6 flex-wrap">
              {[
                { label: 'OCR Engine', value: 'Tesseract 5.5', icon: 'document_scanner' },
                { label: 'Image Forensics', value: 'ELA + Noise + ORB', icon: 'image_search' },
                { label: 'NLP', value: 'spaCy (lazy)', icon: 'psychology' },
                { label: 'Classifier', value: 'Rule-based fallback', icon: 'model_training' },
              ].map(t => (
                <div key={t.label} className="bg-white/70 border border-white/80 rounded-2xl px-4 py-3 flex items-center gap-3">
                  <span className="material-symbols-outlined text-primary text-lg">{t.icon}</span>
                  <div>
                    <p className="text-[10px] uppercase font-bold text-on-surface-variant/60">{t.label}</p>
                    <p className="text-sm font-semibold text-on-surface">{t.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}
