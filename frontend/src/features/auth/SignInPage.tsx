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
    <main className="login-page login-experience">
      <section className="login-intro login-botgo-panel" aria-label="Ботго таныг угтаж байна">
        <div className="brand login-brand login-brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <strong>OrderHub</strong>
        </div>
        <div className="login-botgo-orbit login-botgo-orbit-large" aria-hidden="true" />
        <div className="login-botgo-orbit login-botgo-orbit-small" aria-hidden="true" />
        <div className="login-message login-message-first" aria-hidden="true">
          <span className="login-message-dot" />
          <span>Сайн уу!</span>
        </div>
        <div className="login-message login-message-second" aria-hidden="true">
          <span className="login-message-bars">
            <i />
            <i />
            <i />
          </span>
          <span>Хариу бэлэн</span>
        </div>
        <div className="login-spark login-spark-one" aria-hidden="true">✦</div>
        <div className="login-spark login-spark-two" aria-hidden="true">✦</div>
        <div className="login-botgo-motion">
          <img
            className="login-botgo-image"
            src="/botgo-orderhub.png"
            alt="Малгайтай ботго, OrderHub-ийн туслах дүр"
          />
        </div>
        <div className="login-welcome-copy">
          <p className="marketing-kicker">ТАНЫ ХАЖУУД</p>
          <h1>Харилцагч бүртэйгээ илүү ойр.</h1>
          <p>Ботго танай багийг хүлээж байна.</p>
        </div>
      </section>
      <form
        className="login-card login-experience-form"
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
        <div className="login-form-heading">
          <span className="login-form-icon" aria-hidden="true">↗</span>
          <div>
            <small className="eyebrow">ORDERHUB</small>
            <h2>Тавтай морил</h2>
          </div>
        </div>
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
        <p className="login-form-footnote">Ажлын орчин тань аюулгүй холбогдоно.</p>
      </form>
    </main>
  );
}
