"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, API_URL } from "@/lib/api";
import type { Account, CommentAutomationRule, Page } from "@/lib/types";
import { dateTime } from "@/lib/format";
import { useCanManageIntegration, useCompany } from "./shell";
import { PlatformBadge, StatusBadge } from "./social-ui";
import { Empty, ErrorNotice, Pager } from "./ui";
const labels = {
  ACTIVE: "Холбогдсон",
  NEEDS_REAUTH: "Дахин холбох шаардлагатай",
  DISCONNECTED: "Салгасан",
};
const syncLabels: Record<string, string> = {
  IDLE: "Бэлэн",
  QUEUED: "Дараалалд",
  RUNNING: "Синк хийж байна",
  FAILED: "Синк амжилтгүй",
};
type Choices = {
  selection_id: string | null;
  pages: { id: string; name: string }[];
};

export function CommentAutomationSettings({ account }: { account: Account }) {
  const company = useCompany();
  const rule = useQuery({
    queryKey: ["comment-automation", company, account.id],
    queryFn: () =>
      api<CommentAutomationRule>(
        `/api/meta/accounts/${account.id}/comment-automation/`,
      ),
  });
  if (rule.isLoading)
    return <p className="muted">Автомат хариуны тохиргоог ачаалж байна…</p>;
  if (!rule.data) return <ErrorNotice error={rule.error} />;
  return (
    <CommentAutomationForm
      key={rule.data.updated_at ?? "new"}
      account={account}
      initial={rule.data}
      company={company}
    />
  );
}

function CommentAutomationForm({
  account,
  initial,
  company,
}: {
  account: Account;
  initial: CommentAutomationRule;
  company: string;
}) {
  const cache = useQueryClient();
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  async function save() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await api<CommentAutomationRule>(
        `/api/meta/accounts/${account.id}/comment-automation/`,
        { method: "PUT", body: JSON.stringify(form) },
      );
      setForm(updated);
      cache.setQueryData(["comment-automation", company, account.id], updated);
      setSaved(true);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="comment-automation">
      <div className="automation-heading">
        <div>
          <p className="eyebrow">FACEBOOK COMMENT</p>
          <h3>Сэтгэгдлийн автомат хариу</h3>
        </div>
        <label className="switch-control">
          <input
            type="checkbox"
            checked={form.is_enabled}
            onChange={(event) =>
              setForm({ ...form, is_enabled: event.target.checked })
            }
          />
          <span>{form.is_enabled ? "Идэвхтэй" : "Унтраалттай"}</span>
        </label>
      </div>
      <p className="muted">
        Шинэ top-level Facebook сэтгэгдэл бүрт сонгосон нийтийн хариуг бичиж,
        хэрэглэгчид нэг удаагийн хувийн мессеж илгээнэ.
      </p>
      <div className="automation-field">
        <label className="check-row">
          <input
            type="checkbox"
            checked={form.public_reply_enabled}
            onChange={(event) =>
              setForm({ ...form, public_reply_enabled: event.target.checked })
            }
          />
          Нийтийн хариу илгээх
        </label>
        <textarea
          aria-label={`${account.display_name} нийтийн хариу`}
          value={form.public_reply_text}
          maxLength={8000}
          disabled={!form.public_reply_enabled}
          onChange={(event) =>
            setForm({ ...form, public_reply_text: event.target.value })
          }
        />
      </div>
      <div className="automation-field">
        <label className="check-row">
          <input
            type="checkbox"
            checked={form.private_reply_enabled}
            onChange={(event) =>
              setForm({ ...form, private_reply_enabled: event.target.checked })
            }
          />
          Хувийн мессеж илгээх
        </label>
        <textarea
          aria-label={`${account.display_name} хувийн мессеж`}
          value={form.private_reply_text}
          maxLength={2000}
          disabled={!form.private_reply_enabled}
          onChange={(event) =>
            setForm({ ...form, private_reply_text: event.target.value })
          }
        />
        <small className="muted">
          Meta нэг сэтгэгдэлд зөвхөн нэг private reply зөвшөөрдөг. Хэрэглэгч
          хариулсны дараа одоогийн Мессеж хэсэгт үргэлжилнэ.
        </small>
      </div>
      <ErrorNotice error={error} />
      <div className="integration-actions">
        <button
          className="primary"
          disabled={saving}
          onClick={() => void save()}
        >
          {saving ? "Хадгалж байна…" : "Хадгалах"}
        </button>
        {saved && <span role="status">Тохиргоо хадгалагдлаа.</span>}
      </div>
    </div>
  );
}
export default function Integrations() {
  const company = useCompany();
  const canManageIntegration = useCanManageIntegration();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const accounts = useQuery({
    queryKey: ["accounts", company, page],
    queryFn: () => api<Page<Account>>(`/api/meta/accounts/?page=${page}`),
    refetchInterval: 5000,
  });
  const choices = useQuery({
    queryKey: ["page-choices", company],
    queryFn: () => api<Choices>("/api/meta/facebook/pages/"),
    retry: false,
    enabled: canManageIntegration,
  });
  async function action(
    id: string,
    fn: () => Promise<unknown>,
    success: string,
  ) {
    setBusy(id);
    setError(null);
    setNotice("");
    try {
      const result = await fn();
      await cache.invalidateQueries({ queryKey: ["accounts", company] });
      await cache.invalidateQueries({ queryKey: ["page-choices", company] });
      setNotice(typeof result === "string" ? result : success);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ТОХИРГОО</p>
          <h1>Холболтууд</h1>
          <p className="muted">Facebook хуудсаа холбож ажлаа эхлүүлээрэй.</p>
        </div>
      </div>
      <ErrorNotice error={error || accounts.error} />
      {notice && (
        <p role="status" className="success">
          {notice}
        </p>
      )}
      <section className="card integration-card">
        <div className="connection">
          <PlatformBadge platform="FACEBOOK_PAGE" />
          <div>
            <h2>Facebook</h2>
            <p className="muted">Нийтлэл, сэтгэгдэл болон Messenger мессеж</p>
          </div>
        </div>
        <p className="muted">
          Компанийн OWNER эсвэл ADMIN эрхээр холболт удирдана.
        </p>
        {canManageIntegration && (
          <a
            className="connect-link"
            href={`${API_URL}/api/meta/facebook/connect/`}
          >
            + Facebook холбох
          </a>
        )}
      </section>
      {canManageIntegration && choices.data?.pages.length ? (
        <section className="card integration-card">
          <h2>Холбох хуудсаа сонгох</h2>
          {choices.data.pages.map((p) => (
            <div className="page-choice" key={p.id}>
              <strong>{p.name}</strong>
              <button
                className="primary"
                disabled={!!busy}
                onClick={() =>
                  void action(
                    p.id,
                    () =>
                      post("/api/meta/facebook/pages/", {
                        selection_id: choices.data?.selection_id,
                        page_id: p.id,
                      }),
                    "Хуудас холбогдлоо. Синк эхэлж байна.",
                  )
                }
              >
                {busy === p.id ? "Холбож байна…" : "Сонгох"}
              </button>
            </div>
          ))}
        </section>
      ) : null}
      {accounts.isLoading ? (
        <Empty>Ачаалж байна…</Empty>
      ) : (
        accounts.data?.results.map((a) => (
          <section key={a.id} className="card integration-card">
            <div className="connection">
              <PlatformBadge platform={a.platform} />
              <div>
                <h2>{a.display_name}</h2>
                <StatusBadge
                  tone={a.status === "ACTIVE" ? "success" : "warning"}
                >
                  {labels[a.status]}
                </StatusBadge>
              </div>
            </div>
            <p className="muted">
              Синк: {syncLabels[a.sync_status] ?? a.sync_status} ·{" "}
              {a.last_synced_at
                ? dateTime(a.last_synced_at)
                : "Одоогоор синк хийгдээгүй"}
            </p>
            {a.last_error && (
              <p className="error">
                Facebook хүсэлт амжилтгүй. Холболт болон зөвшөөрлөө шалгаад
                дахин оролдоно уу.
              </p>
            )}
            {canManageIntegration && (
              <>
                <div className="integration-actions">
                  <button
                    disabled={!!busy || a.status !== "ACTIVE"}
                    onClick={() =>
                      void action(
                        a.id,
                        () => post(`/api/meta/accounts/${a.id}/sync/`),
                        "Синк хийх хүсэлтийг хүлээн авлаа.",
                      )
                    }
                  >
                    ↻ Синк хийх
                  </button>
                  <a
                    className="button-link"
                    href={`${API_URL}/api/meta/facebook/connect/`}
                  >
                    Дахин холбох
                  </a>
                  <button
                    disabled={!!busy || a.status === "DISCONNECTED"}
                    onClick={() => {
                      if (
                        window.confirm(`${a.display_name} холболтыг салгах уу?`)
                      )
                        void action(
                          a.id,
                          async () => {
                            const result = await api<{
                              remote_unsubscribed: boolean;
                              shared_subscription: boolean;
                            }>(`/api/meta/accounts/${a.id}/`, {
                              method: "DELETE",
                            });
                            if (
                              !result.remote_unsubscribed &&
                              !result.shared_subscription
                            )
                              return "Локал холболт салсан. Meta Dashboard дээр app subscription-ийг шалгана уу.";
                          },
                          "Холболт саллаа.",
                        );
                    }}
                  >
                    Салгах
                  </button>
                </div>
                {a.platform === "FACEBOOK_PAGE" && (
                  <CommentAutomationSettings account={a} />
                )}
              </>
            )}
          </section>
        ))
      )}
      <Pager page={page} count={accounts.data?.count ?? 0} onChange={setPage} />
    </>
  );
}
