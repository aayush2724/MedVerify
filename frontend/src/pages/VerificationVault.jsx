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
  const [previewRecord, setPreviewRecord] = useState(null);
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

  const statusCounts = records.reduce((acc, r) => {
    const key = (r.status || 'GENUINE').toUpperCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

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
      // If the string lacks a timezone offset or Z suffix, append 'Z' to treat it as UTC
      let parsedStr = dateStr;
      if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.match(/-\d{2}:\d{2}$/)) {
        parsedStr = dateStr + 'Z';
      }
      const d = new Date(parsedStr);
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
              <p className="text-xs font-bold text-primary">Verification Vault</p>
              <p className="text-[10px] text-on-surface-variant/50 font-semibold tracking-wider uppercase">Records Ledger</p>
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
                <h2 className="text-lg font-bold text-primary mb-1">Verification Vault</h2>
                <p className="text-xs text-on-surface-variant/70 mb-5 max-w-xl">
                  Every verification run is recorded here with its verdict, confidence and full audit trail.
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-5">
                  <div>
                    <p className="text-2xl font-bold text-primary leading-none">
                      {loading ? '—' : records.length}
                    </p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Total Records</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-secondary leading-none">
                      {loading ? '—' : statusCounts.GENUINE || 0}
                    </p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Genuine</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-amber-600 leading-none">
                      {loading ? '—' : statusCounts.SUSPICIOUS || 0}
                    </p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Suspicious</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-error leading-none">
                      {loading ? '—' : statusCounts.FAKE || 0}
                    </p>
                    <p className="text-[10px] text-on-surface-variant/50 font-bold uppercase tracking-wider mt-1">Fake / Altered</p>
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
                            <div className="flex items-center justify-end gap-1">
                              <button 
                                onClick={() => setPreviewRecord(log)}
                                className="material-symbols-outlined p-1 text-on-surface-variant/40 hover:text-primary hover:bg-white/50 rounded-md transition-colors cursor-pointer text-[18px]"
                                title="Preview Certificate File"
                              >
                                visibility
                              </button>
                              <button 
                                onClick={() => navigate(`/report/${log.id}`)}
                                className="material-symbols-outlined p-1 text-on-surface-variant/40 hover:text-primary hover:bg-white/50 rounded-md transition-colors cursor-pointer text-[18px]"
                                title="Open Forensic Report"
                              >
                                open_in_new
                              </button>
                            </div>
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


        </div>
      </main>

      {/* Dynamic Certificate Preview Modal */}
      {previewRecord && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="glass-card rounded-[32px] w-full max-w-4xl max-h-[85vh] flex flex-col border border-white/50 shadow-2xl relative overflow-hidden text-left bg-white/80">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-white/30 bg-white/40 flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-primary tracking-widest">Document Vault Preview</span>
                <h3 className="text-base font-bold text-on-surface truncate max-w-xl">{previewRecord.filename}</h3>
              </div>
              <button 
                onClick={() => setPreviewRecord(null)}
                className="w-8 h-8 rounded-full bg-white/60 border border-white/80 flex items-center justify-center hover:bg-error-container/20 hover:text-error transition-all cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 flex flex-col items-center justify-center min-h-[350px] bg-slate-950/5">
              {previewRecord.filename?.toLowerCase().endsWith('.pdf') ? (
                <iframe 
                  src={`/api/certificates/${previewRecord.id}/file?token=${localStorage.getItem('access_token')}`} 
                  className="w-full h-[50vh] rounded-2xl border-0 shadow-inner bg-white" 
                  title="PDF Certificate Preview"
                />
              ) : (
                <div className="relative group max-w-full max-h-[50vh] rounded-2xl overflow-hidden shadow-md bg-white border border-white/40">
                  <img 
                    src={`/api/certificates/${previewRecord.id}/file?token=${localStorage.getItem('access_token')}`} 
                    alt="Certificate Original Preview" 
                    className="max-w-full max-h-[50vh] object-contain block"
                    onError={(e) => {
                      e.currentTarget.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23faf8ff'/%3E%3Ctext x='50' y='50' text-anchor='middle' font-size='6' fill='%237c5cbf'%3EPreview Load Error%3C/text%3E%3C/svg%3E`;
                    }}
                  />
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-white/30 bg-white/40 flex items-center justify-between">
              <span className="text-[10px] font-bold text-on-surface-variant/60 uppercase">
                Verdict: <span className="underline">{previewRecord.status}</span>
              </span>
              <div className="flex gap-2">
                <a 
                  href={`/api/certificates/${previewRecord.id}/file?token=${localStorage.getItem('access_token')}`} 
                  download={previewRecord.filename}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-xl bg-white/60 border border-white text-on-surface font-bold text-xs shadow-sm hover:bg-primary-container/20 transition-all flex items-center gap-1.5 cursor-pointer decoration-none"
                >
                  <span className="material-symbols-outlined text-[16px]">download</span>
                  Download Original
                </a>
                <button 
                  onClick={() => { setPreviewRecord(null); navigate(`/report/${previewRecord.id}`); }}
                  className="px-4 py-2 rounded-xl bg-gradient-to-tr from-primary to-primary-container text-white font-bold text-xs shadow-md hover:shadow-lg transition-all flex items-center gap-1.5 cursor-pointer inner-glow"
                >
                  <span className="material-symbols-outlined text-[16px]">analytics</span>
                  View Diagnostics
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
