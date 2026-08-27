import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

const ROLE_HIERARCHY = { admin: 3, verifier: 2, viewer: 1 };

function hasAccess(userRole, requiredRole) {
  if (!requiredRole) return true;
  const allowed = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
  const userLevel = ROLE_HIERARCHY[userRole] ?? 0;
  return allowed.some((r) => userLevel >= (ROLE_HIERARCHY[r] ?? Infinity));
}

export default function ProtectedRoute({ children, requiredRole = null }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
      </div>
    );
  }
  // Carry the attempted location so Login can return the user here afterwards.
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!hasAccess(user.role, requiredRole)) return <Navigate to="/" replace />;

  return children;
}
