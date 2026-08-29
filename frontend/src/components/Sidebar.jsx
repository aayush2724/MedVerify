import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const ALL_NAV_ITEMS = [
  { path: '/', label: 'Launchpad', icon: 'home', roles: ['admin', 'verifier', 'viewer'] },
  { path: '/dashboard', label: 'Command Center', icon: 'monitoring', roles: ['admin'] },
  { path: '/analysis', label: 'Analysis Engine', icon: 'query_stats', roles: ['admin', 'verifier'] },
  { path: '/vault', label: 'Verification Vault', icon: 'verified_user', roles: ['admin', 'verifier', 'viewer'] },
  { path: '/medications', label: 'Medication Safety', icon: 'pill', roles: ['admin', 'verifier', 'viewer'] },
  { path: '/prescription-check', label: 'Prescription Check', icon: 'clinical_notes', roles: ['admin', 'verifier', 'viewer'] },
];

const ROLE_LABELS = { admin: 'System Admin', verifier: 'Verifier', viewer: 'Viewer' };

/** Deterministic initials avatar — no external image URLs to break or mislead. */
function InitialsAvatar({ name, email }) {
  const source = (name || email || '?').trim();
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  const initials = parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : source.slice(0, 2).toUpperCase();
  return (
    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shrink-0 shadow-sm">
      <span className="text-white text-sm font-bold tracking-wide">{initials}</span>
    </div>
  );
}

export default function Sidebar({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user: authUser, logout } = useAuth();

  const rawUser = authUser || user || { role: 'viewer' };
  const role = ['admin', 'verifier', 'viewer'].includes((rawUser.role || '').toLowerCase())
    ? rawUser.role.toLowerCase()
    : 'viewer';
  const displayName = rawUser.name || rawUser.email || 'Guest';

  const isActive = (path) =>
    location.pathname === path ||
    (path !== '/' && location.pathname.startsWith(`${path}/`));

  const navItems = ALL_NAV_ITEMS.filter((item) => item.roles.includes(role));

  return (
    <nav className="print:hidden h-screen w-20 lg:w-72 fixed left-0 top-0 border-r border-outline-variant/20 bg-white/70 backdrop-blur-2xl flex flex-col p-4 lg:p-6 z-50 transition-all duration-300">
      {/* Brand */}
      <div
        onClick={() => navigate('/')}
        className="mb-10 flex items-center justify-center lg:justify-start gap-3 cursor-pointer hover:opacity-80 transition-opacity"
      >
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-primary-container flex items-center justify-center shrink-0 shadow-md shadow-primary/20">
          <span className="material-symbols-outlined text-white text-[22px]" style={{ fontVariationSettings: "'FILL' 1" }}>
            shield_with_heart
          </span>
        </div>
        <div className="hidden lg:block text-left">
          <h1 className="text-lg font-bold tracking-tight text-on-surface leading-none">MedVerify</h1>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-on-surface-variant/50 mt-1">
            Verification Suite
          </p>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 space-y-1">
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center justify-center lg:justify-start gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 text-sm ${
                active
                  ? 'bg-primary/10 text-primary font-bold'
                  : 'text-on-surface-variant/70 font-medium hover:text-on-surface hover:bg-surface-container-low'
              }`}
              title={item.label}
            >
              <span
                className={`material-symbols-outlined text-[22px] shrink-0 ${active ? '' : ''}`}
                style={{ fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}
              >
                {item.icon}
              </span>
              <span className="hidden lg:block">{item.label}</span>
              {active && <span className="hidden lg:block ml-auto w-1.5 h-1.5 rounded-full bg-primary" />}
            </button>
          );
        })}
      </div>

      {/* Primary action */}
      {(role === 'verifier' || role === 'admin') && location.pathname !== '/analysis' && (
        <button
          onClick={() => navigate('/analysis')}
          className="mb-4 w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-bold shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/30 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-[20px]">add</span>
          <span className="hidden lg:inline">New Verification</span>
        </button>
      )}

      {/* User footer */}
      <div className="pt-4 border-t border-outline-variant/20 flex flex-col lg:flex-row items-center lg:justify-between gap-3 lg:gap-2">
        <div
          onClick={() => navigate('/profile')}
          className="flex items-center gap-3 cursor-pointer hover:opacity-80 active:scale-[0.98] transition-all min-w-0"
          title="Edit Profile"
        >
          {rawUser.avatar ? (
            <div className="w-10 h-10 rounded-full overflow-hidden shrink-0 border border-outline-variant/30">
              <img
                alt=""
                src={rawUser.avatar}
                className="w-full h-full object-cover"
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            </div>
          ) : (
            <InitialsAvatar name={rawUser.name} email={rawUser.email} />
          )}
          <div className="hidden lg:block text-left min-w-0">
            <p className="text-sm font-bold text-on-surface truncate max-w-[120px]">{displayName}</p>
            <p className="text-[10px] text-on-surface-variant/60 font-semibold uppercase tracking-wider">
              {ROLE_LABELS[role]}
            </p>
          </div>
        </div>
        <button
          onClick={() => logout()}
          className="p-2 rounded-lg hover:bg-error-container/20 transition-colors group shrink-0"
          title="Log out"
        >
          <span className="material-symbols-outlined text-[20px] text-on-surface-variant/50 group-hover:text-error transition-colors">
            logout
          </span>
        </button>
      </div>
    </nav>
  );
}
