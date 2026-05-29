import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleStart = () => {
    if (user) {
      if (user.role === 'admin') {
        navigate('/dashboard');
      } else if (user.role === 'verifier') {
        navigate('/analysis');
      } else {
        navigate('/vault');
      }
    } else {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen text-on-surface overflow-hidden relative">
      {/* Background gradients */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_top_left,rgba(177,156,217,0.24),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(178,238,185,0.2),transparent_30%),linear-gradient(180deg,#faf8ff_0%,#f9f9f9_55%,#f6faf7_100%)]" />
      <div className="fixed top-[-10%] left-[-8%] w-[34rem] h-[34rem] rounded-full bg-primary-container/35 blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-12%] right-[-10%] w-[32rem] h-[32rem] rounded-full bg-secondary-container/35 blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="relative z-20 max-w-7xl mx-auto px-6 lg:px-10 pt-8 pb-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.35em] text-on-surface-variant/60 mb-2">Certificate Verification Console</p>
          <h1 className="font-display-lg text-primary leading-none">MedVerify Suite</h1>
        </div>
        <div className="hidden md:flex items-center gap-3">
          <button onClick={handleStart} className="px-5 py-2.5 rounded-full bg-primary text-white text-sm font-semibold shadow-lg shadow-primary/20 hover:shadow-xl transition-all active:scale-95 cursor-pointer">
            {user ? 'Go to Console' : 'Get Started'}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 lg:px-10 pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start mt-4">
          
          {/* Left Column: Welcoming introduction and CTA */}
          <section className="lg:col-span-5 space-y-6">
            <div className="glass-card rounded-[32px] p-8 lg:p-10 border-white/50 text-left">
              <p className="text-[11px] uppercase tracking-[0.35em] text-primary font-bold mb-4">Welcome to MedVerify</p>
              <h2 className="font-display-lg text-on-surface leading-[0.95] mb-5">
                Smart and simple medical certificate verification.
              </h2>
              <p className="font-body-lg text-on-surface-variant/80 max-w-lg">
                MedVerify helps you quickly check if a medical certificate is genuine. Our system reads the document details, scans for signs of editing, and creates a clear authenticity report automatically.
              </p>

              <div className="grid grid-cols-3 gap-3 mt-8">
                {[
                  ['Smart Scan', 'Reads text details'],
                  ['Image Check', 'Scans for edits'],
                  ['Secure Logs', 'Keeps clear records'],
                ].map(([title, copy]) => (
                  <div key={title} className="rounded-3xl bg-white/70 border border-white/80 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-primary font-bold mb-2">{title}</p>
                    <p className="text-xs text-on-surface-variant/75 leading-snug">{copy}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Beginner-friendly Guide Card with CTA */}
            <div className="glass-card rounded-[32px] p-8 lg:p-10 border-white/50 space-y-6 text-left relative overflow-hidden">
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-primary-container/10 rounded-full blur-3xl pointer-events-none"></div>
              <p className="text-[11px] uppercase tracking-[0.35em] text-primary font-bold">Secure Console</p>
              <h3 className="font-headline-md text-headline-md text-on-surface">Ready to start verifying?</h3>
              <p className="font-body-md text-on-surface-variant/80">
                To keep medical data private and secure, all document scans and forensic analysis are conducted inside our protected workspace terminal.
              </p>
              
              <div className="pt-2 space-y-4">
                <button 
                  onClick={handleStart} 
                  className="w-full py-4 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold text-md shadow-lg shadow-primary/20 hover:shadow-xl transition-all active:scale-[0.98] flex items-center justify-center gap-2 cursor-pointer border-t border-white/30"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {user ? 'dashboard' : 'login'}
                  </span>
                  <span>{user ? 'Open Workspace Console' : 'Log In to Secure Console'}</span>
                </button>
                
                <div className="flex items-center justify-center gap-2 text-xs text-on-surface-variant/60 font-semibold uppercase tracking-wider">
                  <span className="material-symbols-outlined text-[16px] text-secondary">verified_user</span>
                  <span>End-to-End Encryption Enabled</span>
                </div>
              </div>
            </div>
          </section>

          {/* Right Column: Process walkthrough and feature definitions */}
          <section className="lg:col-span-7 space-y-6">
            <div className="glass-card rounded-[36px] p-6 lg:p-8 border-white/50 overflow-hidden relative">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(177,156,217,0.12),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(178,238,185,0.14),transparent_35%)]" />
              <div className="relative z-10 flex items-start justify-between gap-6 flex-wrap">
                <div className="text-left">
                  <p className="text-[11px] uppercase tracking-[0.35em] text-on-surface-variant/60 mb-2">How it works</p>
                  <h3 className="font-headline-lg text-on-surface mb-2">Fast and automatic analysis</h3>
                  <p className="text-sm text-on-surface-variant/75 max-w-xl">Our intelligent platform processes documents and presents verifiers with a clear, easy-to-read authenticity summary.</p>
                </div>
                <div className="rounded-[28px] bg-white/70 border border-white/80 px-5 py-4 min-w-[180px] text-left">
                  <p className="text-[10px] uppercase tracking-[0.3em] text-on-surface-variant/60 font-bold mb-1">System status</p>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse" />
                    <p className="text-sm font-semibold text-on-surface">Ready to assist</p>
                  </div>
                </div>
              </div>

              <div className="relative z-10 mt-8 grid gap-4 sm:grid-cols-3 text-left">
                {[
                  { value: '3', label: 'analysis steps', note: 'reads, scans, reports' },
                  { value: '1', label: 'simple report', note: 'all details in one page' },
                  { value: '0', label: 'complex setups', note: 'runs fully in your browser' },
                ].map((item) => (
                  <div key={item.label} className="rounded-[28px] bg-white/65 border border-white/80 p-5">
                    <p className="text-4xl font-display-lg text-primary mb-1">{item.value}</p>
                    <p className="text-sm font-semibold text-on-surface mb-1 uppercase tracking-[0.18em]">{item.label}</p>
                    <p className="text-xs text-on-surface-variant/65">{item.note}</p>
                  </div>
                ))}
              </div>

              <div className="relative z-10 mt-5 rounded-[30px] bg-white/70 border border-white/80 p-5 lg:p-6 text-left">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.3em] text-primary font-bold">Verification Steps</p>
                    <p className="text-sm text-on-surface-variant/70">From upload to secure report</p>
                  </div>
                  <span className="text-xs font-bold uppercase tracking-[0.25em] text-on-surface-variant/50">MedVerify</span>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  {[
                    'Log in to your secure console',
                    'Upload the certificate document',
                    'Wait a few seconds for the smart check',
                    'Open and inspect the detailed report',
                  ].map((item, index) => (
                    <div key={item} className="flex items-start gap-3 rounded-2xl bg-surface/70 p-4 border border-white/70">
                      <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">0{index + 1}</div>
                      <p className="text-sm text-on-surface-variant/80">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid sm:grid-cols-3 gap-4 text-left">
              {[
                ['Authenticity Score', 'Calculates a clear trust percent'],
                ['Key Information', 'Extracts dates, doctors, and edit flags'],
                ['Detailed Summary', 'Combines all details in a single view'],
              ].map(([title, copy]) => (
                <div key={title} className="glass-card rounded-[28px] p-5 border-white/50">
                  <p className="text-[11px] uppercase tracking-[0.35em] text-primary font-bold mb-2">{title}</p>
                  <p className="text-sm text-on-surface-variant/75">{copy}</p>
                </div>
              ))}
            </div>
          </section>

        </div>
      </main>
    </div>
  );
}
