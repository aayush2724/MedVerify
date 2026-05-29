import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const DEFAULT_AVATAR_SVG = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Ccircle cx='20' cy='20' r='20' fill='%23e8e0f0'/%3E%3Ccircle cx='20' cy='16' r='7' fill='%237c5cbf'/%3E%3Cellipse cx='20' cy='34' rx='12' ry='8' fill='%237c5cbf'/%3E%3C/svg%3E`;

const ALL_NAV_ITEMS = [
  { path: '/', label: 'Launchpad', icon: 'home', roles: ['admin', 'verifier', 'viewer'] },
  { path: '/dashboard', label: 'Command Center', icon: 'dashboard', roles: ['admin'] },
  { path: '/analysis', label: 'Analysis Engine', icon: 'query_stats', roles: ['verifier'] },
  { path: '/forensic', label: 'Forensic Report', icon: 'description', roles: ['verifier'] },
  { path: '/vault', label: 'Verification Vault', icon: 'verified_user', roles: ['admin', 'verifier', 'viewer'] },
];

export default function Sidebar({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user: authUser } = useAuth();

  // Use session user or fallback to prop, then fallback to guest
  const rawUser = authUser || user || { name: 'Guest', role: 'viewer', avatar: null };

  // Map roles to correct system roles and profile information
  const getProfile = (u) => {
    // normalize raw role
    let normalizedRole = u.role ? u.role.toLowerCase() : 'viewer';
    if (normalizedRole.includes('admin')) normalizedRole = 'admin';
    else if (normalizedRole.includes('verify')) normalizedRole = 'verifier';
    else normalizedRole = 'viewer';

    if (normalizedRole === 'admin') {
      return {
        name: u.email === 'admin@certsentinel.dev' ? 'Dr. Julian Vance' : (u.name || 'System Admin'),
        role: 'admin',
        roleLabel: 'System Admin',
        avatar: u.avatar || 'https://lh3.googleusercontent.com/aida-public/AB6AXuCx9pEksSfepdb9zDTtfwPbbT7c_OplpA2ekaqkQHhzXAYiHSjppHiqphVSN2h3kDrQRbdWjgCohEZLOYh7KHfDJgIs_XOD_GbShfSOpy9a3O4T5rwt1rXgMSGbGkTUC6-Tdhc7plITdtolD_Yxp8DM7h0oYmCDdAWC_jry_s-jGvd2_8GuTn1au8FYpO1Ozezn_w4M12-COZndGo5CMrso_T9VjXOFZO_oWe6ZdvqWLWjTFkJboEp_O_5Z7yAeoBiPoynKgaB1nASq'
      };
    }
    if (normalizedRole === 'verifier') {
      return {
        name: u.email === 'verifier@certsentinel.dev' ? 'Dr. Sarah Jenkins' : (u.name || 'Hospital Verifier'),
        role: 'verifier',
        roleLabel: 'Verifier',
        avatar: u.avatar || 'https://lh3.googleusercontent.com/aida-public/AB6AXuDCtxurpFAiHFIk1wgdu08am-9cLnd_aDJyIUeBWfxE1sKl6qtcwjwtJUhq-A5n01bMAvUGEidYo_kWmvvTl_v2zcxoDEw9r5Kb3pdm8Ux9jLMMpurbCe7dOPapTSTaEoPzcvX8FApJEe7ktfqsFY3HTSdMjyoHGaGDbe4WCbzN6Q1XHYl0JJajBbze4oIphQ57g5i8AyaGCI_wR37k3XjuHTmZyTNCqrOnJw8J3gOvkkO4rHGSriQeFjmbeGePvZrJAMay_xb9iQ-G'
      };
    }
    return {
      name: u.name || 'Guest Auditor',
      role: 'viewer',
      roleLabel: 'Viewer',
      avatar: u.avatar
    };
  };

  const currentUser = getProfile(rawUser);
  const isActive = (path) => location.pathname === path;

  const navItems = ALL_NAV_ITEMS.filter(
    (item) => !item.roles || item.roles.includes(currentUser.role)
  );

  return (
    <nav className="print:hidden h-screen w-20 lg:w-72 fixed left-0 top-0 border-r border-white/40 bg-white/60 backdrop-blur-3xl flex flex-col p-4 lg:p-container-padding z-50 transition-all duration-300">
      <div onClick={() => navigate('/')} className="mb-12 flex items-center justify-center lg:justify-start gap-3 cursor-pointer hover:opacity-80 transition-opacity">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-primary-container flex items-center justify-center inner-glow shrink-0">
          <span className="material-symbols-outlined text-white" style={{ fontVariationSettings: "'FILL' 1" }}>security</span>
        </div>
        <div className="hidden lg:block text-left">
          <h1 className="font-headline-md text-headline-md font-bold tracking-tight text-primary">MedVerify</h1>
          <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60">Verification Suite</p>
        </div>
      </div>
      
      <div className="flex-1 space-y-2">
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center justify-center lg:justify-start gap-4 px-3 py-3 lg:px-4 lg:py-3 rounded-2xl transition-all duration-300 ${
                active 
                  ? 'bg-white/40 text-primary border-l-4 border-primary font-bold shadow-sm backdrop-blur-md' 
                  : 'text-on-surface-variant/70 hover:text-primary hover:bg-white/20'
              }`}
              title={item.label}
            >
              <span className="material-symbols-outlined shrink-0" style={{ fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}>
                {item.icon}
              </span>
              <span className="hidden lg:block font-label-sm text-label-sm">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-auto pt-8 border-t border-white/30">
        {currentUser.role === 'verifier' && (
          <button onClick={() => navigate('/')} className="w-full py-4 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all inner-glow flex items-center justify-center gap-2">
            <span className="material-symbols-outlined">add</span>
            <span className="hidden lg:inline">New Verification</span>
          </button>
        )}
        <div className="mt-6 flex items-center justify-center lg:justify-start gap-3 px-2">
          <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-white shadow-sm shrink-0">
            <img
              alt="User Avatar"
              src={currentUser.avatar || DEFAULT_AVATAR_SVG}
              onError={(e) => { e.currentTarget.src = DEFAULT_AVATAR_SVG; }}
            />
          </div>
          <div className="hidden lg:block text-left">
            <p className="text-sm font-bold text-on-surface">{currentUser.name}</p>
            <p className="text-[10px] text-on-surface-variant/60 font-bold uppercase">{currentUser.roleLabel}</p>
          </div>
        </div>
      </div>
    </nav>
  );
}
