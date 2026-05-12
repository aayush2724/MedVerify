import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Database, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react';

import { certificateAPI } from '../services/api';

const DashboardPage = () => {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    certificateAPI.getStats()
      .then((res) => setStats(res.data))
      .catch(() => setError('Unable to load dashboard stats'));
  }, []);

  return (
    <main className="container mx-auto max-w-6xl px-6 py-10">
      <Link to="/" className="mb-8 inline-flex items-center gap-2 font-bold text-slate-500 no-underline hover:text-blue-600">
        <ArrowLeft size={20} /> Back to verification
      </Link>

      <div className="mb-10">
        <h1 className="mb-2 text-4xl font-bold text-slate-900">Admin Dashboard</h1>
        <p className="text-slate-500">Operational snapshot of certificate verification activity.</p>
      </div>

      {error ? (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-6 font-semibold text-red-700">{error}</div>
      ) : !stats ? (
        <div className="flex items-center gap-3 text-slate-500">
          <Loader2 className="animate-spin" /> Loading dashboard...
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
          <MetricCard icon={Database} label="Total" value={stats.total ?? stats.total_verifications ?? 0} />
          <MetricCard icon={ShieldCheck} label="Genuine" value={stats.genuine_count ?? stats.by_status?.GENUINE ?? 0} />
          <MetricCard icon={ShieldAlert} label="Suspicious" value={stats.suspicious_count ?? stats.by_status?.SUSPICIOUS ?? 0} />
          <MetricCard icon={ShieldAlert} label="Fake" value={stats.fake_count ?? stats.by_status?.FAKE ?? 0} />
        </div>
      )}
    </main>
  );
};

const MetricCard = ({ icon: Icon, label, value }) => (
  <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
      <Icon size={24} />
    </div>
    <p className="text-sm font-semibold text-slate-500">{label}</p>
    <p className="text-3xl font-bold text-slate-900">{value}</p>
  </div>
);

export default DashboardPage;
