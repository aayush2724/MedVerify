import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await login(email, password);
      // Return to the page that redirected here; otherwise land on the
      // role's own console — /dashboard is admin-only and would bounce
      // everyone else straight back out.
      const from = location.state?.from?.pathname;
      const roleHome = { admin: '/dashboard', verifier: '/analysis', viewer: '/vault' };
      navigate(from || roleHome[data?.user?.role] || '/vault', { replace: true });
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 relative overflow-hidden">
      {/* Decorative Elements */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px] -mr-64 -mt-64"></div>
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-secondary/5 rounded-full blur-[100px] -ml-32 -mb-32"></div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="w-full max-w-[420px] bg-surface border border-outline-variant/30 rounded-3xl p-10 shadow-xl relative z-10"
      >
        <div className="mb-10">
          <div 
            onClick={() => navigate('/')} 
            className="inline-flex items-center gap-3 mb-6 cursor-pointer hover:opacity-80 active:scale-95 transition-all"
            title="Go to Home"
          >
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
              <span className="material-symbols-outlined text-on-primary text-[24px]" style={{fontVariationSettings: "'FILL' 1"}}>shield_with_heart</span>
            </div>
            <span className="font-title-lg text-primary font-bold tracking-tight">MedVerify</span>
          </div>
          
          <h1 className="font-display-sm text-text-primary mb-2">Welcome Back</h1>
          <p className="font-body-md text-text-tertiary">Access your forensic verification dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="block font-label-sm text-text-tertiary uppercase tracking-widest px-1">
              Internal Identity
            </label>
            <div className="relative group">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary text-[20px] group-focus-within:text-primary transition-colors">alternate_email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-surface-container-low border border-outline-variant/30 rounded-2xl pl-12 pr-4 py-3.5 font-body-md text-text-primary focus:ring-2 focus:ring-primary/20 focus:border-primary/30 outline-none transition-all"
                placeholder="admin@medverify.dev"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="block font-label-sm text-text-tertiary uppercase tracking-widest px-1">
              Security Key
            </label>
            <div className="relative group">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary text-[20px] group-focus-within:text-primary transition-colors">lock</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-surface-container-low border border-outline-variant/30 rounded-2xl pl-12 pr-4 py-3.5 font-body-md text-text-primary focus:ring-2 focus:ring-primary/20 focus:border-primary/30 outline-none transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-4 bg-error/5 border border-error/20 rounded-2xl flex items-start gap-3"
            >
              <span className="material-symbols-outlined text-error text-[20px]">error</span>
              <p className="font-body-sm text-error leading-relaxed">{error}</p>
            </motion.div>
          )}

          <motion.button
            type="submit"
            disabled={loading}
            whileHover={!loading ? { scale: 1.01 } : {}}
            whileTap={!loading ? { scale: 0.98 } : {}}
            className={`w-full bg-primary text-on-primary py-4 rounded-2xl font-label-lg shadow-lg shadow-primary/20 transition-all ${loading ? 'opacity-70 cursor-not-allowed' : 'hover:bg-primary/95 hover:shadow-xl active:scale-95'}`}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Establishing Secure Session...</span>
              </div>
            ) : 'Access Terminal'}
          </motion.button>
        </form>

        <div className="mt-10 pt-8 border-t border-outline-variant/20">
          <p className="font-label-sm text-text-tertiary text-center leading-relaxed mb-4">
            Secure forensic environment. Authorized access only.
          </p>
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-2xl p-4 space-y-2 text-left font-body-sm">
            <p className="font-bold text-text-secondary text-[11px] uppercase tracking-wider mb-1">Demo Accounts</p>
            <div className="flex justify-between text-xs text-text-tertiary">
              <span>Admin:</span>
              <span className="font-bold text-primary">admin@medverify.dev</span>
            </div>
            <div className="flex justify-between text-xs text-text-tertiary">
              <span>Verifier:</span>
              <span className="font-bold text-primary">verifier@medverify.dev</span>
            </div>
            <div className="flex justify-between text-xs text-text-tertiary">
              <span>Viewer:</span>
              <span className="font-bold text-primary">viewer@medverify.dev</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
