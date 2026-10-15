import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, put } from "@/lib/api-client";
import { dateTime } from "@/lib/formatters";
import type { Account, CommentAutomationRule, Page, PageChoices } from "@/types/api";
import AutomationFields from "@/components/social/AutomationFields";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorNotice,
  LoadingState,
  Pager,
  PlatformBadge,
  StatusBadge,
} from "@/components/ui";
import Icon from "@/components/ui/Icon";
import { useWorkspace } from "@/features/companies/WorkspaceContext";

const statusLabels = {
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

export default function IntegrationsPage() {
  const { companyId, canManage } = useWorkspace();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [disconnecting, setDisconnecting] = useState<Account | null>(null);
  const accounts = useQuery({
    queryKey: ["accounts", companyId, page],
    queryFn: () => api<Page<Account>>(`/api/meta/accounts/?page=${page}`),
    refetchInterval: 5000,
  });
  const choices = useQuery({
    queryKey: ["page-choices", companyId],
    queryFn: () => api<PageChoices>("/api/meta/facebook/pages/"),
    retry: false,
    enabled: canManage,
  });
  async function action(key: string, operation: () => Promise<unknown>, success: string) {
    setBusy(key);
    setError(null);
    setNotice("");
    try {
      await operation();
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["accounts", companyId] }),
        cache.invalidateQueries({ queryKey: ["page-choices", companyId] }),
      ]);
      setNotice(success);
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(null);
    }
  }
  return (
    <div className="screen integrations-screen">
      <div className="page-top">
        <div>
          <h1>Холболтууд</h1>
          <p>Сошиал сувгууд болон бизнес хаягуудаа удирдана.</p>
        </div>
        {canManage && (
          <a className="button button-primary" href="/api/meta/facebook/connect/">
            + Facebook холбох
          </a>
        )}
      </div>
      <ErrorNotice error={error || accounts.error} />
      {notice && (
        <div className="feedback success" role="status">
          <Icon name="check" />
          <span>
            <strong>{notice}</strong>
          </span>
        </div>
      )}
      <div className="integration-summary">
        <span className="summary-icon">
          <Icon name="link" />
        </span>
        <div>
          <strong>{accounts.data?.count ?? 0} суваг холбогдсон</strong>
          <p>Мессеж, нийтлэлүүд автоматаар синк хийгдэнэ.</p>
        </div>
        <StatusBadge
          tone={
            accounts.data?.results.some((item) => item.status === "ACTIVE") ? "success" : "warning"
          }
        >
          {accounts.data?.results.some((item) => item.status === "ACTIVE")
            ? "Хэвийн"
            : "Тохиргоо шаардлагатай"}
        </StatusBadge>
      </div>
      {canManage && choices.data?.pages.length ? (
        <section className="page-choice-card">
          <h2>Холбох Page-аа сонгоно уу</h2>
          {choices.data.pages.map((choice) => (
            <div className="page-choice" key={choice.id}>
              <span>
                <Avatar name={choice.name} store />
                <strong>{choice.name}</strong>
              </span>
              <Button
                variant="primary"
                disabled={!!busy}
                onClick={() =>
                  void action(
                    choice.id,
                    () =>
                      post("/api/meta/facebook/pages/", {
                        selection_id: choices.data?.selection_id,
                        page_id: choice.id,
                      }),
                    "Facebook Page холбогдлоо.",
                  )
                }
              >
                {busy === choice.id ? "Холбож байна..." : "Сонгох"}
              </Button>
            </div>
          ))}
        </section>
      ) : null}
      <h2 className="connections-title">Холбогдсон сувгууд</h2>
      {accounts.isLoading ? (
        <LoadingState />
      ) : accounts.data?.results.length ? (
        accounts.data.results.map((account) => (
          <article className="integration-card" key={account.id}>
            <div className="integration-brand">
              <span className="facebook-logo">f</span>
              <span>
                <strong>Facebook</strong>
                <small>Мессеж, нийтлэл, сэтгэгдэл</small>
              </span>
              <StatusBadge tone={account.status === "ACTIVE" ? "success" : "warning"}>
                {statusLabels[account.status]}
              </StatusBadge>
            </div>
            <div className="connected-account">
              <div>
                <Avatar name={account.display_name} store />
                <span>
                  <small>ХОЛБОГДСОН ХАЯГ</small>
                  <strong>{account.display_name}</strong>
                </span>
              </div>
              <div className="sync-info">
                <Icon name="clock" />
                <span>
                  <small>{syncLabels[account.sync_status] ?? account.sync_status}</small>
                  <strong>
                    {account.last_synced_at ? dateTime(account.last_synced_at) : "Синк хийгдээгүй"}
                  </strong>
                </span>
              </div>
            </div>
            {account.last_error && (
              <div className="feedback danger">
                <span>
                  <strong>Facebook хүсэлт амжилтгүй</strong>
                  <small>Холболт болон зөвшөөрлөө шалгана уу.</small>
                </span>
              </div>
            )}
            <div className="integration-footer">
              <span>
                <i className="health-dot" />
                Холболтын төлөв: {statusLabels[account.status]}
              </span>
              {canManage && (
                <div>
                  <Button
                    icon="sync"
                    disabled={!!busy || account.status !== "ACTIVE"}
                    onClick={() =>
                      void action(
                        account.id,
                        () => post(`/api/meta/accounts/${account.id}/sync/`),
                        "Синк хийх хүсэлтийг хүлээн авлаа.",
                      )
                    }
                  >
                    {busy === account.id ? "Синк хийж байна..." : "Синк хийх"}
                  </Button>
                  <a className="button button-quiet" href="/api/meta/facebook/connect/">
                    Дахин холбох
                  </a>
                  <Button
                    variant="quiet"
                    className="danger-text"
                    disabled={account.status === "DISCONNECTED"}
                    onClick={() => setDisconnecting(account)}
                  >
                    Салгах
                  </Button>
                </div>
              )}
            </div>
            {canManage && account.platform === "FACEBOOK_PAGE" && (
              <CommentAutomation account={account} />
            )}
          </article>
        ))
      ) : (
        <EmptyState
          title="Холбогдсон суваг алга"
          description="OWNER эсвэл ADMIN эрхээр Facebook Page холбоно уу."
        />
      )}
      <Pager page={page} count={accounts.data?.count ?? 0} onChange={setPage} />
      {disconnecting && (
        <div className="modal-backdrop" onClick={() => setDisconnecting(null)}>
          <div className="confirm-dialog" onClick={(event) => event.stopPropagation()}>
            <span className="dialog-icon">
              <Icon name="link" />
            </span>
            <h2>Facebook сувгийг салгах уу?</h2>
            <p>{disconnecting.display_name}-ийн шинэ мессеж, нийтлэлүүд синк хийхээ болино.</p>
            <div>
              <Button onClick={() => setDisconnecting(null)}>Болих</Button>
              <Button
                variant="danger"
                onClick={() =>
                  void action(
                    disconnecting.id,
                    () =>
                      api(`/api/meta/accounts/${disconnecting.id}/`, {
                        method: "DELETE",
                      }),
                    "Холболт саллаа.",
                  ).then(() => setDisconnecting(null))
                }
              >
                Салгах
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CommentAutomation({ account }: { account: Account }) {
  const { companyId } = useWorkspace();
  const query = useQuery({
    queryKey: ["comment-automation", companyId, account.id],
    queryFn: () =>
      api<CommentAutomationRule>(`/api/meta/accounts/${account.id}/comment-automation/`),
  });
  if (query.isLoading) return <LoadingState>Автомат хариуны тохиргоог ачаалж байна…</LoadingState>;
  if (!query.data) return <ErrorNotice error={query.error} />;
  return <AutomationForm account={account} initial={query.data} />;
}

function AutomationForm({
  account,
  initial,
}: {
  account: Account;
  initial: CommentAutomationRule;
}) {
  const [form, setForm] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<unknown>(null);
  return (
    <details className="comment-automation" open>
      <summary>Сэтгэгдлийн автомат хариу</summary>
      <p>Шинэ Facebook сэтгэгдэлд нийтийн хариу болон нэг удаагийн хувийн мессеж илгээнэ.</p>
      <AutomationFields value={form} onChange={setForm} />
      <ErrorNotice error={error} />
      <div className="form-actions">
        <Button
          variant="primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setSaved(false);
            setError(null);
            try {
              setForm(
                await put<CommentAutomationRule>(
                  `/api/meta/accounts/${account.id}/comment-automation/`,
                  form,
                ),
              );
              setSaved(true);
            } catch (reason) {
              setError(reason);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Хадгалж байна..." : "Хадгалах"}
        </Button>
        {saved && <StatusBadge tone="success">Хадгалагдлаа</StatusBadge>}
      </div>
    </details>
  );
}
