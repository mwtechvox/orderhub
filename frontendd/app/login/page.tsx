"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { ErrorNotice } from "@/components/ui";
export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const router = useRouter();
  const cache = useQueryClient();
  return (
    <main className="login">
      <div className="login-intro">
        <span className="brand-icon">O</span>
        <h1>
          Харилцагч бүртэйгээ
          <br />
          илүү ойр.
        </h1>
        <p>Facebook нийтлэл, сэтгэгдэл, Messenger мессеж — нэг ажлын орчинд.</p>
      </div>
      <form
        className="card login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await post("/api/auth/login/", { username, password });
            cache.clear();
            router.push("/inbox");
          } catch (err) {
            setError(err);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="eyebrow">ORDERHUB</p>
        <h2>Тавтай морил</h2>
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
          {busy ? "Нэвтэрч байна…" : "Нэвтрэх →"}
        </button>
      </form>
    </main>
  );
}
