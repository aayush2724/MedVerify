import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

export default function AnalysisEngine() {
  const navigate = useNavigate();
  const user = {
    name: "Dr. Julian Vance",
    role: "Lead Administrator",
    avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuCx9pEksSfepdb9zDTtfwPbbT7c_OplpA2ekaqkQHhzXAYiHSjppHiqphVSN2h3kDrQRbdWjgCohEZLOYh7KHfDJgIs_XOD_GbShfSOpy9a3O4T5rwt1rXgMSGbGkTUC6-Tdhc7plITdtolD_Yxp8DM7h0oYmCDdAWC_jry_s-jGvd2_8GuTn1au8FYpO1Ozezn_w4M12-COZndGo5CMrso_T9VjXOFZO_oWe6ZdvqWLWjTFkJboEp_O_5Z7yAeoBiPoynKgaB1nASq"
  };

  const queueItems = [
    { id: 'SPECIMEN_0092-A', origin: 'North Cluster Lab', size: '2.4MB', time: '2m ago', priority: 'Priority', progress: 72, icon: "https://lh3.googleusercontent.com/aida-public/AB6AXuDCtxurpFAiHFIk1wgdu08am-9cLnd_aDJyIUeBWfxE1sKl6qtcwjwtJUhq-A5n01bMAvUGEidYo_kWmvvTl_v2zcxoDEw9r5Kb3pdm8Ux9jLMMpurbCe7dOPapTSTaEoPzcvX8FApJEe7ktfqsFY3HTSdMjyoHGaGDbe4WCbzN6Q1XHYl0JJajBbze4oIphQ57g5i8AyaGCI_wR37k3XjuHTmZyTNCqrOnJw8J3gOvkkO4rHGSriQeFjmbeGePvZrJAMay_xb9iQ-G" },
    { id: 'SPECIMEN_0088-C', origin: 'Mobile Unit 4', size: '1.1MB', time: '15m ago', priority: 'Standard', progress: 0, icon: "https://lh3.googleusercontent.com/aida-public/AB6AXuBF77tpuAl4tIyBWnSfP3qaMzPiv1V2fEJqrmLp6EmUnC1VUC27PeD1cWTfQE0pIhvuhjZQireHul0kH7bOzf6U5FKsWvcXmnsW_50szxEpiQj6_zoXcyAkp1avk_a6SqME357Vg_TklL-V24qoFEQu9-QNRSmPksTjitNiC4Mb1GwePM2GFovlBZ1LFLjsmB7g6JJF0blo8tHoIyBKIgpb7wHtiytP31kAY54jFCAk8plvX8TW72F--jA_W9azMfVp8SlDIjHHdUIm" },
    { id: 'GEN-CERT_FINAL_X', origin: 'External Archive', size: '14.5MB', time: '1h ago', priority: 'Verification Delay', progress: 44, icon: "https://lh3.googleusercontent.com/aida-public/AB6AXuDfCmvxQVEtVwcv84i_5pw4qdns4LZGILRQ-kIzKWXcRFwedMuQDfnuO1VuK7Ej8jX_7Rork-AzSieyqntwhsTlw-VeVygoF9NmEjOfumurhylRIQL_bXYFUWenCUow2U8nZ_Te6IB3FXWLeRI6vQ_-JXQfOBB4bBx18Ubjg4vHDV5MN3u4qNUlyTPqVu0u4ZS-pWUZwnymYSSanfG6CadgWlfxEP2S5PN00Sij2MCASJHo93Sp_okN75pVCCZbkQ4ODfIsqBkMOH8Y", status: 'Halted' },
  ];

  return (
    <div className="text-on-surface overflow-x-hidden relative min-h-screen">
      <Sidebar user={user} />

      {/* Main Content */}
      <main className="ml-20 lg:ml-72 p-4 lg:p-gutter min-h-screen transition-all duration-300">
        {/* TopAppBar */}
        <header className="flex items-center justify-between h-20 mb-8">
          <div className="flex-1 max-w-xl">
            <div className="relative group">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/50">search</span>
              <input 
                className="w-full pl-12 pr-4 py-3 rounded-full border-none bg-white/40 backdrop-blur-xl focus:ring-2 focus:ring-primary-container/50 transition-all font-body-md outline-none" 
                placeholder="Search specimens or certificates..." 
                type="text"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="w-10 h-10 flex items-center justify-center rounded-full bg-white/40 backdrop-blur-xl hover:bg-white/60 transition-colors">
              <span className="material-symbols-outlined text-on-surface-variant">notifications</span>
            </button>
            <button className="w-10 h-10 flex items-center justify-center rounded-full bg-white/40 backdrop-blur-xl hover:bg-white/60 transition-colors">
              <span className="material-symbols-outlined text-on-surface-variant">settings</span>
            </button>
            <div className="h-6 w-[1px] bg-on-surface-variant/20 mx-2"></div>
            <div className="flex items-center gap-2">
              <span className="font-label-sm text-on-surface">MedVerify Suite</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-bold uppercase">Pro</span>
            </div>
          </div>
        </header>

        {/* Page Header */}
        <div className="mb-10 text-left">
          <h2 className="font-display-lg text-display-lg text-primary tracking-tight">Analysis Engine</h2>
          <p className="font-body-lg text-on-surface-variant/70">Autonomous specimen ingestion and neural certificate validation.</p>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-12 gap-card-gap">
          {/* Ingest Zone (Main Action) */}
          <div className="col-span-8 glass-card rounded-[40px] p-container-padding flex flex-col items-center justify-center text-center relative overflow-hidden group min-h-[500px]">
            {/* Decorative organic shapes */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-primary-container/20 rounded-full blur-3xl"></div>
            <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-secondary-container/20 rounded-full blur-3xl"></div>
            
            <div className="relative z-10 w-full max-w-md">
              <div className="mb-8 p-12 rounded-[48px] border-2 border-dashed border-primary-container/40 bg-white/20 flex flex-col items-center group-hover:bg-white/40 transition-all duration-500">
                <div className="w-24 h-24 mb-6 rounded-full bg-gradient-to-br from-white to-primary-container/20 flex items-center justify-center shadow-inner">
                  <span className="material-symbols-outlined text-5xl text-primary" style={{ fontVariationSettings: "'wght' 200" }}>upload_file</span>
                </div>
                <h3 className="font-headline-md text-headline-md text-on-surface mb-2">Drop Specimen Here</h3>
                <p className="font-body-md text-on-surface-variant/60">Supports .PDF, .XRAY, .GENOM, and encrypted certificate bundles.</p>
              </div>
              <button onClick={() => navigate('/')} className="px-12 py-5 rounded-full bg-gradient-to-r from-primary-container to-primary text-white font-bold text-lg shadow-2xl hover:scale-105 active:scale-95 transition-all duration-300 flex items-center justify-center gap-4 mx-auto border-t border-white/30 inner-glow">
                <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
                <span>Ingest Certificate</span>
              </button>
              <p className="mt-6 text-label-sm text-on-surface-variant/40 italic">Secure end-to-end neural encryption active.</p>
            </div>
          </div>

          {/* Real-time Metrics */}
          <div className="col-span-4 flex flex-col gap-card-gap">
            {/* Neural Confidence */}
            <div className="glass-card rounded-[32px] p-gutter inner-glow text-left">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <p className="text-label-sm text-on-surface-variant/70 uppercase">Neural Confidence</p>
                  <h4 className="text-3xl font-bold text-primary">98.4%</h4>
                </div>
                <div className="p-3 rounded-2xl bg-primary-container/20">
                  <span className="material-symbols-outlined text-primary">psychology</span>
                </div>
              </div>
              <div className="h-4 organic-progress mb-2">
                <div className="organic-progress-fill w-[98.4%]"></div>
              </div>
              <p className="text-[12px] text-on-surface-variant/60 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px] text-secondary">check_circle</span>
                Exceeds safety threshold by 2.4%
              </p>
            </div>

            {/* Genetic Fidelity */}
            <div className="glass-card rounded-[32px] p-gutter inner-glow text-left">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <p className="text-label-sm text-on-surface-variant/70 uppercase">Genetic Fidelity</p>
                  <h4 className="text-3xl font-bold text-secondary">89.2%</h4>
                </div>
                <div className="p-3 rounded-2xl bg-secondary-container/20">
                  <span className="material-symbols-outlined text-secondary">genetics</span>
                </div>
              </div>
              <div className="h-4 organic-progress mb-2 bg-on-surface-variant/5">
                <div className="h-full rounded-full bg-gradient-to-r from-secondary-container to-secondary w-[89.2%] shadow-[0_0_15px_rgba(50,105,64,0.3)]"></div>
              </div>
              <p className="text-[12px] text-on-surface-variant/60 flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px] text-primary">info</span>
                Minor sequence variance detected
              </p>
            </div>

            {/* System Load */}
            <div className="glass-card rounded-[32px] p-gutter flex items-center gap-4 text-left">
              <div className="w-12 h-12 rounded-full border-4 border-primary-container/20 border-t-primary animate-spin"></div>
              <div>
                <p className="font-label-sm text-on-surface font-bold">Neural Processing</p>
                <p className="text-label-sm text-on-surface-variant/60">Cluster Alpha: Active</p>
              </div>
            </div>
          </div>

          {/* Analysis Queue */}
          <div className="col-span-12 glass-card rounded-[40px] p-container-padding">
            <div className="flex items-center justify-between mb-8">
              <h3 className="font-headline-md text-headline-md text-on-surface">Live Analysis Queue</h3>
              <div className="flex gap-2">
                <button className="px-4 py-2 rounded-full bg-white/40 border border-white/40 text-label-sm hover:bg-white transition-colors">All Specimens</button>
                <button className="px-4 py-2 rounded-full bg-primary text-white text-label-sm shadow-md font-bold">Processing (4)</button>
              </div>
            </div>
            
            <div className="space-y-4">
              {queueItems.map((item, index) => (
                <div key={index} className="flex items-center gap-6 p-4 rounded-3xl bg-white/30 hover:bg-white/50 transition-all border border-transparent hover:border-white/40 group text-left">
                  <div className="w-14 h-14 rounded-2xl bg-surface-container-highest flex items-center justify-center overflow-hidden">
                    <img alt="Specimen Icon" className={`w-10 h-10 ${item.progress === 0 ? 'opacity-60' : ''}`} src={item.icon} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h5 className="font-bold text-on-surface">{item.id}</h5>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        item.status === 'Halted' ? 'bg-error-container text-error' : 
                        item.priority === 'Priority' ? 'bg-primary-container/20 text-primary' : 'bg-secondary-container/20 text-secondary'
                      }`}>
                        {item.status || item.priority}
                      </span>
                    </div>
                    <p className="text-label-sm text-on-surface-variant/60">Origin: {item.origin} • Size: {item.size} • Ingested: {item.time}</p>
                  </div>
                  <div className="w-48">
                    <div className="flex justify-between mb-1">
                      <span className={`text-[11px] font-bold ${item.status === 'Halted' ? 'text-error' : item.progress === 0 ? 'text-on-surface-variant/40' : 'text-primary'}`}>
                        {item.status || (item.progress === 0 ? 'In Queue' : 'Processing')}
                      </span>
                      <span className={`text-[11px] font-bold ${item.status === 'Halted' ? 'text-error' : item.progress === 0 ? 'text-on-surface-variant/40' : 'text-primary'}`}>{item.progress}%</span>
                    </div>
                    <div className={`h-2 organic-progress ${item.status === 'Halted' ? 'bg-error/10' : ''}`}>
                      <div 
                        className={`${item.status === 'Halted' ? 'h-full rounded-full bg-error' : 'organic-progress-fill'} transition-all duration-1000 ease-out`} 
                        style={{ width: `${item.progress}%`, boxShadow: item.status === 'Halted' ? '0 0 15px rgba(186,26,26,0.3)' : undefined }}
                      ></div>
                    </div>
                  </div>
                  <button className="p-2 rounded-xl text-on-surface-variant/40 hover:text-primary transition-colors">
                    <span className="material-symbols-outlined">more_vert</span>
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Floating Action Button */}
        <button className="fixed bottom-12 right-12 w-16 h-16 rounded-3xl bg-primary text-white shadow-2xl hover:scale-110 active:scale-90 transition-all duration-300 flex items-center justify-center group z-40 border-t border-white/20">
          <span className="material-symbols-outlined text-3xl group-hover:rotate-90 transition-transform duration-500">add</span>
        </button>
      </main>

      {/* Background 3D Blobs */}
      <div className="fixed top-0 left-0 w-full h-full -z-10 pointer-events-none opacity-40 overflow-hidden">
        <div className="absolute top-[10%] right-[5%] w-96 h-96 bg-primary-container rounded-full blur-[120px] mix-blend-multiply"></div>
        <div className="absolute bottom-[20%] left-[10%] w-[500px] h-[500px] bg-secondary-container rounded-full blur-[150px] mix-blend-multiply"></div>
        <div className="absolute top-[40%] left-[30%] w-72 h-72 bg-tertiary-fixed rounded-full blur-[100px] mix-blend-multiply"></div>
      </div>
    </div>
  );
}


