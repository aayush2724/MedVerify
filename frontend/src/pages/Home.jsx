import { Link } from 'react-router-dom';
import { Activity, History, LayoutDashboard, LogIn, ShieldCheck } from 'lucide-react';

import VerifyPage from './VerifyPage';
import { useAuth } from '../hooks/useAuth';

const Home = () => {
  const { user, logout } = useAuth();

  return (
    <main>
      <header className="border-b border-slate-200 bg-white">
        <div className="container mx-auto flex items-center justify-between py-4">
          <Link to="/" className="flex items-center gap-3 text-slate-900 no-underline">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
              <ShieldCheck size={24} />
            </span>
            <span className="text-xl font-bold">CertSentinel</span>
          </Link>

          <nav className="flex items-center gap-2">
            <Link className="btn btn-secondary" to="/history">
              <History size={18} /> History
            </Link>
            {user?.role === 'admin' && (
              <Link className="btn btn-secondary" to="/dashboard">
                <LayoutDashboard size={18} /> Dashboard
              </Link>
            )}
            {user ? (
              <button className="btn btn-outline" type="button" onClick={logout}>
                {user.email}
              </button>
            ) : (
              <Link className="btn btn-primary" to="/login">
                <LogIn size={18} /> Login
              </Link>
            )}
          </nav>
        </div>
      </header>

      <section className="py-10">
        <div className="container mx-auto mb-8 flex items-center gap-3 text-sm font-semibold text-blue-600">
          <Activity size={18} />
          Medical certificate verification
        </div>
        <VerifyPage />
      </section>
    </main>
  );
};

export default Home;
