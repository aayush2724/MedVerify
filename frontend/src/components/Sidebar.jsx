import { useNavigate, useLocation } from 'react-router-dom';

const DEFAULT_AVATAR_SVG = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Ccircle cx='20' cy='20' r='20' fill='%23e8e0f0'/%3E%3Ccircle cx='20' cy='16' r='7' fill='%237c5cbf'/%3E%3Cellipse cx='20' cy='34' rx='12' ry='8' fill='%237c5cbf'/%3E%3C/svg%3E`;

const ALL_NAV_ITEMS = [
  { path: '/dashboard', label: 'Command Center', icon: 'dashboard', roles: ['admin'] },
  { path: '/analysis', label: 'Analysis Engine', icon: 'query_stats', roles: ['admin', 'verifier'] },
  { path: '/forensic', label: 'Forensic Report', icon: 'description', roles: ['admin', 'verifier'] },
  { path: '/vault', label: 'Verification Vault', icon: 'verified_user', roles: ['admin', 'verifier', 'viewer'] },
];

export default function Sidebar({ user }) {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const currentUser = user || { name: 'Guest', role: 'viewer', avatar: null };

  const navItems = ALL_NAV_ITEMS.filter(
    (item) => !item.roles || item.roles.includes(currentUser.role)
  );

  return (
    <nav className="h-screen w-72 fixed left-0 top-0 border-r border-white/40 bg-white/60 backdrop-blur-3xl flex flex-col p-container-padding z-50">
      <div className="mb-12 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-primary-container flex items-center justify-center inner-glow">
          <span className="material-symbols-outlined text-white" style={{ fontVariationSettings: "'FILL' 1" }}>security</span>
        </div>
        <div>
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
              className={`w-full flex items-center gap-4 px-4 py-3 rounded-2xl transition-all duration-300 ${
                active 
                  ? 'bg-white/40 text-primary border-l-4 border-primary font-bold shadow-sm backdrop-blur-md' 
                  : 'text-on-surface-variant/70 hover:text-primary hover:bg-white/20'
              }`}
            >
              <span className="material-symbols-outlined" style={{ fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}>
                {item.icon}
              </span>
              <span className="font-label-sm text-label-sm">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-auto pt-8 border-t border-white/30">
        <button className="w-full py-4 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all inner-glow flex items-center justify-center gap-2">
          <span className="material-symbols-outlined">add</span>
          New Verification
        </button>
        <div className="mt-6 flex items-center gap-3 px-2">
          <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-white shadow-sm">
            <img
              alt="User Avatar"
              src={currentUser.avatar || DEFAULT_AVATAR_SVG}
              onError={(e) => { e.currentTarget.src = DEFAULT_AVATAR_SVG; }}
            />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-on-surface">{currentUser.name}</p>
            <p className="text-[10px] text-on-surface-variant/60 font-bold uppercase">{currentUser.role}</p>
          </div>
        </div>
      </div>
    </nav>
  );
}



