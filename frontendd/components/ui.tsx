"use client";
import { useId, useState } from "react";
export function ErrorNotice({ error }: { error: unknown }) {
  return error ? (
    <p role="alert" className="error">
      {error instanceof Error ? error.message : "Алдаа гарлаа."}
    </p>
  ) : null;
}
export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Pager({
  page,
  count,
  onChange,
}: {
  page: number;
  count: number;
  onChange: (page: number) => void;
}) {
  return count > 25 ? (
    <div className="pager">
      <button disabled={page === 1} onClick={() => onChange(page - 1)}>
        ← Өмнөх
      </button>
      <span>
        {page} / {Math.ceil(count / 25)}
      </span>
      <button disabled={page * 25 >= count} onClick={() => onChange(page + 1)}>
        Дараах →
      </button>
    </div>
  ) : null;
}
export function Composer({
  onSend,
  label = "Илгээх",
  disabled = false,
  maxLength = 8000,
}: {
  onSend: (text: string) => Promise<unknown>;
  label?: string;
  disabled?: boolean;
  maxLength?: number;
}) {
  const inputId = useId();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || busy || disabled) return;
    setBusy(true);
    setError(null);
    try {
      await onSend(text.trim());
      setText("");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="composer">
      <label className="sr-only" htmlFor={inputId}>
        Хариу бичих
      </label>
      <textarea
        id={inputId}
        aria-label="Хариу бичих"
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={maxLength}
        placeholder="Хариу бичих…"
        disabled={disabled || busy}
      />
      <button className="primary" disabled={disabled || busy || !text.trim()}>
        {busy ? "Илгээж байна…" : label}
      </button>
      <ErrorNotice error={error} />
    </form>
  );
}
