import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api, patch } from "@/lib/api-client";
import type { Account, CommentAutomationRule, Page, Post } from "@/types/api";
import AutomationFields, { DEFAULT_AUTOMATION } from "@/components/social/AutomationFields";
import { Button, ErrorNotice, LoadingState } from "@/components/ui";
import { useWorkspace } from "@/features/companies/WorkspaceContext";

export default function PostComposerPage() {
  const { id } = useParams();
  const { companyId, canManage } = useWorkspace();
  const navigate = useNavigate();
  const accounts = useQuery({
    queryKey: ["accounts", companyId],
    queryFn: () => api<Page<Account>>("/api/meta/accounts/"),
  });
  const existing = useQuery({
    queryKey: ["post", companyId, id],
    queryFn: () => api<Post>(`/api/posts/${id}/`),
    enabled: !!id,
  });
  const [account, setAccount] = useState("");
  const [message, setMessage] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [override, setOverride] = useState(false);
  const [automation, setAutomation] = useState<CommentAutomationRule>(DEFAULT_AUTOMATION);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    const item = existing.data;
    if (item) {
      setAccount(item.social_account);
      setMessage(item.message);
      setImageUrl(item.media[0]?.url ?? "");
      setScheduledAt(item.scheduled_at?.slice(0, 16) ?? "");
      setOverride(!!item.comment_automation);
      setAutomation(item.comment_automation ?? DEFAULT_AUTOMATION);
    } else if (!account && accounts.data?.results[0]) setAccount(accounts.data.results[0].id);
  }, [existing.data, accounts.data, account]);
  if (!canManage) return <Navigate to="/posts" replace />;
  if (accounts.isLoading || (id && existing.isLoading)) return <LoadingState />;
  async function save(mode: "DRAFT" | "PUBLISH_NOW" | "SCHEDULE") {
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      social_account: account,
      message,
      media: imageUrl.trim() ? [{ type: "image", url: imageUrl.trim() }] : [],
      publish_mode: mode,
    };
    if (mode === "SCHEDULE") body.scheduled_at = new Date(scheduledAt).toISOString();
    if (override) body.comment_automation = automation;
    try {
      const saved = id
        ? await patch<Post>(`/api/posts/${id}/`, body)
        : await api<Post>("/api/posts/", {
            method: "POST",
            body: JSON.stringify(body),
          });
      navigate(`/posts/${saved.id}`);
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }
  const activeAccounts =
    accounts.data?.results.filter(
      (item) => item.status === "ACTIVE" && item.platform === "FACEBOOK_PAGE",
    ) ?? [];
  return (
    <div className="screen composer-page">
      <div className="page-top">
        <div className="title-with-back">
          <Link className="button button-icon" to={id ? `/posts/${id}` : "/posts"}>
            ←
          </Link>
          <div>
            <h1>{id ? "Нийтлэл засах" : "Шинэ нийтлэл"}</h1>
            <p>Facebook Page нийтлэл бэлтгэж, хуваарьт оруулна.</p>
          </div>
        </div>
      </div>
      <form className="post-editor" onSubmit={(event) => event.preventDefault()}>
        <label>
          Facebook Page
          <select value={account} onChange={(event) => setAccount(event.target.value)}>
            {activeAccounts.map((item) => (
              <option key={item.id} value={item.id}>
                {item.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Нийтлэлийн текст
          <textarea
            rows={8}
            maxLength={63206}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>
        <label>
          Зургийн HTTPS URL <small>(нэг зураг)</small>
          <input
            type="url"
            placeholder="https://..."
            value={imageUrl}
            onChange={(event) => setImageUrl(event.target.value)}
          />
        </label>
        <label>
          Хуваарьт нийтлэх хугацаа
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={(event) => setScheduledAt(event.target.value)}
          />
        </label>
        <details className="automation-card" open={override}>
          <summary>Сэтгэгдлийн автомат хариу</summary>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={override}
              onChange={(event) => setOverride(event.target.checked)}
            />
            <span>Энэ нийтлэлд тусдаа тохиргоо ашиглах</span>
          </label>
          {override ? (
            <AutomationFields value={automation} onChange={setAutomation} />
          ) : (
            <p>Page-ийн үндсэн тохиргоог ашиглана.</p>
          )}
        </details>
        <ErrorNotice error={error || accounts.error || existing.error} />
        <div className="form-actions">
          <Button disabled={busy || !account} onClick={() => void save("DRAFT")}>
            Ноорог хадгалах
          </Button>
          <Button disabled={busy || !account || !scheduledAt} onClick={() => void save("SCHEDULE")}>
            Хуваарьт оруулах
          </Button>
          <Button
            variant="primary"
            disabled={busy || !account}
            onClick={() => void save("PUBLISH_NOW")}
          >
            Одоо нийтлэх
          </Button>
        </div>
      </form>
    </div>
  );
}
