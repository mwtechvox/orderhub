"use client";
import Image from "next/image";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { ErrorNotice } from "@/components/ui";
export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [isEntering, setIsEntering] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const router = useRouter();
  const cache = useQueryClient();
  return (
    <main className={`login login-experience ${isEntering ? "is-entering" : ""}`}>
      <div className="login-aurora login-aurora-one" aria-hidden="true" />
      <div className="login-aurora login-aurora-two" aria-hidden="true" />
      <section className="login-botgo-panel" aria-label="Ботго таныг угтаж байна">
        <div className="login-brand-lockup">
          <span className="marketing-brand-mark" aria-hidden="true">
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
          <Image
            className="login-botgo-image"
            src="/botgo-orderhub.png"
            alt="Малгайтай ботго, OrderHub-ийн туслах дүр"
            width={1229}
            height={1280}
            priority
          />
        </div>
        <div className="login-welcome-copy">
          <p className="marketing-kicker">ТАНЫ ХАЖУУД</p>
          <h1>Харилцагч бүртэйгээ илүү ойр.</h1>
          <p>Ботго танай багийг хүлээж байна.</p>
        </div>
      </section>
      <form
        className="card login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await post("/api/auth/login/", { username, password });
            cache.clear();
            setIsEntering(true);
            window.setTimeout(() => router.push("/inbox"), 560);
          } catch (err) {
            setError(err);
            setBusy(false);
          }
        }}
      >
        <div className="login-form-heading">
          <span className="login-form-icon" aria-hidden="true">↗</span>
          <div>
            <p className="eyebrow">ORDERHUB</p>
            <h2>Тавтай морил</h2>
          </div>
        </div>
        <p className="muted">Ажлын бүртгэлээрээ нэвтэрнэ үү.</p>
        <label>
          Нэвтрэх нэр
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label>
          Нууц үг
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <ErrorNotice error={error} />
        <button className="primary" disabled={busy}>
          {isEntering ? "Тавтай морил…" : busy ? "Нэвтэрч байна…" : "Нэвтрэх →"}
        </button>
        <p className="login-form-footnote">Ажлын орчин тань аюулгүй холбогдоно.</p>
      </form>
    </main>
  );
}
