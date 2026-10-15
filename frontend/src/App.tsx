import { Navigate, Route, Routes, useLocation } from "react-router";
import { LoadingState } from "@/components/ui";
import { useAuth } from "@/features/auth/AuthContext";
import SignInPage from "@/features/auth/SignInPage";
import InboxPage from "@/features/inbox/InboxPage";
import IntegrationsPage from "@/features/integrations/IntegrationsPage";
import PostComposerPage from "@/features/posts/PostComposerPage";
import PostDetailPage from "@/features/posts/PostDetailPage";
import PostsPage from "@/features/posts/PostsPage";
import AppShell from "@/layouts/AppShell";

function ProtectedShell() {
  const { user, checking } = useAuth();
  const location = useLocation();
  if (checking)
    return (
      <main className="fatal-state">
        <LoadingState />
      </main>
    );
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<SignInPage />} />
      <Route element={<ProtectedShell />}>
        <Route index element={<Navigate to="/inbox" replace />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/posts" element={<PostsPage />} />
        <Route path="/posts/new" element={<PostComposerPage />} />
        <Route path="/posts/:id" element={<PostDetailPage />} />
        <Route path="/posts/:id/edit" element={<PostComposerPage />} />
        <Route path="/settings/integrations" element={<IntegrationsPage />} />
        <Route path="*" element={<Navigate to="/inbox" replace />} />
      </Route>
    </Routes>
  );
}
