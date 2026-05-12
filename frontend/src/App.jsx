import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Suspense, lazy } from 'react';
import { AuthProvider } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';

const Home = lazy(() => import('./pages/Home'));
const Report = lazy(() => import('./pages/Report'));
const Login = lazy(() => import('./pages/Login'));
const History = lazy(() => import('./pages/History'));
const CommandCenter = lazy(() => import('./pages/CommandCenter'));
const AnalysisEngine = lazy(() => import('./pages/AnalysisEngine'));
const ForensicReport = lazy(() => import('./pages/ForensicReport'));
const VerificationVault = lazy(() => import('./pages/VerificationVault'));

const pageVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.22, ease: 'easeOut' } },
  exit:    { opacity: 0, transition: { duration: 0.15, ease: 'easeIn' } },
};

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={
          <motion.div {...pageVariants}>
            <Suspense fallback={<PageLoader />}>
              <Home />
            </Suspense>
          </motion.div>
        } />
        <Route path="/login" element={
          <motion.div {...pageVariants}>
            <Suspense fallback={<PageLoader />}>
              <Login />
            </Suspense>
          </motion.div>
        } />
        <Route path="/report/:id" element={
          <ProtectedRoute>
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <Report />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/dashboard" element={
          <ProtectedRoute requiredRole="admin">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <CommandCenter />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/analysis" element={
          <ProtectedRoute requiredRole="admin">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <AnalysisEngine />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/forensic" element={
          <ProtectedRoute requiredRole="admin">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <ForensicReport />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/vault" element={
          <ProtectedRoute requiredRole="admin">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <VerificationVault />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/history" element={
          <ProtectedRoute requiredRole="admin">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <History />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
      </Routes>
    </AnimatePresence>
  );
}

function PageLoader() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg)',
    }}>
      <div style={{
        width: '8px', height: '8px',
        borderRadius: '50%',
        background: 'var(--accent)',
        animation: 'pulse 1.5s ease-in-out infinite',
      }} />
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AnimatedRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
