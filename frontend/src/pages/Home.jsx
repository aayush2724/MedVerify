import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';

const ROLE_HOME = { admin: '/dashboard', verifier: '/analysis', viewer: '/vault' };

const MODULES = [
  {
    icon: 'gavel',
    tag: 'Module 1 · For verifiers & auditors',
    title: 'Document Forensics',
    copy: 'Checks whether a medical certificate or report is authentic. OCR reads the document, image forensics scan for signs of editing, and every run lands in an auditable ledger.',
    points: ['OCR text integrity', 'Error-level & clone analysis', 'Persistent audit trail'],
    cta: 'Verify a document',
    path: '/analysis',
    guestPath: '/login',
  },
  {
    icon: 'pill',
    tag: 'Module 2 · For patients & consumers',
    title: 'Medication Safety Check',
    copy: 'Build a personal medication list and check it for repeated active ingredients and daily totals against published FDA label limits. Every flag cites its public source.',
    points: ['Duplicate-ingredient detection', 'Daily totals vs. labeled maximums', 'RxNorm & openFDA sourced'],
    cta: 'Check my medications',
    path: '/medications',
    guestPath: '/login',
  },
];

const STEPS = [
  ['Sign in', 'Every workspace is scoped to your account and role.'],
  ['Upload or add', 'A document to verify, or the medications you take.'],
  ['Automatic analysis', 'Forensic checks or the safety rule engine run in seconds.'],
  ['Read the report', 'Clear verdicts with the evidence and sources behind them.'],
];

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const go = (path, guestPath) => navigate(user ? path : guestPath);
  const handleStart = () => navigate(user ? (ROLE_HOME[user.role] || '/vault') : '/login');

  return (
    <div className="min-h-screen text-on-surface relative overflow-x-hidden">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_top_left,rgba(177,156,217,0.2),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(178,238,185,0.16),transparent_30%),linear-gradient(180deg,#faf8ff_0%,#f9f9f9_55%,#f6faf7_100%)]" />

      {/* Header */}
      <header className="relative z-20 max-w-6xl mx-auto px-6 lg:px-10 pt-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-primary-container flex items-center justify-center shadow-md shadow-primary/20">
            <span className="material-symbols-outlined text-white text-[22px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              shield_with_heart
            </span>
          </div>
          <div>
            <p className="text-lg font-bold tracking-tight text-on-surface leading-none">MedVerify</p>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-on-surface-variant/50 mt-0.5">
              Verification Suite
            </p>
          </div>
        </div>
        <button
          onClick={handleStart}
          className="px-5 py-2.5 rounded-full bg-primary text-white text-sm font-bold shadow-md shadow-primary/20 hover:shadow-lg transition-all active:scale-95"
        >
          {user ? 'Open Console' : 'Sign In'}
        </button>
      </header>

      {/* Hero */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 lg:px-10">
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="pt-16 lg:pt-24 pb-12 text-center max-w-3xl mx-auto"
        >
          <p className="text-[11px] font-bold uppercase tracking-[0.35em] text-primary mb-5">
            Document forensics · Medication safety
          </p>
          <h1 className="text-4xl lg:text-[3.4rem] font-extrabold tracking-tight leading-[1.08] text-on-surface">
            One platform for trust in
            <span className="text-primary"> medical documents</span> and
            <span className="text-primary"> everyday medications</span>.
          </h1>
          <p className="mt-6 text-lg text-on-surface-variant/75 leading-relaxed max-w-2xl mx-auto">
            MedVerify verifies clinical documents for tampering — and helps patients catch the
            medication mistakes that hide inside combination products. Two modules, one secure
            backbone, every result explainable.
          </p>
        </motion.section>

        {/* Module cards */}
        <section className="grid md:grid-cols-2 gap-5 pb-14">
          {MODULES.map((m, i) => (
            <motion.div
              key={m.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.1 + i * 0.08, ease: 'easeOut' }}
              className="glass-card rounded-[28px] p-8 border-white/50 text-left flex flex-col hover:shadow-xl hover:shadow-primary/5 transition-shadow"
            >
              <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center mb-5">
                <span className="material-symbols-outlined text-primary text-[26px]">{m.icon}</span>
              </div>
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant/50 mb-2">{m.tag}</p>
              <h2 className="text-2xl font-bold text-on-surface mb-3">{m.title}</h2>
              <p className="text-sm text-on-surface-variant/75 leading-relaxed mb-5">{m.copy}</p>
              <ul className="space-y-2 mb-7">
                {m.points.map((pt) => (
                  <li key={pt} className="flex items-center gap-2.5 text-sm text-on-surface-variant">
                    <span className="material-symbols-outlined text-secondary text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                      check_circle
                    </span>
                    {pt}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => go(m.path, m.guestPath)}
                className="mt-auto w-full py-3.5 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-bold shadow-md shadow-primary/20 hover:shadow-lg active:scale-[0.98] transition-all flex items-center justify-center gap-2"
              >
                {m.cta}
                <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
              </button>
            </motion.div>
          ))}
        </section>

        {/* How it works */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.25, ease: 'easeOut' }}
          className="glass-card rounded-[28px] p-8 lg:p-10 mb-14 text-left"
        >
          <div className="flex items-end justify-between flex-wrap gap-3 mb-8">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-primary mb-2">How it works</p>
              <h3 className="text-2xl font-bold text-on-surface">From sign-in to a sourced report</h3>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {STEPS.map(([title, copy], index) => (
              <div key={title} className="rounded-2xl bg-white/60 border border-white/70 p-5">
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold mb-3">
                  {index + 1}
                </div>
                <p className="text-sm font-bold text-on-surface mb-1">{title}</p>
                <p className="text-xs text-on-surface-variant/70 leading-relaxed">{copy}</p>
              </div>
            ))}
          </div>
        </motion.section>

        {/* Footer note */}
        <footer className="pb-10 text-center">
          <p className="text-xs text-on-surface-variant/50 max-w-2xl mx-auto leading-relaxed">
            The Medication Safety Check is an informational tool built on published RxNorm and
            openFDA label data. It is not medical advice — always confirm with a pharmacist or doctor.
          </p>
        </footer>
      </main>
    </div>
  );
}
