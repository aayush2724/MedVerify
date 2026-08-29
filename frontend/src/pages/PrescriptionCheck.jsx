/**
 * Prescription Check — Module 2, Phase 3
 *
 * One upload, both modules: is this document authentic, and is the medication
 * regimen written on it internally safe?
 *
 * The page is built around one editorial rule. The medication list shown here
 * was read by OCR and confirmed by nobody, so the reading caveat sits *above*
 * the findings, and every detected row states how it was read — whether the
 * frequency came off the page or was assumed, and whether the product was
 * matched at all. A screenshot of this page should not be able to imply more
 * certainty than the pipeline actually had.
 */
import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from '../components/Sidebar';
import { FindingCard, Section, Stat } from '../components/FindingCard';
import { pipelineAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

const DOCUMENT_VERDICT = {
  GENUINE: {
    label: 'No tampering detected', icon: 'verified',
    tone: 'text-secondary', bg: 'bg-secondary-container/40', border: 'border-secondary/20',
  },
  SUSPICIOUS: {
    label: 'Possible tampering', icon: 'warning',
    tone: 'text-amber-700', bg: 'bg-amber-100/50', border: 'border-amber-500/20',
  },
  FAKE: {
    label: 'Likely forged', icon: 'gpp_bad',
    tone: 'text-error', bg: 'bg-error-container/40', border: 'border-error/20',
  },
  ERROR: {
    label: 'Could not be analysed', icon: 'help',
    tone: 'text-primary', bg: 'bg-primary-fixed/50', border: 'border-primary/20',
  },
};

const CONFIDENCE_LABEL = {
  high: 'Read with confidence',
  medium: 'Best guess from the text',
  low: 'Uncertain reading',
};

export default function PrescriptionCheck() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const choose = useCallback((picked) => {
    if (!picked) return;
    setFile(picked);
    setResult(null);
    setError(null);
  }, []);

  const run = async () => {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setProgress(0);
    try {
      const res = await pipelineAPI.analyse(file, (event) => {
        if (event.total) setProgress(Math.round((event.loaded * 100) / event.total));
      });
      setResult(res.data);
    } catch (err) {
      setError(
        err.response?.data?.message ||
        err.response?.data?.error ||
        'That document could not be analysed. Check the file and try again.',
      );
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setProgress(0);
    if (inputRef.current) inputRef.current.value = '';
  };

  const findings = result?.safety?.findings || [];
  const signals = findings.filter((f) => f.severity !== 'info');
  const notes = findings.filter((f) => f.severity === 'info');
  const detected = result?.medications_detected || [];
  const verdict = result
    ? DOCUMENT_VERDICT[result.document.status] || DOCUMENT_VERDICT.ERROR
    : null;

  return (
    <div className="min-h-screen">
      <Sidebar user={user} />
      <main className="ml-20 lg:ml-72 p-6 lg:p-container-padding transition-all duration-300">
        <div className="max-w-3xl mx-auto">

          <header className="mb-7">
            <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60 mb-1">
              Combined check
            </p>
            <h1 className="text-2xl font-bold text-on-surface">Prescription Check</h1>
            <p className="text-on-surface-variant mt-2 leading-relaxed">
              Upload a prescription once. It is checked for tampering, and the medications
              written on it are checked for repeated ingredients, daily totals against
              labeled maximums, and interactions documented on the drugs’ own labels.
            </p>
          </header>

          {/* Upload */}
          {!result && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  choose(e.dataTransfer.files?.[0]);
                }}
                onClick={() => inputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    inputRef.current?.click();
                  }
                }}
                className={`rounded-3xl border-2 border-dashed p-10 text-center cursor-pointer transition-all backdrop-blur-2xl ${
                  dragging
                    ? 'border-primary bg-primary-fixed/40'
                    : 'border-outline-variant bg-white/60 hover:border-primary/50'
                }`}
              >
                <span className="material-symbols-outlined text-4xl text-primary">
                  {file ? 'description' : 'upload_file'}
                </span>
                <p className="font-bold text-on-surface mt-3">
                  {file ? file.name : 'Drop a prescription here, or click to choose'}
                </p>
                <p className="text-sm text-on-surface-variant/70 mt-1">
                  PNG, JPG or PDF · up to 16 MB
                </p>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf"
                  className="hidden"
                  onChange={(e) => choose(e.target.files?.[0])}
                />
              </div>

              {busy && (
                <div className="mt-4">
                  <div className="h-2 rounded-full bg-white/60 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all"
                      style={{ width: `${Math.max(progress, 8)}%` }}
                    />
                  </div>
                  <p className="text-xs text-on-surface-variant/70 mt-2">
                    Reading the document, then checking the medications on it. This can take
                    a minute — drug lookups are fetched live the first time.
                  </p>
                </div>
              )}

              {error && (
                <div className="mt-4 rounded-2xl border border-error/20 bg-error-container/30 p-4 text-sm text-error">
                  {error}
                </div>
              )}

              <button
                onClick={run}
                disabled={!file || busy}
                className="mt-5 w-full py-3.5 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.01] active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
              >
                {busy ? 'Analysing…' : 'Run both checks'}
              </button>
            </motion.div>
          )}

          {/* Result */}
          {result && (
            <>
              {/* Half one — the document itself */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-3xl border ${verdict.border} ${verdict.bg} backdrop-blur-2xl p-7 mb-6`}
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-white/70 flex items-center justify-center shrink-0">
                    <span className={`material-symbols-outlined ${verdict.tone} text-2xl`}>
                      {verdict.icon}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60 mb-1">
                      Document forensics
                    </p>
                    <h2 className={`text-2xl font-bold ${verdict.tone}`}>{verdict.label}</h2>
                    <p className="text-on-surface-variant mt-1 text-sm truncate">
                      {result.document.original_filename}
                    </p>
                  </div>
                </div>

                <div className="mt-5 pt-5 border-t border-white/50 flex flex-wrap gap-6 text-sm">
                  <Stat
                    label="Confidence"
                    value={
                      result.document.confidence_score != null
                        ? `${Math.round(result.document.confidence_score * 100)}%`
                        : '—'
                    }
                  />
                  <Stat label="Medications read" value={detected.length} />
                  <Stat label="Safety signals" value={signals.length} />
                  <Stat label="Coverage notes" value={notes.length} />
                </div>

                <button
                  onClick={() => navigate(`/report/${result.document.record_id}`)}
                  className="mt-5 text-sm font-bold text-primary hover:underline flex items-center gap-1"
                >
                  See the full forensic report
                  <span className="material-symbols-outlined text-base">arrow_forward</span>
                </button>
              </motion.div>

              {/* How the list was read — above the findings, deliberately. */}
              <div className="mb-6 rounded-2xl border border-amber-500/25 bg-amber-100/40 backdrop-blur-xl p-4 flex gap-3">
                <span className="material-symbols-outlined text-amber-700 shrink-0">
                  document_scanner
                </span>
                <p className="text-sm text-on-surface-variant leading-relaxed">
                  {result.reading_caveat}
                </p>
              </div>

              {result.safety?.disclaimer && (
                <div className="mb-6 rounded-2xl border border-primary/15 bg-white/60 backdrop-blur-xl p-4 flex gap-3">
                  <span className="material-symbols-outlined text-primary shrink-0">stethoscope</span>
                  <p className="text-sm text-on-surface-variant leading-relaxed">
                    {result.safety.disclaimer}
                  </p>
                </div>
              )}

              {/* What was read off the page */}
              {detected.length > 0 && (
                <Section
                  title="Read from the document"
                  subtitle="Check each line against the original. This is what the rules below ran on."
                >
                  <div className="rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl divide-y divide-outline-variant/30">
                    {detected.map((m) => (
                      <DetectedRow key={m.id} med={m} />
                    ))}
                  </div>
                </Section>
              )}

              {signals.length > 0 && (
                <Section
                  title="Safety signals"
                  subtitle="Repeated ingredients, daily totals near a labeled maximum, and label-documented interactions."
                >
                  {signals.map((f, i) => <FindingCard key={`${f.rule_id}-${i}`} finding={f} />)}
                </Section>
              )}

              {notes.length > 0 && (
                <Section title="Coverage notes" subtitle="What this check could not assess, and why.">
                  {notes.map((f, i) => <FindingCard key={`${f.rule_id}-${i}`} finding={f} />)}
                </Section>
              )}

              {detected.length > 0 && findings.length === 0 && (
                <div className="rounded-2xl border border-white/40 bg-white/60 backdrop-blur-2xl p-8 text-center text-on-surface-variant">
                  No rule produced a finding for the medications read off this document.
                </div>
              )}

              <div className="mt-8 flex flex-wrap gap-3 print:hidden">
                <button
                  onClick={() => window.print()}
                  className="py-3 px-5 rounded-2xl bg-white/70 border border-white/50 font-bold text-on-surface hover:bg-white transition-all flex items-center gap-2"
                >
                  <span className="material-symbols-outlined">print</span>
                  Print for my pharmacist
                </button>
                <button
                  onClick={reset}
                  className="py-3 px-5 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all"
                >
                  Check another document
                </button>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

/**
 * One medication read off the page.
 *
 * Provenance sits next to the value rather than in a footnote: an assumed
 * frequency and a stated one look different, because a daily total built on an
 * assumption can be wrong in the direction that matters.
 */
function DetectedRow({ med }) {
  const unmatched = !med.matched_product;
  return (
    <div className="p-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <p className="font-bold text-on-surface text-sm">
            {med.resolved_name || med.display_name}
            {med.strength_text && (
              <span className="font-normal text-on-surface-variant"> · {med.strength_text}</span>
            )}
          </p>
          <p className="text-xs text-on-surface-variant/60 mt-0.5 font-mono truncate">
            “{med.line}”
          </p>
        </div>
        <span
          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md shrink-0 ${
            unmatched
              ? 'bg-primary-fixed/60 text-primary'
              : 'bg-secondary-container/60 text-secondary'
          }`}
        >
          {unmatched ? 'Not matched' : CONFIDENCE_LABEL[med.match_confidence] || 'Matched'}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-on-surface-variant/80">
        <span>
          {med.units_per_dose} per dose
          {med.units_source === 'assumed' && (
            <span className="text-on-surface-variant/50"> (assumed)</span>
          )}
        </span>
        <span>
          {med.doses_per_day}×/day
          {med.frequency_source === 'assumed' ? (
            <span className="text-amber-700 font-medium"> (assumed — not stated on the page)</span>
          ) : (
            med.schedule_note && (
              <span className="text-on-surface-variant/50"> (read as “{med.schedule_note}”)</span>
            )
          )}
        </span>
        {med.resolution_status === 'not_attempted' && (
          <span className="text-amber-700 font-medium">
            Never looked up — past this document’s limit
          </span>
        )}
      </div>

      {/* The matched product carries drugs the page never named, so findings
          below may concern something that is not on this prescription. */}
      {med.extra_ingredients?.length > 0 && (
        <p className="mt-2 text-xs text-amber-700 bg-amber-100/50 rounded-lg px-2.5 py-1.5">
          The closest product on file also contains{' '}
          <span className="font-bold">{med.extra_ingredients.join(', ')}</span>, which this
          document did not name. Check it against what was dispensed.
        </p>
      )}
    </div>
  );
}
