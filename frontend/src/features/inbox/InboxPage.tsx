import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post } from "@/lib/api-client";
import { dateTime } from "@/lib/formatters";
import type { Account, Conversation, Message, Page } from "@/types/api";
import Filters from "@/components/social/Filters";
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

export default function InboxPage() {
  const { companyId } = useWorkspace();
  const cache = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [mobileChat, setMobileChat] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("");
  const [account, setAccount] = useState("");
  const [actionError, setActionError] = useState<unknown>(null);
  const accounts = useQuery({
    queryKey: ["accounts", companyId],
    queryFn: () => api<Page<Account>>("/api/meta/accounts/"),
  });
  const conversations = useQuery({
    queryKey: ["conversations", companyId, page, search, platform, account],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), search });
      if (platform) params.set("platform", platform);
      if (account) params.set("social_account", account);
      return api<Page<Conversation>>(`/api/conversations/?${params}`);
    },
    refetchInterval: 2000,
  });
  const selectedConversation =
    conversations.data?.results.find((item) => item.id === selected) ?? null;

  async function selectConversation(item: Conversation) {
    setSelected(item.id);
    setMobileChat(true);
    setActionError(null);
    try {
      await post(`/api/conversations/${item.id}/read/`);
      await cache.invalidateQueries({ queryKey: ["conversations", companyId] });
    } catch (reason) {
      setActionError(reason);
    }
  }

  return (
    <div className={`screen inbox-screen ${mobileChat ? "mobile-chat-open" : ""}`}>
      <div className="page-top inbox-top">
        <div>
          <h1>Мессеж</h1>
          <p>Харилцагчидтай нэг дороос холбогдоорой.</p>
        </div>
        <StatusBadge tone="success">2 секунд тутам шинэчлэгдэнэ</StatusBadge>
      </div>
      <ErrorNotice error={accounts.error || conversations.error || actionError} />
      <div className="inbox-filters">
        <Filters
          accounts={accounts.data?.results ?? []}
          platform={platform}
          account={account}
          search={search}
          searchPlaceholder="Харилцагч, мессеж хайх..."
          onPlatformChange={(value) => {
            setPlatform(value);
            setAccount("");
            setPage(1);
            setSelected(null);
          }}
          onAccountChange={(value) => {
            setAccount(value);
            setPage(1);
            setSelected(null);
          }}
          onSearchChange={(value) => {
            setSearch(value);
            setPage(1);
          }}
        />
      </div>
      <div className="inbox-workspace">
        <section className="conversation-column">
          <div className="conversation-heading">
            <span>
              <strong>Ярианууд</strong>
              <small>{conversations.data?.count ?? 0} идэвхтэй</small>
            </span>
          </div>
          <div className="conversation-list">
            {conversations.isLoading ? (
              <LoadingState />
            ) : conversations.data?.results.length ? (
              conversations.data.results.map((item) => (
                <ConversationRow
                  key={item.id}
                  item={item}
                  selected={selected === item.id}
                  onClick={() => void selectConversation(item)}
                />
              ))
            ) : (
              <EmptyState title="Яриа алга" description="Facebook хуудсаа холбоод синк хийнэ үү." />
            )}
          </div>
          <Pager
            page={page}
            count={conversations.data?.count ?? 0}
            onChange={(value) => {
              setPage(value);
              setSelected(null);
            }}
          />
          <div className="list-footer">
            <span className="pulse-dot" /> Ярианууд автоматаар шинэчлэгдэнэ
          </div>
        </section>
        {selected ? (
          <ChatPanel id={selected} onBack={() => setMobileChat(false)} />
        ) : (
          <section className="chat-panel chat-empty">
            <EmptyState
              title="Яриа сонгоно уу"
              description="Харилцагчийн мессеж болон хариу энд харагдана."
            />
          </section>
        )}
        {selectedConversation ? (
          <CustomerContext item={selectedConversation} />
        ) : (
          <aside className="context-panel">
            <EmptyState title="Харилцагчийн мэдээлэл" description="Яриа сонгоход энд харагдана." />
          </aside>
        )}
      </div>
    </div>
  );
}

function ConversationRow({
  item,
  selected,
  onClick,
}: {
  item: Conversation;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`conversation-item ${selected ? "selected" : ""} ${
        item.unread_count ? "unread" : ""
      }`}
      onClick={onClick}
    >
      <Avatar name={item.customer.name} />
      <span className="conversation-copy">
        <span className="conversation-top">
          <strong>{item.customer.name || "Facebook хэрэглэгч"}</strong>
          <time>{dateTime(item.last_message_at)}</time>
        </span>
        <span className="conversation-meta">
          <PlatformBadge platform={item.platform} compact />
          <small>{item.page_name}</small>
        </span>
        <span className="preview-row">
          <span>{item.last_message || "Мессеж алга"}</span>
          {item.unread_count > 0 && <b className="unread-badge">{item.unread_count}</b>}
        </span>
      </span>
    </button>
  );
}

function ChatPanel({ id, onBack }: { id: string; onBack: () => void }) {
  const { companyId } = useWorkspace();
  const cache = useQueryClient();
  const pending = useRef<{ text: string; key: string } | null>(null);
  const [draft, setDraft] = useState("");
  const [page, setPage] = useState(1);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const conversation = useQuery({
    queryKey: ["conversation", companyId, id],
    queryFn: () => api<Conversation>(`/api/conversations/${id}/`),
    refetchInterval: 2000,
  });
  const messages = useQuery({
    queryKey: ["messages", companyId, id, page],
    queryFn: () => api<Page<Message>>(`/api/conversations/${id}/messages/?page=${page}`),
    refetchInterval: 2000,
  });
  const item = conversation.data;
  async function send() {
    const text = draft.trim();
    if (!text || sending || !item?.can_reply) return;
    if (!pending.current || pending.current.text !== text)
      pending.current = { text, key: crypto.randomUUID() };
    setSending(true);
    setError(null);
    try {
      await post("/api/messages/send/", {
        conversation_id: id,
        text,
        idempotency_key: pending.current.key,
      });
      pending.current = null;
      setDraft("");
      setPage(1);
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["messages", companyId, id] }),
        cache.invalidateQueries({ queryKey: ["conversations", companyId] }),
      ]);
    } catch (reason) {
      setError(reason);
    } finally {
      setSending(false);
    }
  }
  return (
    <section className="chat-panel">
      <header className="chat-header">
        <Button variant="icon" icon="arrow" className="mobile-back" onClick={onBack} />
        <Avatar name={item?.customer.name} />
        <div className="chat-person">
          <strong>{item?.customer.name || "Facebook хэрэглэгч"}</strong>
          <span>
            {item && <PlatformBadge platform={item.platform} />}
            <small>{item?.page_name}</small>
          </span>
        </div>
        {item && (
          <div className="reply-window">
            <StatusBadge tone={item.can_reply ? "success" : "warning"}>
              {item.can_reply ? "Хариулах боломжтой" : "24 цагийн хугацаа дууссан"}
            </StatusBadge>
          </div>
        )}
      </header>
      <ErrorNotice error={conversation.error || messages.error || error} />
      <div className="message-stream">
        <Pager page={page} count={messages.data?.count ?? 0} onChange={setPage} />
        {messages.isLoading ? (
          <LoadingState />
        ) : (
          [...(messages.data?.results ?? [])]
            .reverse()
            .map((message) => <MessageBubble key={message.id} message={message} />)
        )}
      </div>
      <div className="composer-wrap">
        {item && !item.can_reply && (
          <p className="composer-warning">
            Хэрэглэгч дахин мессеж илгээсний дараа хариулах боломжтой.
          </p>
        )}
        <div className="composer">
          <textarea
            value={draft}
            maxLength={2000}
            disabled={!item?.can_reply || sending}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void send();
              }
            }}
            placeholder="Мессеж бичих..."
          />
          <div className="composer-tools">
            <span />
            <Button
              variant="primary"
              icon="send"
              onClick={() => void send()}
              disabled={!draft.trim() || !item?.can_reply || sending}
            >
              {sending ? "Илгээж байна..." : "Илгээх"}
            </Button>
          </div>
        </div>
        <small className="composer-hint">Enter дарж илгээнэ · Shift + Enter шинэ мөр</small>
      </div>
    </section>
  );
}

function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`message-row ${message.direction === "OUTBOUND" ? "outgoing" : "incoming"}`}>
      {message.direction === "INBOUND" && <Avatar size="sm" />}
      <div>
        <div className="message-bubble">
          {message.text || "Хавсралт"}
          {message.attachments.map((attachment, index) => (
            <a key={index} href={attachment.url} target="_blank" rel="noreferrer">
              Хавсралт ↗
            </a>
          ))}
        </div>
        <time>
          {dateTime(message.sent_at)} · {messageStatus(message)}
        </time>
        {message.status === "FAILED" && (
          <small className="message-error">
            {message.error_code === "META_DELIVERY_UNKNOWN"
              ? "Хүргэлтийн төлөв тодорхойгүй. Messenger дээр шалгана уу."
              : "Илгээж чадсангүй."}
          </small>
        )}
      </div>
    </div>
  );
}

function messageStatus(message: Message) {
  return (
    {
      RECEIVED: "Хүлээн авсан",
      PENDING: "Дараалалд",
      SENDING: "Илгээж байна",
      SENT: "Илгээсэн",
      FAILED: "Амжилтгүй",
    } as const
  )[message.status];
}

function CustomerContext({ item }: { item: Conversation }) {
  return (
    <aside className="context-panel">
      <div className="context-profile">
        <Avatar name={item.customer.name} size="xl" />
        <strong>{item.customer.name || "Facebook хэрэглэгч"}</strong>
        <span>
          <PlatformBadge platform={item.platform} />{" "}
          <span className="account-pill">{item.page_name}</span>
        </span>
      </div>
      <div className="context-section">
        <h3>Харилцагч</h3>
        <dl>
          <div>
            <dt>Суваг</dt>
            <dd>Facebook</dd>
          </div>
          <div>
            <dt>Хаяг</dt>
            <dd>{item.page_name}</dd>
          </div>
        </dl>
      </div>
      <div className="context-section">
        <h3>Сүүлийн идэвх</h3>
        <div className="activity-item">
          <span className="activity-icon">
            <Icon name="message" size={16} />
          </span>
          <span>
            <strong>{item.last_message || "Мессеж алга"}</strong>
            <small>{dateTime(item.last_message_at)}</small>
          </span>
        </div>
      </div>
      <div className="context-section">
        <h3>Хариулах боломж</h3>
        <div className="reply-progress">
          <StatusBadge tone={item.can_reply ? "success" : "warning"}>
            {item.can_reply ? "Нээлттэй" : "Хаалттай"}
          </StatusBadge>
          <p>
            {item.can_reply
              ? "24 цагийн хариулах хугацаа хэвийн байна."
              : "Хэрэглэгчийн шинэ мессежийг хүлээнэ."}
          </p>
        </div>
      </div>
    </aside>
  );
}
