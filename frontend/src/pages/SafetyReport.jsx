import { useState, useEffect } from 'react';
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import { medicationAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

/**
 * Severity presentation deliberately mirrors Module 1's Tamper Signal /
 * Content Audit Check pattern: red for something acted on now, amber for
 * something to raise, blue-violet for an informational gap in coverage.
 */
const SEVERITY = {
  high: {
    label: 'Action needed', icon: 'e911_emergency', chip: 'Safety Signal',
    text: 'text-error', bg: 'bg-error-container/40', border: 'border-error/20', dot: 'bg-error',
  },
  moderate: {
    label: 'Worth checking', icon: 'warning', chip: 'Safety Signal',
    text: 'text-amber-700', bg: 'bg-amber-100/50', border: 'border-amber-500/20', dot: 'bg-amber-500',
  },
  info: {
    label: 'Not checked', icon: 'help', chip: 'Coverage Note',
    text: 'text-primary', bg: 'bg-primary-fixed/50', border: 'border-primary/20', dot: 'bg-primary',
  },
};

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
  const [loading, setLoading] = useState(!location.state?.result);
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
            {error || 'No result to show.'}
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

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant/50">{label}</p>
      <p className="font-bold text-on-surface">{value}</p>
    </div>
  );
}

function Section({ title, subtitle, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-bold text-on-surface">{title}</h2>
      {subtitle && <p className="text-sm text-on-surface-variant/60 mb-3">{subtitle}</p>}
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function FindingCard({ finding }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const cfg = SEVERITY[finding.severity] || SEVERITY.info;
  const ev = finding.evidence || {};

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl border ${cfg.border} ${cfg.bg} backdrop-blur-2xl p-5`}>
      <div className="flex items-start gap-3">
        <span className={`material-symbols-outlined ${cfg.text} shrink-0`}>{cfg.icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-[10px] font-bold uppercase tracking-widest ${cfg.text}`}>
              {cfg.chip} · {cfg.label}
            </span>
            <span className="text-[10px] font-mono text-on-surface-variant/40">{finding.rule_id}</span>
          </div>
          <h3 className="font-bold text-on-surface">{finding.title}</h3>
          <p className="text-sm text-on-surface-variant mt-1.5 leading-relaxed">{finding.message}</p>

          {/* Dose maths, shown rather than asserted */}
          {ev.labeled_max_daily_mg != null && ev.combined_daily_mg != null && (
            <div className="mt-4">
              <div className="flex justify-between text-xs font-bold text-on-surface-variant/70 mb-1.5">
                <span>{ev.combined_daily_mg.toLocaleString()} mg from your list</span>
                <span>labeled max {ev.labeled_max_daily_mg.toLocaleString()} mg</span>
              </div>
              <div className="h-2.5 rounded-full bg-white/60 overflow-hidden">
                <div className={`h-full rounded-full ${cfg.dot}`}
                  style={{ width: `${Math.min(100, (ev.percent_of_max ?? 0))}%` }} />
              </div>
              <p className="text-[11px] text-on-surface-variant/60 mt-1">
                {ev.percent_of_max}% of the labeled daily maximum
              </p>
            </div>
          )}

          {finding.products?.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {finding.products.map((p) => (
                <span key={p} className="text-xs px-2.5 py-1 rounded-lg bg-white/70 text-on-surface-variant font-medium">
                  {p}
                </span>
              ))}
            </div>
          )}

          {/* Citations — required on every finding */}
          {finding.citations?.length > 0 && (
            <div className="mt-4 pt-3 border-t border-white/50">
              <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant/50 mb-1.5">
                Source
              </p>
              {finding.citations.map((c, i) => (
                <div key={i} className="text-xs text-on-surface-variant/80 mb-1.5">
                  {c.url ? (
                    <a href={c.url} target="_blank" rel="noopener noreferrer"
                      className="font-medium text-primary hover:underline">{c.source}</a>
                  ) : (
                    <span className="font-medium">{c.source}</span>
                  )}
                  {c.excerpt && (
                    <p className="text-on-surface-variant/60 mt-0.5 line-clamp-3 italic">“{c.excerpt}”</p>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="mt-3 text-xs text-on-surface-variant/70 leading-relaxed border-l-2 border-primary/30 pl-3">
            {finding.caveat}
          </p>

          {ev.contributions?.length > 0 && (
            <>
              <button onClick={() => setShowEvidence((v) => !v)}
                className="mt-3 text-xs font-bold text-primary hover:underline flex items-center gap-1 print:hidden">
                <span className="material-symbols-outlined text-sm">
                  {showEvidence ? 'expand_less' : 'expand_more'}
                </span>
                {showEvidence ? 'Hide the calculation' : 'Show the calculation'}
              </button>
              {showEvidence && (
                <div className="mt-2 rounded-xl bg-white/60 p-3 text-xs space-y-1.5">
                  {ev.contributions.map((c, i) => (
                    <div key={i} className="flex justify-between gap-3">
                      <span className="text-on-surface-variant truncate">{c.product}</span>
                      <span className="font-mono text-on-surface shrink-0">
                        {c.daily_mg != null
                          ? `${c.strength_mg} mg × ${c.units_per_dose} × ${c.doses_per_day}/day = ${c.daily_mg} mg`
                          : (c.reason || 'not counted')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
