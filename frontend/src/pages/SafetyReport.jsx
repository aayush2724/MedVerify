import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import { medicationAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { FindingCard, Section, Stat } from '../components/FindingCard';

const VERDICT = {
  none: {
    title: 'Nothing flagged in this list',
    body: 'No repeated active ingredients and no daily totals at or near a labeled maximum. That is not the same as "safe" — it only means these two checks found nothing.',
    icon: 'check_circle', tone: 'text-secondary', bg: 'bg-secondary-container/40', border: 'border-secondary/20',
  },
  info: {
    title: 'Checked, with gaps',
    body: 'No dose or duplicate problems were found, but some items could not be assessed. See the coverage notes below.',
    icon: 'info', tone: 'text-primary', bg: 'bg-primary-fixed/50', border: 'border-primary/20',
  },
  moderate: {
    title: 'Something worth raising',
    body: 'This list contains a repeated ingredient or a daily total close to its labeled maximum. Take this to a pharmacist.',
    icon: 'warning', tone: 'text-amber-700', bg: 'bg-amber-100/50', border: 'border-amber-500/20',
  },
  high: {
    title: 'Speak to a pharmacist or doctor',
    body: 'A combined daily total on this list may exceed a labeled maximum. Do not change what you take on your own — take this result to a professional.',
    icon: 'e911_emergency', tone: 'text-error', bg: 'bg-error-container/40', border: 'border-error/20',
  },
};

export default function SafetyReport() {
  const navigate = useNavigate();
  const location = useLocation();
  const { id } = useParams();
  const { user } = useAuth();

  const [result, setResult] = useState(location.state?.result || null);
  // Only a load with an id to fetch starts in the loading state; a direct
  // visit with neither router state nor an id renders the empty state at once.
  const [loading, setLoading] = useState(() => !location.state?.result && Boolean(id));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (result || !id) return;
    (async () => {
      try {
        const res = await medicationAPI.getSafetyCheck(id);
        setResult(res.data);
      } catch (err) {
        setError(err.response?.data?.message || 'That safety check could not be loaded.');
      } finally {
        setLoading(false);
      }
    })();
  }, [id, result]);

  if (loading) {
    return (
      <div className="min-h-screen">
        <Sidebar user={user} />
        <main className="ml-20 lg:ml-72 p-6 lg:p-container-padding">
          <div className="max-w-3xl mx-auto space-y-4">
            <div className="h-32 rounded-3xl bg-white/40 animate-pulse" />
            <div className="h-24 rounded-2xl bg-white/40 animate-pulse" />
          </div>
        </main>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen">
        <Sidebar user={user} />
        <main className="ml-20 lg:ml-72 p-6 lg:p-container-padding">
          <div className="max-w-3xl mx-auto rounded-2xl border border-error/20 bg-error-container/30 p-6 text-error">
            {error || 'No safety check to show. Run one from your medication list.'}
          </div>
        </main>
      </div>
    );
  }

  const verdict = VERDICT[result.highest_severity] || VERDICT.none;
  const findings = result.findings || [];
  const signals = findings.filter((f) => f.severity !== 'info');
  const notes = findings.filter((f) => f.severity === 'info');

  return (
    <div className="min-h-screen">
      <Sidebar user={user} />
      <main className="ml-20 lg:ml-72 p-6 lg:p-container-padding transition-all duration-300">
        <div className="max-w-3xl mx-auto">

          <button onClick={() => navigate('/medications')}
            className="mb-6 flex items-center gap-2 text-sm font-bold text-on-surface-variant/70 hover:text-primary transition-colors print:hidden">
            <span className="material-symbols-outlined text-base">arrow_back</span>
            Back to my medications
          </button>

          {/* Verdict */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className={`rounded-3xl border ${verdict.border} ${verdict.bg} backdrop-blur-2xl p-7 mb-6`}>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-white/70 flex items-center justify-center shrink-0">
                <span className={`material-symbols-outlined ${verdict.tone} text-2xl`}>{verdict.icon}</span>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60 mb-1">
                  Medication safety check
                </p>
                <h1 className={`text-2xl font-bold ${verdict.tone}`}>{verdict.title}</h1>
                <p className="text-on-surface-variant mt-2 leading-relaxed">{verdict.body}</p>
              </div>
            </div>

            <div className="mt-5 pt-5 border-t border-white/50 flex flex-wrap gap-6 text-sm">
              <Stat label="Items checked" value={(result.medications_checked || []).length} />
              <Stat label="Safety signals" value={signals.length} />
              <Stat label="Coverage notes" value={notes.length} />
              <Stat label="Rule engine" value={result.rule_engine_version} />
            </div>
          </motion.div>

          {/* The caveat, before the findings rather than after them. */}
          <div className="mb-6 rounded-2xl border border-primary/15 bg-white/60 backdrop-blur-xl p-4 flex gap-3">
            <span className="material-symbols-outlined text-primary shrink-0">stethoscope</span>
            <p className="text-sm text-on-surface-variant leading-relaxed">{result.disclaimer}</p>
          </div>

          {signals.length > 0 && (
            <Section title="Safety signals" subtitle="Repeated ingredients and daily totals at or near a labeled maximum.">
              {signals.map((f, i) => <FindingCard key={`${f.rule_id}-${i}`} finding={f} />)}
            </Section>
          )}

          {notes.length > 0 && (
            <Section title="Coverage notes" subtitle="What this check could not assess, and why.">
              {notes.map((f, i) => <FindingCard key={`${f.rule_id}-${i}`} finding={f} />)}
            </Section>
          )}

          {findings.length === 0 && (
            <div className="rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl p-8 text-center text-on-surface-variant">
              No rule produced a finding for this list.
            </div>
          )}

          {/* What was checked */}
          <Section title="What was checked" subtitle="The exact list and doses this result was calculated from.">
            <div className="rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl divide-y divide-outline-variant/30">
              {(result.medications_checked || []).map((m) => (
                <div key={m.medication_id} className="p-4">
                  <p className="font-bold text-on-surface text-sm">{m.display_name}</p>
                  <p className="text-xs text-on-surface-variant/70 mt-1">
                    {m.units_per_dose} per dose · {m.doses_per_day}×/day
                    {m.ingredients.length > 0 && ' — '}
                    {m.ingredients.map((i) =>
                      `${i.name}${i.strength_display ? ` ${i.strength_display}` : ''}`).join(', ')}
                  </p>
                </div>
              ))}
            </div>
          </Section>

          {/* Sources */}
          {(result.sources_used || []).length > 0 && (
            <Section title="Data sources" subtitle="Every finding above traces back to one of these.">
              <div className="rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl p-5 space-y-2">
                {result.sources_used.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className="material-symbols-outlined text-base text-primary shrink-0 mt-0.5">link</span>
                    <div>
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noopener noreferrer"
                          className="font-medium text-primary hover:underline">{s.source}</a>
                      ) : (
                        <span className="font-medium text-on-surface">{s.source}</span>
                      )}
                      {s.label_id && (
                        <span className="text-on-surface-variant/50 text-xs"> · label {s.label_id}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          <div className="mt-8 flex flex-wrap gap-3 print:hidden">
            <button onClick={() => window.print()}
              className="py-3 px-5 rounded-2xl bg-white/70 border border-white/50 font-bold text-on-surface hover:bg-white transition-all flex items-center gap-2">
              <span className="material-symbols-outlined">print</span>
              Print for my pharmacist
            </button>
            <button onClick={() => navigate('/medications')}
              className="py-3 px-5 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all">
              Back to my list
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
