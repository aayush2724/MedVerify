import { Navigate } from 'react-router-dom';
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

  if (loading) return null;
  if (!user)   return <Navigate to="/login" replace />;
  if (!hasAccess(user.role, requiredRole)) return <Navigate to="/" replace />;

  return children;
}
