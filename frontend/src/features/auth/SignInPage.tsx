import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { Button, ErrorNotice } from "@/components/ui";
import { useAuth } from "./AuthContext";

export default function SignInPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  if (user) return <Navigate to="/inbox" replace />;
  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="brand login-brand">
          <span className="brand-mark">
            <span />
            <span />
            <span />
          </span>
          <strong>OrderHub</strong>
        </div>
        <h1>
          Харилцагч бүртэйгээ
          <br />
          илүү ойр.
        </h1>
        <p>Facebook нийтлэл, сэтгэгдэл, Messenger мессеж — нэг өнгөлөг ажлын орчинд.</p>
      </section>
      <form
        className="login-card"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await signIn(username, password);
            navigate((location.state as { from?: string } | null)?.from ?? "/inbox", {
              replace: true,
            });
          } catch (reason) {
            setError(reason);
          } finally {
            setBusy(false);
          }
        }}
      >
        <small className="eyebrow">ORDERHUB</small>
        <h2>Тавтай морил</h2>
        <p>Ажлын бүртгэлээрээ нэвтэрнэ үү.</p>
        <label>
          Нэвтрэх нэр
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          Нууц үг
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <ErrorNotice error={error} />
        <Button type="submit" variant="primary" disabled={busy}>
          {busy ? "Нэвтэрч байна…" : "Нэвтрэх"}
        </Button>
      </form>
    </main>
  );
}
