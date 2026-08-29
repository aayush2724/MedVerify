/**
 * Shared presentation for one medication-safety finding.
 *
 * Used by both the saved-list report (`SafetyReport`) and the combined
 * prescription report (`PrescriptionCheck`). Kept in one place deliberately:
 * every finding carries a citation and a caveat by contract, and two copies of
 * this card would eventually disagree about whether to render them.
 */
import { useState } from 'react';
import { motion } from 'framer-motion';

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


export function Stat({ label, value }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant/50">{label}</p>
      <p className="font-bold text-on-surface">{value}</p>
    </div>
  );
}


export function Section({ title, subtitle, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-bold text-on-surface">{title}</h2>
      {subtitle && <p className="text-sm text-on-surface-variant/60 mb-3">{subtitle}</p>}
      <div className="space-y-3">{children}</div>
    </section>
  );
}


export function FindingCard({ finding }) {
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

          {/* How an interaction was matched changes how much it means: a label
              naming the drug outright is not the same claim as one naming a
              class it belongs to, so the card says which happened. */}
          {ev.match_type && (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                ev.match_type === 'ingredient'
                  ? 'bg-error-container/50 text-error'
                  : 'bg-primary-fixed/60 text-primary'
              }`}>
                {ev.match_type === 'ingredient' ? 'Named on the label' : 'Matched by drug class'}
              </span>
              {ev.contraindication_wording && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-error-container/50 text-error">
                  Do-not-combine wording
                </span>
              )}
              {ev.mention_count > 1 && (
                <span className="text-[10px] font-medium text-on-surface-variant/60">
                  {ev.mention_count} label passages
                </span>
              )}
            </div>
          )}
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
                  {c.section && (
                    <span className="text-on-surface-variant/50 text-[11px]">
                      {' · '}{c.section.replace(/_/g, ' ')}
                    </span>
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

