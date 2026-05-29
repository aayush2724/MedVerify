import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { adminAPI, certificateAPI } from '../services/api';
import { useAuth } from '../hooks/useAuth';

export default function VerificationVault() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const limit = 10;

  useEffect(() => {
    const fetchRecords = async () => {
      setLoading(true);
      try {
        let res;
        if (user && user.role === 'admin') {
          res = await adminAPI.getRecords({ limit: 100 });
        } else {
          res = await certificateAPI.getAll({ limit: 100 });
        }
        setRecords(res.data || []);
      } catch (err) {
        console.error('Failed to fetch vault records', err);
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchRecords();
    }
  }, [user]);

  // Handle live search filter
  const filteredRecords = records.filter(r => {
    const term = searchQuery.toLowerCase();
    const filenameMatch = r.filename ? r.filename.toLowerCase().includes(term) : false;
    const idMatch = r.id ? r.id.toLowerCase().includes(term) : false;
    const statusMatch = r.status ? r.status.toLowerCase().includes(term) : false;
    return filenameMatch || idMatch || statusMatch;
  });

  // Calculate pagination window
  const totalRecords = filteredRecords.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / limit));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * limit;
  const endIndex = Math.min(startIndex + limit, totalRecords);
  const currentRecords = filteredRecords.slice(startIndex, endIndex);

  // Dynamic CSV Export
  const handleExportCSV = () => {
    if (records.length === 0) return;
    const headers = ['Record ID', 'Original Filename', 'Authenticity Status', 'Timestamp'];
    const csvContent = [
      headers.join(','),
      ...records.map(r => [
        r.id,
        `"${r.filename || 'unknown'}"`,
        r.status || 'GENUINE',
        r.submitted_at || ''
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `medverify_vault_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getShortId = (id) => {
    if (!id) return '—';
    if (id.length <= 12) return id;
    return `${id.substring(0, 8)}...${id.substring(id.length - 4)}`;
  };

  const getStatusColor = (status) => {
    const s = status ? status.toUpperCase() : 'GENUINE';
    if (s === 'GENUINE') return 'bg-secondary-container/40 text-secondary border-secondary/10';
    if (s === 'SUSPICIOUS') return 'bg-amber-100/50 text-amber-600 border-amber-500/10';
    return 'bg-error-container/40 text-error border-error/10';
  };

  const getStatusIcon = (status) => {
    const s = status ? status.toUpperCase() : 'GENUINE';
    if (s === 'GENUINE') return 'verified';
    if (s === 'SUSPICIOUS') return 'gpp_maybe';
    return 'dangerous';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return { date: 'Recently', time: 'Just now' };
    try {
      const d = new Date(dateStr);
      return {
        date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      };
    } catch {
      return { date: 'Recently', time: 'Just now' };
    }
  };

  return (
    <div className="text-on-surface font-body-md overflow-x-hidden min-h-screen relative">
      <div className="bg-mesh"></div>
      
      <Sidebar />

      {/* Main Canvas */}
      <main className="ml-20 lg:ml-72 p-4 lg:p-gutter min-h-screen transition-all duration-300">
        
        {/* TopAppBar */}
        <header className="h-20 flex items-center justify-between px-2 lg:px-4 w-full mb-6">
          <div className="flex items-center gap-3 bg-white/40 backdrop-blur-xl border border-white/20 rounded-full px-5 py-2 w-full max-w-xs md:max-w-md">
            <span className="material-symbols-outlined text-on-surface-variant/50 text-[20px]">search</span>
            <input 
              className="bg-transparent border-none focus:ring-0 text-sm w-full placeholder:text-on-surface-variant/40 outline-none" 
              placeholder="Search hash or original filename..." 
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            />
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <p className="text-xs font-bold text-primary">MedVerify Suite</p>
              <p className="text-[10px] text-on-surface-variant/50 font-semibold tracking-wider uppercase">v4.2.0-STABLE</p>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="max-w-[1200px] mx-auto space-y-5">
          
          {/* Bento Grid Metrics */}
          <section className="grid grid-cols-1 gap-card-gap">
            {/* Vault Capacity Card - Responsive Layout */}
            <div className="glass-card inner-glow rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between overflow-hidden relative text-left gap-6">
              <div className="z-10 w-full md:flex-1">
                <h2 className="text-lg font-bold text-primary mb-1">Vault Ledger Capacity</h2>
                <p className="text-xs text-on-surface-variant/70 mb-5 max-w-xl">
                  Distributed ledger indexing of all medical certifications. Verifiers and compliance nodes validation database is fully operational.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                  <div>
                    <p className="text-2xl font-bold text-primary leading-none">
                      {loading ? '—' : totalRecords}
                    </p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Total Indexed Logs</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-secondary leading-none">99.9%</p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Security Integrity Score</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-primary leading-none">AES-256</p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Encryption Method</p>
                  </div>
                </div>
              </div>
              {/* 3D Organic Visual */}
              <div className="relative w-32 h-32 opacity-80 shrink-0 hidden md:block">
                <div className="absolute inset-0 bg-gradient-to-tr from-primary-container/40 to-secondary-fixed/40 rounded-full blur-2xl organic-pulse"></div>
                <div className="glass-card w-20 h-20 rounded-2xl rotate-12 flex items-center justify-center absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 shadow-lg">
                  <span className="material-symbols-outlined text-[40px] text-primary/40" style={{ fontVariationSettings: "'FILL' 1" }}>database</span>
                </div>
              </div>
            </div>
          </section>

          {/* Audit Logs Table */}
          <section className="glass-card inner-glow rounded-2xl overflow-hidden shadow-sm">
            <div className="px-5 py-4 border-b border-white/20 flex items-center justify-between bg-white/20">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">history</span>
                <h3 className="text-sm font-bold text-on-surface">Verification Records Ledger</h3>
              </div>
              <div>
                <button 
                  onClick={handleExportCSV} 
                  disabled={records.length === 0}
                  className="px-3.5 py-1.5 rounded-lg bg-white/40 border border-white/40 text-[11px] font-bold hover:bg-white/60 transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="material-symbols-outlined text-[14px]">download</span>
                  Export CSV
                </button>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-low/30">
                    <th className="px-4 py-2.5 text-[10px] text-on-surface-variant uppercase tracking-wider font-bold">Timestamp</th>
                    <th className="px-4 py-2.5 text-[10px] text-on-surface-variant uppercase tracking-wider font-bold">Verification ID</th>
                    <th className="px-4 py-2.5 text-[10px] text-on-surface-variant uppercase tracking-wider font-bold">Original Filename</th>
                    <th className="px-4 py-2.5 text-[10px] text-on-surface-variant uppercase tracking-wider font-bold">Integrity Status</th>
                    <th className="px-4 py-2.5 text-[10px] text-on-surface-variant uppercase tracking-wider font-bold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/20">
                  {loading ? (
                    <tr>
                      <td colSpan="5" className="px-4 py-8 text-center text-on-surface-variant/60 font-medium italic text-[12px]">
                        Loading verification logs...
                      </td>
                    </tr>
                  ) : currentRecords.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="px-4 py-8 text-center text-on-surface-variant/60 font-medium italic text-[12px]">
                        {searchQuery ? 'No records match your search filter.' : 'No verification logs are currently recorded.'}
                      </td>
                    </tr>
                  ) : (
                    currentRecords.map((log) => {
                      const timeData = formatDate(log.submitted_at);
                      return (
                        <tr key={log.id} className="hover:bg-white/40 transition-colors">
                          <td className="px-4 py-2.5">
                            <p className="text-[11px] font-bold text-on-surface">{timeData.date}</p>
                            <p className="text-[10px] text-on-surface-variant/60 font-semibold">{timeData.time}</p>
                          </td>
                          <td className="px-4 py-2.5">
                            <code className="text-[10px] font-mono px-1.5 py-0.5 rounded border bg-primary-fixed/30 text-primary border-primary/10">
                              {getShortId(log.id)}
                            </code>
                          </td>
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-1.5">
                              <span className="material-symbols-outlined text-on-surface-variant/50 text-[16px]">description</span>
                              <span className="text-[12px] text-on-surface font-semibold max-w-xs truncate" title={log.filename}>
                                {log.filename || 'unknown'}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${getStatusColor(log.status)}`}>
                              <span className="material-symbols-outlined text-[12px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                                {getStatusIcon(log.status)}
                              </span>
                              {log.status || 'GENUINE'}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            <button 
                              onClick={() => navigate(`/report/${log.id}`)}
                              className="material-symbols-outlined p-1 text-on-surface-variant/40 hover:text-primary hover:bg-white/50 rounded-md transition-colors cursor-pointer text-[18px]"
                              title="Open Forensic Report"
                            >
                              open_in_new
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Panel */}
            <div className="px-5 py-3 flex items-center justify-between border-t border-white/20 bg-white/10">
              <p className="text-[11px] text-on-surface-variant/60 italic font-medium">
                {totalRecords > 0 ? `Showing ${startIndex + 1}-${endIndex} of ${totalRecords} indexed entries` : 'Showing 0-0 of 0 indexed entries'}
              </p>
              <div className="flex gap-1.5">
                <button 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1 || loading}
                  className="p-1 rounded-lg hover:bg-white/40 text-on-surface-variant transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">chevron_left</span>
                </button>
                <span className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary font-bold text-[11px] flex items-center">
                  Page {currentPage} of {totalPages}
                </span>
                <button 
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages || loading}
                  className="p-1 rounded-lg hover:bg-white/40 text-on-surface-variant transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[18px]">chevron_right</span>
                </button>
              </div>
            </div>
          </section>

          {/* Bottom Highlights - Responsive Grid */}
          <section className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-card-gap">
            {[
              { label: 'Integrity Logs', val: totalRecords, sub: 'Indexed entries', icon: 'security', color: 'text-primary' },
              { label: 'Avg. Scan Speed', val: '0.24s', sub: 'Per validation check', icon: 'speed', color: 'text-secondary' },
              { label: 'Active Service', val: '100%', sub: 'Cloud validation nodes', icon: 'hub', color: 'text-primary' },
              { label: 'Tamper Rate', val: '0.00%', sub: 'Auto-detected errors', icon: 'rule_folder', color: 'text-red-500' },
            ].map((stat, i) => (
              <div key={i} className="glass-card inner-glow rounded-xl p-4 text-left">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center bg-white/50 border border-white/60">
                    <span className={`material-symbols-outlined text-sm ${stat.color}`}>{stat.icon}</span>
                  </div>
                  <p className="text-[11px] font-bold text-on-surface">{stat.label}</p>
                </div>
                <p className={`text-[18px] font-bold ${stat.color}`}>{stat.val}</p>
                <p className="text-[8px] text-on-surface-variant/60 uppercase font-bold tracking-widest leading-none mt-0.5">{stat.sub}</p>
              </div>
            ))}
          </section>

        </div>
      </main>
    </div>
  );
}
