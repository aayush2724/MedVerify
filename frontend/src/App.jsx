import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Suspense, lazy } from 'react';
import { AuthProvider } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';

const Home = lazy(() => import('./pages/Home'));
const Report = lazy(() => import('./pages/Report'));
const Login = lazy(() => import('./pages/Login'));
const CommandCenter = lazy(() => import('./pages/CommandCenter'));
const AnalysisEngine = lazy(() => import('./pages/AnalysisEngine'));
const VerificationVault = lazy(() => import('./pages/VerificationVault'));
const ForensicReport = lazy(() => import('./pages/ForensicReport'));
const Profile = lazy(() => import('./pages/Profile'));
// Module 2 — Medication Safety Check
const MyMedications = lazy(() => import('./pages/MyMedications'));
const AddMedication = lazy(() => import('./pages/AddMedication'));
const SafetyReport = lazy(() => import('./pages/SafetyReport'));
// Module 2, Phase 3 — both modules over one document
const PrescriptionCheck = lazy(() => import('./pages/PrescriptionCheck'));

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
        <Route path="/forensic-report" element={
          <ProtectedRoute requiredRole="verifier">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <ForensicReport />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/analysis" element={
          <ProtectedRoute requiredRole="verifier">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <AnalysisEngine />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/vault" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <VerificationVault />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        {/* Module 2 — available to every signed-in role: a medication list is
            personal, not privileged. */}
        <Route path="/medications" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <MyMedications />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/medications/add" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <AddMedication />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/medications/report" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <SafetyReport />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/medications/report/:id" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <SafetyReport />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        {/* Phase 3 reads a medication list off the document, so it is scoped
            like Module 2 (any signed-in user, own data only) rather than like
            Module 1's verifier-only upload. */}
        <Route path="/prescription-check" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <PrescriptionCheck />
              </Suspense>
            </motion.div>
          </ProtectedRoute>
        } />
        <Route path="/profile" element={
          <ProtectedRoute requiredRole="viewer">
            <motion.div {...pageVariants}>
              <Suspense fallback={<PageLoader />}>
                <Profile />
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
