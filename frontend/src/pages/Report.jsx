import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { certificateAPI } from '../services/api';

const STATUS_THEMES = {
  GENUINE: {
    border: 'border-emerald-500/20',
    bg: 'bg-emerald-50/40',
    text: 'text-emerald-700',
    badgeBg: 'bg-emerald-500/10',
    badgeText: 'text-emerald-700',
    label: 'Likely Genuine',
    icon: 'check_circle'
  },
  SUSPICIOUS: {
    border: 'border-amber-500/20',
    bg: 'bg-amber-50/40',
    text: 'text-amber-700',
    badgeBg: 'bg-amber-500/10',
    badgeText: 'text-amber-700',
    label: 'Suspicious Anomalies',
    icon: 'warning'
  },
  FAKE: {
    border: 'border-red-500/20',
    bg: 'bg-red-50/40',
    text: 'text-red-700',
    badgeBg: 'bg-red-500/10',
    badgeText: 'text-red-700',
    label: 'Likely Fake / Altered',
    icon: 'dangerous'
  }
};

const fadeUp = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
};

export default function Report() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    certificateAPI.getById(id)
      .then(res => setRecord(res.data))
      .catch(() => setError('Certificate record not found.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <PageShell><LoadingSkeleton /></PageShell>;
  if (error) return <PageShell><ErrorState message={error} onBack={() => navigate('/vault')} /></PageShell>;

  const { status, confidence_score, reasons, extracted_info, image_forensics, processing_time_ms } = record;
  
  const theme = STATUS_THEMES[status] || STATUS_THEMES.SUSPICIOUS;
  const confidencePercent = Math.round((confidence_score || 0) * 100);
  const filename = record.filename || 'unknown_document.pdf';

  // Read ELA and Font scores correcting for the nested ml_features bug
  const elaScore = image_forensics?.ml_features?.ela_score ?? image_forensics?.ela_score;
  const fontScore = image_forensics?.ml_features?.font_consistency_score ?? image_forensics?.font_consistency_score;
  const copyMove = image_forensics?.ml_features?.copy_move_detected ?? image_forensics?.copy_move_detected;
  const noiseScore = image_forensics?.ml_features?.noise_inconsistency_score ?? image_forensics?.noise_inconsistency_score;

  return (
    <PageShell>
      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-6 lg:py-8 space-y-6 print:py-2">
        
        {/* Navigation Breadcrumb - Hidden when printing */}
        <motion.button
          variants={fadeUp}
          initial="initial"
          animate="animate"
          onClick={() => navigate('/vault')}
          className="print:hidden inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant/60 hover:text-primary transition-colors cursor-pointer"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          <span>Back to Records Ledger</span>
        </motion.button>

        {/* Cohesive Summary Banner Card */}
        <motion.section 
          variants={fadeUp}
          initial="initial"
          animate="animate"
          className="glass-card inner-glow rounded-3xl p-6 lg:p-8 border-white/50 overflow-hidden relative text-left print:border-none print:shadow-none print:bg-white"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(177,156,217,0.1),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(178,238,185,0.1),transparent_35%)] print:hidden" />
          
          <div className="relative z-10 space-y-6">
            
            {/* Header: Verdict & Circular Progress Indicator */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/20 pb-5">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${theme.badgeBg} ${theme.badgeText}`}>
                    <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>{theme.icon}</span>
                    {theme.label}
                  </span>
                </div>
                <h2 className="text-2xl lg:text-3xl font-extrabold text-on-surface tracking-tight">
                  Verification Verdict: <span className={theme.text}>{STATUS_THEMES[status]?.label || status}</span>
                </h2>
              </div>
              
              {/* Radial Confidence Indicator */}
              <div className="flex items-center gap-3 bg-white/40 border border-white/60 rounded-2xl px-4 py-2.5 shadow-sm shrink-0 print:border-none print:bg-transparent print:shadow-none">
                <div className="relative w-10 h-10">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                    <circle className="text-outline-variant/30" cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3.5"></circle>
                    <circle 
                      className="text-primary transition-all duration-1000" 
                      cx="18" cy="18" r="16" fill="none" 
                      stroke="currentColor" strokeDasharray="100" strokeDashoffset={100 - confidencePercent} 
                      strokeLinecap="round" strokeWidth="3.5"
                    ></circle>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-[10px] font-extrabold text-primary">{confidencePercent}%</span>
                  </div>
                </div>
                <div>
                  <p className="text-[9px] uppercase tracking-widest text-on-surface-variant/60 font-bold leading-none">Confidence</p>
                  <p className="text-[12px] font-bold text-on-surface mt-0.5">Scoring Match</p>
                </div>
              </div>
            </div>

            {/* Document details & action buttons */}
            <div className="grid grid-cols-1 md:grid-cols-[1.3fr_0.7fr] print:grid-cols-1 gap-6 items-center">
              
              {/* Left Column: Filename & Description */}
              <div className="space-y-3">
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-on-surface-variant/50 font-bold">Document Source</p>
                  <div className="flex items-center gap-2 mt-1 bg-white/30 border border-white/40 rounded-xl px-3.5 py-2 w-full max-w-md print:bg-transparent print:border-none print:px-0">
                    <span className="material-symbols-outlined text-on-surface-variant/50 text-[18px]">description</span>
                    <span className="text-xs font-mono font-semibold text-on-surface truncate max-w-[260px] md:max-w-[340px] print:max-w-full" title={filename}>
                      {filename}
                    </span>
                  </div>
                </div>
                
                {/* Clean Metadata Badge Row */}
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="px-2.5 py-1 rounded-lg bg-white/40 border border-white/50 text-[10px] font-bold text-on-surface-variant/70 print:bg-transparent print:border-none print:px-0">
                    ID: <code className="font-mono">{getShortId(id)}</code>
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-white/40 border border-white/50 text-[10px] font-bold text-on-surface-variant/70 print:bg-transparent print:border-none print:px-0">
                    Duration: {processing_time_ms} ms
                  </span>
                  <span className="px-2.5 py-1 rounded-lg bg-white/40 border border-white/50 text-[10px] font-bold text-on-surface-variant/70 print:bg-transparent print:border-none print:px-0">
                    Engine: {record.model_version || 'v1.0.0'}
                  </span>
                </div>
              </div>

              {/* Right Column: Actions - Hidden during PDF Print */}
              <div className="print:hidden flex flex-col gap-2.5 w-full">
                <button 
                  onClick={() => window.print()} 
                  className="w-full px-5 py-3 rounded-xl bg-gradient-to-tr from-primary to-primary-container text-white text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer inner-glow"
                >
                  <span className="material-symbols-outlined text-[16px]">print</span>
                  Export PDF Report
                </button>
              </div>

            </div>

          </div>
        </motion.section>

        {/* Structured Body: Extracted Fields vs. Fraud Signals */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 print:gap-4">
          
          {/* Card: Extracted Fields */}
          <motion.div variants={fadeUp} initial="initial" animate="animate" className="glass-card inner-glow rounded-3xl overflow-hidden border-white/50 text-left print:border-none print:shadow-none print:bg-white">
            <div className="px-5 py-3.5 border-b border-white/20 bg-white/20 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">person_search</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface">Extracted Information</h3>
            </div>
            
            <div className="divide-y divide-white/20">
              {[
                { label: 'Physician Name', val: extracted_info?.doctor_name, icon: 'badge' },
                { label: 'Hospital Facility', val: extracted_info?.hospital_name, icon: 'local_hospital' },
                { label: 'Signature Date(s)', val: extracted_info?.dates?.join(', '), icon: 'calendar_month' },
                { label: 'Licensing Registration', val: extracted_info?.registration_numbers?.join(', '), icon: 'pin' },
              ].map(({ label, val, icon }) => (
                <div key={label} className="p-4 flex items-start gap-3 hover:bg-white/10 transition-colors">
                  <div className="w-7 h-7 rounded-lg bg-white/50 border border-white/60 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="material-symbols-outlined text-primary text-[16px]">{icon}</span>
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider">{label}</p>
                    <p className={`text-xs font-semibold ${val ? 'text-on-surface' : 'text-on-surface-variant/50 italic font-medium'}`}>
                      {val || 'Not detected'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card: Detection Signals */}
          <motion.div variants={fadeUp} initial="initial" animate="animate" className="glass-card inner-glow rounded-3xl overflow-hidden border-white/50 text-left print:border-none print:shadow-none print:bg-white">
            <div className="px-5 py-3.5 border-b border-white/20 bg-white/20 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[18px]">gpp_maybe</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface">Verification Signals</h3>
            </div>
            
            <div className="divide-y divide-white/20">
              {(reasons || []).map((reason, i) => (
                <div key={i} className="flex items-start gap-3 p-4 hover:bg-white/10 transition-colors">
                  <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="material-symbols-outlined text-amber-600 text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>
                  </div>
                  <p className="text-xs text-on-surface-variant/80 font-medium leading-relaxed mt-0.5">{reason}</p>
                </div>
              ))}
              
              {(!reasons || reasons.length === 0) && (
                <div className="p-8 flex flex-col items-center justify-center text-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                    <span className="material-symbols-outlined text-emerald-600 text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
                  </div>
                  <div>
                    <p className="text-xs font-bold text-on-surface">No Anomalies Found</p>
                    <p className="text-[10px] text-on-surface-variant/60 mt-0.5 max-w-[240px]">All forensic and metadata validation passes with a high confidence rating.</p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>

        </div>

        {/* Digital Forensic Analysis Section */}
        <motion.div variants={fadeUp} initial="initial" animate="animate" className="glass-card inner-glow rounded-3xl overflow-hidden border-white/50 text-left print:border-none print:shadow-none print:bg-white">
          <div className="px-5 py-3.5 border-b border-white/20 bg-white/20 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[18px]">biometric_profile</span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface">Digital Forensic Diagnostics</h3>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-px bg-outline-variant/30 print:bg-transparent">
            {[
              {
                label: 'Copy-Move Detected',
                val: copyMove === true ? 'Yes' : (copyMove === false ? 'No' : 'No'),
                hint: 'Checks clone tampering',
                warn: copyMove === true,
                icon: 'content_copy'
              },
              {
                label: 'Error Level Analysis (ELA)',
                val: typeof elaScore === 'number' ? elaScore.toFixed(2) : '0.00',
                hint: 'Double compression score',
                warn: typeof elaScore === 'number' && elaScore > 0.5,
                icon: 'broken_image'
              },
              {
                label: 'Noise Inconsistency',
                val: typeof noiseScore === 'number' ? noiseScore.toFixed(2) : '0.00',
                hint: 'Substrate density match',
                warn: typeof noiseScore === 'number' && noiseScore > 0.6,
                icon: 'grain'
              },
              {
                label: 'Font Consistency',
                val: typeof fontScore === 'number' ? fontScore.toFixed(2) : '1.00',
                hint: 'Typographical integrity',
                warn: typeof fontScore === 'number' && fontScore < 0.7,
                icon: 'font_download'
              }
            ].map(({ label, val, hint, warn, icon }) => (
              <div key={label} className="bg-white/60 p-5 flex flex-col justify-between min-h-[110px] print:bg-white print:border-b print:border-outline-variant/20">
                <div className="flex items-center gap-2">
                  <span className={`material-symbols-outlined text-sm ${warn ? 'text-error' : 'text-on-surface-variant/50'}`}>{icon}</span>
                  <p className="text-[10px] text-on-surface-variant/60 font-bold uppercase tracking-wider">{label}</p>
                </div>
                <div className="mt-3">
                  <p className={`text-xl font-bold leading-none tracking-tight ${warn ? 'text-error' : 'text-on-surface'}`}>
                    {val}
                  </p>
                  <p className="text-[9px] text-on-surface-variant/40 font-semibold tracking-wide uppercase mt-1.5 leading-none">{hint}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

      </div>
    </PageShell>
  );
}

function PageShell({ children }) {
  return (
    <div className="min-h-screen text-on-surface overflow-x-hidden relative print:bg-white">
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_top_left,rgba(177,156,217,0.18),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(178,238,185,0.14),transparent_30%),linear-gradient(180deg,#faf8ff_0%,#f9f9f9_50%,#f7faf7_100%)] print:hidden" />
      {children}
    </div>
  );
}

function getShortId(id) {
  if (!id) return '—';
  if (id.length <= 12) return id;
  return `${id.substring(0, 8)}...${id.substring(id.length - 4)}`;
}

function LoadingSkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
      <div className="h-4 w-32 rounded-full bg-outline-variant/30 animate-pulse" />
      <div className="h-[200px] rounded-3xl bg-outline-variant/20 animate-pulse" />
      <div className="grid md:grid-cols-2 gap-5">
        <div className="h-[220px] rounded-3xl bg-outline-variant/20 animate-pulse" />
        <div className="h-[220px] rounded-3xl bg-outline-variant/20 animate-pulse" />
      </div>
      <div className="h-[120px] rounded-3xl bg-outline-variant/20 animate-pulse" />
    </div>
  );
}

function ErrorState({ message, onBack }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center text-red-600 mb-2">
        <span className="material-symbols-outlined text-2xl">error</span>
      </div>
      <h3 className="text-lg font-bold text-on-surface">Data Load Failure</h3>
      <p className="text-xs text-on-surface-variant/70 max-w-xs">{message}</p>
      <button onClick={onBack} className="mt-2 px-5 py-2 rounded-xl bg-primary text-white text-xs font-bold shadow-md hover:shadow-lg transition-all cursor-pointer">
        Return to Records
      </button>
    </div>
  );
}
