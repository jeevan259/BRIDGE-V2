import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/lib/auth';
import apiClient from '@/lib/api';
import { User, UserRole } from '@/types';
import { AppShell } from '@/components/layout/AppShell';
import { Spinner } from '@/components/ui/Spinner';

// Pages
import { LoginPage } from '@/pages/auth/LoginPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { KnowledgePage } from '@/pages/knowledge/KnowledgePage';
import { ValidationPage } from '@/pages/validation/ValidationPage';
import { ReviewPage } from '@/pages/review/ReviewPage';
import { ContinuityPage } from '@/pages/continuity/ContinuityPage';
import { GuidelinePage } from '@/pages/guideline/GuidelinePage';
import { GovernancePage } from '@/pages/governance/GovernancePage';
import { AdminPage } from '@/pages/admin/AdminPage';

interface GuardProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

const AuthGuard: React.FC<GuardProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, user, setUser, setLoading, logout } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('bridge_access_token');
      if (!token) {
        setLoading(false);
        return;
      }

      if (!user) {
        try {
          const { data } = await apiClient.get<User>('/auth/me');
          setUser(data);
        } catch (err) {
          const savedUserRaw = localStorage.getItem('bridge_user');
          if (savedUserRaw) {
            try {
              setUser(JSON.parse(savedUserRaw));
            } catch {
              logout();
            }
          } else {
            console.error('Failed to restore user session:', err);
            logout();
          }
        } finally {
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    };

    initAuth();
  }, [user, setUser, setLoading, logout]);

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-[#0B0F19] flex items-center justify-center">
        <Spinner size="lg" label="Initializing secure BRIDGE session..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Application Routes */}
        <Route
          path="/"
          element={
            <AuthGuard>
              <AppShell />
            </AuthGuard>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="overview" element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="submissions" element={<ValidationPage />} />
          <Route path="validation" element={<Navigate to="/submissions" replace />} />

          <Route
            path="review"
            element={
              <AuthGuard allowedRoles={['administrator', 'brand_manager', 'reviewer', 'auditor']}>
                <ReviewPage />
              </AuthGuard>
            }
          />

          <Route
            path="continuity"
            element={
              <AuthGuard allowedRoles={['administrator', 'brand_manager', 'reviewer', 'auditor']}>
                <ContinuityPage />
              </AuthGuard>
            }
          />

          <Route
            path="guidelines"
            element={
              <AuthGuard allowedRoles={['administrator', 'brand_manager', 'reviewer', 'auditor']}>
                <GuidelinePage />
              </AuthGuard>
            }
          />

          <Route
            path="governance"
            element={
              <AuthGuard allowedRoles={['administrator', 'brand_manager', 'reviewer', 'auditor']}>
                <GovernancePage />
              </AuthGuard>
            }
          />
          <Route path="audit" element={<Navigate to="/governance" replace />} />

          <Route
            path="admin"
            element={
              <AuthGuard allowedRoles={['administrator']}>
                <AdminPage />
              </AuthGuard>
            }
          />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
