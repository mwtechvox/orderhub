"use client";
import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post } from "@/lib/api";
import type { Account, Conversation, Message, Page } from "@/lib/types";
import { dateTime } from "@/lib/format";
import { useCompany } from "./shell";
import {
  AccountSelector,
  ChannelSelector,
  FilterBar,
  PlatformBadge,
  StatusBadge,
} from "./social-ui";
import { Composer, Empty, ErrorNotice, Pager } from "./ui";
const statuses = {
  RECEIVED: "Хүлээн авсан",
  PENDING: "Дараалалд",
  SENDING: "Илгээж байна",
  SENT: "Илгээсэн",
  FAILED: "Амжилтгүй",
};
export function MessageBubble({ message }: { message: Message }) {
  return (
    <div
      className={`bubble ${message.direction === "OUTBOUND" ? "outgoing" : "incoming"}`}
    >
      <p>{message.text}</p>
      {message.attachments.map((a, i) => (
        <a key={i} href={a.url} target="_blank" rel="noopener noreferrer">
          Хавсралт ↗
        </a>
      ))}
      <small>
        {dateTime(message.sent_at)} · {statuses[message.status]}
      </small>
      {message.status === "FAILED" && (
        <p role="status" className="message-error">
          {message.error_code === "META_DELIVERY_UNKNOWN"
            ? "Хүргэлтийг батлах боломжгүй. Messenger дээр шалгана уу."
            : "Илгээж чадсангүй. Холболт болон хариулах хугацааг шалгана уу."}
        </p>
      )}
    </div>
  );
}
export function ConversationList({
  items,
  selected,
  onSelect,
}: {
  items: Conversation[];
  selected: string | null;
  onSelect: (c: Conversation) => void;
}) {
  return (
    <div>
      {items.map((c) => (
        <button
          key={c.id}
          className={`conversation ${selected === c.id ? "selected" : ""}`}
          onClick={() => onSelect(c)}
        >
          <span className="customer-avatar">{(c.customer.name || "F")[0]}</span>
          <div className="conversation-body">
            <div className="conversation-title">
              <strong>{c.customer.name || "Facebook хэрэглэгч"}</strong>
              <small>{dateTime(c.last_message_at)}</small>
            </div>
            <p>{c.last_message || "Мессеж алга"}</p>
            <span className="channel-label">
              <PlatformBadge platform={c.platform} /> {c.page_name}
            </span>
          </div>
          {c.unread_count > 0 && (
            <span className="unread" aria-label={`${c.unread_count} уншаагүй`}>
              {c.unread_count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
export default function Inbox() {
  const company = useCompany();
  const cache = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("");
  const [account, setAccount] = useState("");
  const [error, setError] = useState<unknown>(null);
  const accounts = useQuery({
    queryKey: ["accounts", company],
    queryFn: () => api<Page<Account>>("/api/meta/accounts/"),
  });
  const platforms = [
    ...new Set((accounts.data?.results ?? []).map((item) => item.platform)),
  ];
  const conversations = useQuery({
    queryKey: ["conversations", company, page, search, platform, account],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), search });
      if (platform) params.set("platform", platform);
      if (account) params.set("social_account", account);
      return api<Page<Conversation>>(`/api/conversations/?${params}`);
    },
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });
  async function select(c: Conversation) {
    setSelected(c.id);
    try {
      await post(`/api/conversations/${c.id}/read/`);
      await cache.invalidateQueries({ queryKey: ["conversations", company] });
    } catch (err) {
      setError(err);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">FACEBOOK MESSENGER</p>
          <h1>Мессеж</h1>
          <p className="muted">Харилцагчдынхаа асуултад нэг дор хариулаарай.</p>
        </div>
        <span className="live-status">
          <span className="status-dot" /> 2 секунд тутам шинэчлэгдэнэ
        </span>
      </div>
      <ErrorNotice error={conversations.error || accounts.error || error} />
      <FilterBar>
        <ChannelSelector
          value={platform}
          platforms={platforms}
          onChange={(value) => {
            setPlatform(value);
            setAccount("");
            setPage(1);
            setSelected(null);
          }}
        />
        <AccountSelector
          value={account}
          accounts={accounts.data?.results ?? []}
          platform={platform}
          onChange={(value) => {
            setAccount(value);
            setPage(1);
            setSelected(null);
          }}
        />
      </FilterBar>
      <div className={`inbox ${selected ? "has-selection" : ""}`}>
        <section className="conversation-panel">
          <div className="conversation-search">
            <input
              aria-label="Харилцагч хайх"
              placeholder="Харилцагч хайх…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          {conversations.isLoading ? (
            <Empty>Ачаалж байна…</Empty>
          ) : (
            <ConversationList
              items={conversations.data?.results ?? []}
              selected={selected}
              onSelect={(c) => void select(c)}
            />
          )}{" "}
          {conversations.data?.count === 0 && (
            <Empty>Яриа алга. Facebook хуудсаа холбоод синк хийнэ үү.</Empty>
          )}
          <Pager
            page={page}
            count={conversations.data?.count ?? 0}
            onChange={setPage}
          />
        </section>
        <section className="chat-panel">
          {selected ? (
            <Chat
              key={selected}
              id={selected}
              onBack={() => setSelected(null)}
            />
          ) : (
            <Empty>
              <div className="chat-placeholder">✉</div>
              <h2>Яриа сонгоно уу</h2>
              <p>Харилцагчийн мессеж болон хариу энд харагдана.</p>
            </Empty>
          )}
        </section>
      </div>
    </>
  );
}
function Chat({ id, onBack }: { id: string; onBack: () => void }) {
  const company = useCompany();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const pending = useRef<{ text: string; key: string } | null>(null);
  const conversation = useQuery({
    queryKey: ["conversation", company, id],
    queryFn: () => api<Conversation>(`/api/conversations/${id}/`),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });
  const messages = useQuery({
    queryKey: ["messages", company, id, page],
    queryFn: () =>
      api<Page<Message>>(`/api/conversations/${id}/messages/?page=${page}`),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });
  const eligible = !!conversation.data?.can_reply;
  async function send(text: string) {
    if (!pending.current || pending.current.text !== text)
      pending.current = { text, key: crypto.randomUUID() };
    await post("/api/messages/send/", {
      conversation_id: id,
      text,
      idempotency_key: pending.current.key,
    });
    pending.current = null;
    setPage(1);
    await cache.invalidateQueries({ queryKey: ["messages", company, id] });
    await cache.invalidateQueries({ queryKey: ["conversations", company] });
  }
  return (
    <>
      <header className="chat-header">
        <button className="mobile-back" onClick={onBack}>
          ←
        </button>
        <span className="customer-avatar">
          {(conversation.data?.customer.name || "F")[0]}
        </span>
        <div>
          <strong>
            {conversation.data?.customer.name || "Facebook хэрэглэгч"}
          </strong>
          <small>
            {conversation.data && (
              <PlatformBadge platform={conversation.data.platform} />
            )}{" "}
            {conversation.data?.page_name}
          </small>
          {conversation.data && (
            <StatusBadge
              tone={conversation.data.can_reply ? "success" : "warning"}
            >
              {conversation.data.can_reply
                ? "Хариулах боломжтой"
                : "Хариулах хугацаа дууссан"}
            </StatusBadge>
          )}
        </div>
      </header>
      <ErrorNotice error={conversation.error || messages.error} />
      <div className="message-history">
        <Pager
          page={page}
          count={messages.data?.count ?? 0}
          onChange={setPage}
        />
        {messages.isLoading ? (
          <Empty>Мессеж ачаалж байна…</Empty>
        ) : (
          [...(messages.data?.results ?? [])]
            .reverse()
            .map((m) => <MessageBubble key={m.id} message={m} />)
        )}
      </div>
      <footer className="chat-composer">
        {!eligible && (
          <p className="muted">
            24 цагийн хариулах цонх дууссан. Хэрэглэгч дахин мессеж илгээсний
            дараа хариулах боломжтой.
          </p>
        )}
        <Composer maxLength={2000} disabled={!eligible} onSend={send} />
      </footer>
    </>
  );
}
