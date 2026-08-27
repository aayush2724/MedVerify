import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import Sidebar from '../components/Sidebar';

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [avatar, setAvatar] = useState(user?.avatar || '');
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const roleLabels = {
    admin: 'System Admin',
    verifier: 'Verifier',
    viewer: 'Viewer',
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await updateProfile({ name, email, avatar });
      setSuccess('Profile updated successfully.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const selectAvatar = (url) => {
    setAvatar(url);
  };

  // Neutral inline-SVG avatars only — no external image hosts to break, and
  // no AI-generated faces implying a real person.
  const AVATAR_COLORS = [
    ['%23e8e0f0', '%237c5cbf'],  // lavender
    ['%23d9efdc', '%23326940'],  // mint
    ['%23fde8d9', '%23b45309'],  // amber
    ['%23dbeafe', '%231d4ed8'],  // blue
  ];
  const presetAvatars = AVATAR_COLORS.map(([bg, fg]) =>
    `data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"%3E%3Ccircle cx="20" cy="20" r="20" fill="${bg}"/%3E%3Ccircle cx="20" cy="16" r="7" fill="${fg}"/%3E%3Cellipse cx="20" cy="34" rx="12" ry="8" fill="${fg}"/%3E%3C/svg%3E`
  );

  return (
    <div className="text-on-surface font-body-md overflow-x-hidden min-h-screen relative">
      <div className="bg-mesh"></div>
      
      <Sidebar />

      <main className="ml-20 lg:ml-72 p-4 lg:p-gutter min-h-screen transition-all duration-300">
        {/* Header */}
        <header className="h-20 flex items-center justify-between px-2 lg:px-4 w-full mb-6">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate(-1)}
              className="w-10 h-10 rounded-full bg-white/40 backdrop-blur-xl border border-white/20 flex items-center justify-center text-on-surface hover:bg-white/60 active:scale-95 transition-all shadow-sm cursor-pointer"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
            </button>
            <div>
              <p className="text-[11px] uppercase tracking-[0.35em] text-on-surface-variant/60 mb-1">User Settings</p>
              <h1 className="font-display-sm text-primary leading-none">Identity Terminal</h1>
            </div>
          </div>
        </header>

        {/* Content Canvas */}
        <div className="max-w-2xl mx-auto mt-6">
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card rounded-[32px] p-8 lg:p-10 border-white/50 relative overflow-hidden"
          >
            <div className="mb-8">
              <h2 className="font-headline-md text-on-surface mb-2">Edit Identity Profile</h2>
              <p className="font-body-md text-on-surface-variant/70">Update your forensic credentials and customize your visual terminal details.</p>
            </div>

            <form onSubmit={handleSave} className="space-y-6">
              
              {/* Profile Avatar Selection */}
              <div className="space-y-3">
                <label className="block text-xs font-bold text-on-surface-variant/60 uppercase tracking-widest px-1">
                  Terminal Avatar
                </label>
                <div className="flex items-center gap-6">
                  <div className="w-20 h-20 rounded-full overflow-hidden border-4 border-white shadow-md shrink-0 bg-white">
                    <img 
                      alt="Selected Avatar" 
                      src={avatar || presetAvatars[2]}
                      onError={(e) => { e.currentTarget.src = presetAvatars[2]; }}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs text-on-surface-variant/60">Choose a terminal visual seed:</p>
                    <div className="flex gap-3">
                      {presetAvatars.map((url, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => selectAvatar(url)}
                          className={`w-10 h-10 rounded-full overflow-hidden border-2 cursor-pointer transition-all hover:scale-105 active:scale-95 ${avatar === url || (!avatar && i === 2) ? 'border-primary shadow-md scale-105' : 'border-white/50 opacity-60'}`}
                        >
                          <img 
                            src={url} 
                            alt={`Preset ${i}`} 
                            onError={(e) => { e.currentTarget.src = presetAvatars[2]; }}
                            className="w-full h-full object-cover bg-white" 
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Full Name Input */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-on-surface-variant/60 uppercase tracking-widest px-1">
                  Full Identity Name
                </label>
                <div className="relative group">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40 text-[20px] group-focus-within:text-primary transition-colors">person</span>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-white/50 border border-white/60 focus:border-primary/40 focus:ring-2 focus:ring-primary/10 rounded-2xl pl-12 pr-4 py-3.5 text-sm font-semibold text-on-surface outline-none transition-all"
                    placeholder="Enter your full name"
                  />
                </div>
              </div>

              {/* Email Address Input */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-on-surface-variant/60 uppercase tracking-widest px-1">
                  Identity Email
                </label>
                <div className="relative group">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40 text-[20px] group-focus-within:text-primary transition-colors">alternate_email</span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full bg-white/50 border border-white/60 focus:border-primary/40 focus:ring-2 focus:ring-primary/10 rounded-2xl pl-12 pr-4 py-3.5 text-sm font-semibold text-on-surface outline-none transition-all"
                    placeholder="name@medverify.dev"
                  />
                </div>
              </div>

              {/* Security Authorization Role (Disabled) */}
              <div className="space-y-2 opacity-80">
                <label className="block text-xs font-bold text-on-surface-variant/60 uppercase tracking-widest px-1">
                  Terminal Authorization Level
                </label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant/40 text-[20px]">verified_user</span>
                  <input
                    type="text"
                    disabled
                    value={roleLabels[user?.role] || 'Viewer'}
                    className="w-full bg-on-surface-variant/5 border border-white/20 rounded-2xl pl-12 pr-4 py-3.5 text-sm font-semibold text-on-surface-variant/60 outline-none cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Feedback messages */}
              {error && (
                <div className="p-4 bg-error-container/30 border border-error/20 rounded-2xl flex items-start gap-3">
                  <span className="material-symbols-outlined text-error text-[20px]">error</span>
                  <p className="text-xs text-error font-semibold">{error}</p>
                </div>
              )}

              {success && (
                <div className="p-4 bg-secondary-container/30 border border-secondary/20 rounded-2xl flex items-start gap-3">
                  <span className="material-symbols-outlined text-secondary text-[20px]">check_circle</span>
                  <p className="text-xs text-secondary font-semibold">{success}</p>
                </div>
              )}

              {/* Save Button */}
              <button
                type="submit"
                disabled={loading}
                className={`w-full py-4 rounded-2xl bg-gradient-to-r from-primary to-primary-container text-white font-bold text-sm shadow-lg shadow-primary/20 hover:scale-[1.01] active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer ${loading ? 'opacity-70 cursor-not-allowed' : ''}`}
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>Updating Profile...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[18px]">save</span>
                    <span>Save Changes</span>
                  </>
                )}
              </button>

            </form>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
