import Sidebar from '../components/Sidebar';

export default function ForensicReport() {
  const user = {
    name: "Dr. Alexander Thorne",
    role: "Senior Forensic Lead",
    avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuCx9pEksSfepdb9zDTtfwPbbT7c_OplpA2ekaqkQHhzXAYiHSjppHiqphVSN2h3kDrQRbdWjgCohEZLOYh7KHfDJgIs_XOD_GbShfSOpy9a3O4T5rwt1rXgMSGbGkTUC6-Tdhc7plITdtolD_Yxp8DM7h0oYmCDdAWC_jry_s-jGvd2_8GuTn1au8FYpO1Ozezn_w4M12-COZndGo5CMrso_T9VjXOFZO_oWe6ZdvqWLWjTFkJboEp_O_5Z7yAeoBiPoynKgaB1nASq"
  };

  const analysisBreakdown = [
    { label: 'Ink Composition', val: 98, status: 'Consistent', desc: 'Handwritten glyphs show uniform digital stroke pressure.', icon: 'colorize', color: 'primary' },
    { label: 'Paper Integrity', val: 84, status: 'Template Detected', desc: 'Background pattern matches known digital prescription templates.', icon: 'texture', color: 'secondary' },
    { label: 'Typography', val: 92, status: 'Stable', desc: 'Variable font weights are consistent with Dr. Akash Deep’s registry.', icon: 'font_download', color: 'tertiary' },
  ];

  return (
    <div className="text-on-surface font-body-md overflow-x-hidden min-h-screen relative bg-background">
      {/* Organic Background Decorative Blobs */}
      <div className="fixed top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary-container/20 rounded-full blur-[120px] pointer-events-none -z-10"></div>
      <div className="fixed bottom-[-5%] left-[-5%] w-[400px] h-[400px] bg-secondary-container/20 rounded-full blur-[100px] pointer-events-none -z-10"></div>

      <Sidebar user={user} />

      {/* Main Canvas */}
      <main className="ml-20 lg:ml-72 p-4 lg:p-gutter min-h-screen transition-all duration-300">
        {/* TopAppBar */}
        <header className="fixed top-0 right-0 left-20 lg:left-72 h-20 z-40 bg-white/40 backdrop-blur-xl border-b border-white/20 shadow-sm flex items-center justify-between px-4 lg:px-gutter transition-all duration-300">
          <div className="flex items-center gap-6 flex-1">
            <h2 className="hidden md:block font-headline-md text-headline-md text-primary font-bold">Forensic Node v2.1</h2>
            <div className="relative w-96 max-w-full">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40">search</span>
              <input 
                className="w-full bg-white/20 border-white/40 focus:ring-primary/20 focus:border-primary/40 rounded-full pl-12 pr-4 py-2 text-body-md transition-all outline-none" 
                placeholder="Search forensic records..." 
                type="text"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-surface-container-low/50 rounded-full transition-colors">
              <span className="material-symbols-outlined text-on-surface-variant">notifications</span>
            </button>
            <button className="p-2 hover:bg-surface-container-low/50 rounded-full transition-colors">
              <span className="material-symbols-outlined text-on-surface-variant">settings</span>
            </button>
            <div className="h-10 w-10 rounded-full overflow-hidden border-2 border-white shadow-sm ml-2">
              <img alt="User Avatar" className="w-full h-full object-cover" src={user.avatar} />
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="pt-24 max-w-[1280px] mx-auto space-y-gutter">
          {/* Header Section */}
          <div className="flex items-end justify-between mb-10">
            <div className="text-left">
              <div className="flex items-center gap-3 mb-2">
                <span className="px-3 py-1 bg-secondary-container/50 backdrop-blur-md border border-white/40 rounded-full text-secondary text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></div>
                  Active Diagnostic
                </span>
                <span className="text-on-surface-variant/50 text-label-sm font-bold uppercase">Report #MV-90284-F</span>
              </div>
              <h2 className="font-display-lg text-display-lg text-primary leading-tight">Forensic Analysis Report</h2>
              <p className="font-body-lg text-on-surface-variant/70 max-w-2xl mt-2">Detailed multi-layer validation of substrate integrity and typographic alignment for specimen **AK_2026_PRESC**.</p>
            </div>
            <div className="flex gap-3">
              <button className="px-6 py-3 rounded-full bg-white/40 border border-white/40 font-bold text-label-sm hover:bg-white transition-all flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">download</span>
                Export PDF
              </button>
              <button className="px-6 py-3 rounded-full bg-primary text-white font-bold text-label-sm shadow-lg hover:shadow-primary/20 transition-all flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">verified</span>
                Seal Verification
              </button>
            </div>
          </div>

          <div className="grid grid-cols-12 gap-card-gap">
            {/* Spatial Scan Preview */}
            <div className="col-span-12 lg:col-span-8 glass-card rounded-[40px] p-10 inner-glow relative overflow-hidden flex flex-col items-center">
              <div className="absolute top-6 left-10 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-secondary animate-pulse"></div>
                <span className="text-label-sm font-bold text-secondary uppercase tracking-widest">Spatial Scanning Active</span>
              </div>
              
              {/* Document Mockup with Animation */}
              <div className="relative mt-8 w-[340px] h-[460px] bg-white shadow-2xl rounded-sm border border-black/5 p-10 flex flex-col overflow-hidden group">
                {/* Header Mock */}
                <div className="border-b-2 border-primary/20 pb-4 mb-6">
                  <div className="h-5 w-40 bg-primary/20 rounded-full mb-3"></div>
                  <div className="h-3 w-56 bg-on-surface-variant/10 rounded-full"></div>
                </div>
                {/* Body Mock */}
                <div className="space-y-5">
                  <div className="h-3 w-full bg-on-surface-variant/5 rounded-full"></div>
                  <div className="h-3 w-4/5 bg-on-surface-variant/5 rounded-full"></div>
                  <div className="h-3 w-full bg-on-surface-variant/5 rounded-full"></div>
                  {/* Watermark Overlay */}
                  <div className="my-10 w-full h-16 border-4 border-dashed border-primary/10 rounded-2xl flex items-center justify-center -rotate-12">
                    <span className="text-[12px] text-primary/20 font-black uppercase tracking-[0.4em]">TEMPLATE</span>
                  </div>
                  <div className="h-3 w-3/4 bg-on-surface-variant/5 rounded-full"></div>
                </div>
                {/* Scanning Line */}
                <div className="animate-scan absolute left-0 w-full h-[3px] bg-primary shadow-[0_0_20px_rgba(103,85,140,1)] z-10"></div>
                <div className="absolute inset-0 bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
              </div>

              <div className="mt-10 grid grid-cols-3 gap-12 w-full border-t border-white/20 pt-10 text-left">
                <div className="hover:translate-y-[-2px] transition-transform">
                  <p className="text-[10px] text-on-surface-variant/60 uppercase font-bold tracking-widest mb-1">Subject / Patient</p>
                  <p className="font-bold text-on-surface text-lg">Aayush Kumar</p>
                </div>
                <div className="hover:translate-y-[-2px] transition-transform">
                  <p className="text-[10px] text-on-surface-variant/60 uppercase font-bold tracking-widest mb-1">Medical Lead</p>
                  <p className="font-bold text-on-surface text-lg">Dr. Akash Deep</p>
                </div>
                <div className="hover:translate-y-[-2px] transition-transform">
                  <p className="text-[10px] text-on-surface-variant/60 uppercase font-bold tracking-widest mb-1">Issuance Date</p>
                  <p className="font-bold text-on-surface text-lg">12 May 2026</p>
                </div>
              </div>
            </div>

            {/* Tamper Probability */}
            <div className="col-span-12 lg:col-span-4 glass-card rounded-[40px] p-10 inner-glow flex flex-col justify-center items-center text-center relative overflow-hidden">
              <div className="absolute -top-10 -right-10 w-40 h-40 bg-secondary-container/20 rounded-full blur-3xl"></div>
              <h3 className="font-headline-md text-headline-md text-primary mb-10 z-10">Neural Risk Score</h3>
              <div className="relative w-56 h-56 mb-10 z-10">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle className="text-surface-container-highest" cx="50" cy="50" fill="transparent" r="42" stroke="currentColor" strokeWidth="8"></circle>
                  <circle 
                    className="text-primary transition-all duration-1000 ease-out" 
                    cx="50" cy="50" fill="transparent" r="42" 
                    stroke="currentColor" strokeDasharray="263.9" strokeDashoffset={263.9 * (1 - 0.12)} 
                    strokeLinecap="round" strokeWidth="10" 
                  ></circle>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-5xl font-extrabold text-primary">12%</span>
                  <span className="text-label-sm text-on-surface-variant/60 uppercase font-bold tracking-widest mt-1">Suspicion Index</span>
                </div>
              </div>
              <div className="w-full p-6 bg-primary-container/10 rounded-3xl border border-primary/10 z-10">
                <p className="text-body-md text-primary font-medium">Anomaly detected in substrate background. 'TEMPLATE' watermark identifier suggests a non-unique digital issuance.</p>
              </div>
            </div>

            {/* Structural Breakdown Bento Cards */}
            {analysisBreakdown.map((item, i) => (
              <div key={i} className="col-span-12 md:col-span-4 glass-card rounded-[32px] p-8 inner-glow hover:translate-y-[-6px] transition-all duration-300 group text-left">
                <div className="flex items-center gap-4 mb-6">
                  <div className={`p-4 rounded-2xl bg-${item.color}-container/20 text-${item.color} group-hover:scale-110 transition-transform`}>
                    <span className="material-symbols-outlined text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>{item.icon}</span>
                  </div>
                  <h4 className="font-headline-md text-[22px] text-on-surface font-bold">{item.label}</h4>
                </div>
                <div className="space-y-5">
                  <div className="flex justify-between items-center text-label-sm">
                    <span className="text-on-surface-variant/70 font-bold uppercase tracking-wider">{item.status}</span>
                    <span className={`text-${item.color} font-bold text-lg`}>{item.val}%</span>
                  </div>
                  <div className="w-full h-2.5 bg-surface-container-highest rounded-full overflow-hidden">
                    <div 
                      className={`h-full bg-${item.color} rounded-full transition-all duration-1000 ease-out`} 
                      style={{ width: `${item.val}%` }}
                    ></div>
                  </div>
                  <p className="text-body-md text-on-surface-variant/80 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="pb-20"></div>
      </main>
    </div>
  );
}


