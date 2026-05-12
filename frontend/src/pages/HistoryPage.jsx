import { useMemo, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Calendar, FileText, ChevronRight, Download, Loader2 } from 'lucide-react';
import { getRecords } from '../services/api';

const statusColors = {
  GENUINE: 'bg-emerald-100 text-emerald-700',
  SUSPICIOUS: 'bg-amber-100 text-amber-700',
  FAKE: 'bg-rose-100 text-rose-700',
};

const HistoryPage = () => {
  const [records, setRecords] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        const { data } = await getRecords();
        setRecords(data);
      } catch (err) {
        console.error('Failed to fetch records', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecords();
  }, []);

  const filtered = useMemo(() => {
    let result = records;
    if (searchTerm) {
      result = result.filter(r => 
        r.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.id.toString().includes(searchTerm)
      );
    }
    if (statusFilter !== 'ALL') {
      result = result.filter(r => r.status === statusFilter);
    }
    return result;
  }, [searchTerm, statusFilter, records]);

  const exportToCSV = () => {
    const headers = ['ID', 'Filename', 'Status', 'Confidence', 'Submitted At'];
    const data = filtered.map(r => [r.id, r.filename, r.status, r.confidence, r.submitted_at]);
    const csvContent = [headers, ...data].map(e => e.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'CertSentinel_History.csv';
    link.click();
  };

  return (
    <div className="container mx-auto px-6 max-w-6xl">
      <div className="flex justify-between items-end mb-12">
        <div>
          <h2 className="text-4xl font-bold text-slate-900 mb-2">Verification Audit Log</h2>
          <p className="text-slate-500">Review and manage all historical document verifications.</p>
        </div>
        <button onClick={exportToCSV} className="btn btn-secondary gap-2">
          <Download size={18} /> Export CSV
        </button>
      </div>

      <div className="bg-white rounded-3xl border border-slate-100 shadow-xl overflow-hidden">
        <div className="p-6 border-b bg-slate-50 flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="text" 
              placeholder="Search by filename or ID..." 
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="flex gap-4">
            <div className="relative">
              <Filter className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <select 
                className="pl-12 pr-10 py-3 rounded-xl border border-slate-200 appearance-none bg-white font-semibold text-slate-600 focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="GENUINE">Genuine</option>
                <option value="SUSPICIOUS">Suspicious</option>
                <option value="FAKE">Fake</option>
              </select>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 text-slate-400 text-xs font-bold uppercase tracking-widest border-b">
                <th className="px-8 py-4 text-left">Record ID</th>
                <th className="px-8 py-4 text-left">Document</th>
                <th className="px-8 py-4 text-left">Status</th>
                <th className="px-8 py-4 text-left">Confidence</th>
                <th className="px-8 py-4 text-left">Date</th>
                <th className="px-8 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="px-8 py-12 text-center text-slate-400 font-medium">
                    <Loader2 className="animate-spin mx-auto mb-2" />
                    Loading audit records...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-8 py-12 text-center text-slate-400 font-medium">
                    No matching records found.
                  </td>
                </tr>
              ) : (
                filtered.map((record) => (
                  <tr key={record.id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-8 py-5 font-mono text-xs text-slate-400">#{record.id}</td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center text-slate-500 group-hover:bg-white transition-colors">
                          <FileText size={20} />
                        </div>
                        <span className="font-semibold text-slate-700">{record.filename}</span>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${statusColors[record.status]}`}>
                        {record.status}
                      </span>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <div 
                            className="bg-primary h-full" 
                            style={{ width: `${Math.round(record.confidence * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-slate-600">{Math.round(record.confidence * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-8 py-5 text-sm text-slate-500">
                      <div className="flex items-center gap-2">
                        <Calendar size={14} />
                        {new Date(record.submitted_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <Link 
                        to={`/report/${record.id}`} 
                        className="inline-flex items-center gap-2 text-primary font-bold text-sm hover:underline"
                      >
                        Details <ChevronRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
