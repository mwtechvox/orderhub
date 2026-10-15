import { render, screen, fireEvent } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { ConversationList, MessageBubble } from "@/components/inbox";
import type { Conversation, Message } from "@/lib/types";
it("lists and selects a conversation", () => {
  const c: Conversation = {
    id: "c",
    customer: { id: "u", name: "Бат" },
    social_account: "p",
    platform: "FACEBOOK_PAGE",
    page_name: "Shop",
    last_message: "Үнэ?",
    last_message_at: null,
    unread_count: 2,
    last_inbound_at: null,
    can_reply: false,
  };
  const select = vi.fn();
  render(<ConversationList items={[c]} selected={null} onSelect={select} />);
  expect(screen.getByText("Үнэ?")).toBeInTheDocument();
  expect(screen.getByLabelText("2 уншаагүй")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button"));
  expect(select).toHaveBeenCalledWith(c);
});
it("renders failed outbound status without retrying ambiguous delivery", () => {
  const message: Message = {
    id: "m",
    conversation: "c",
    direction: "OUTBOUND",
    text: "Сайн уу",
    attachments: [],
    status: "FAILED",
    sent_at: "2026-10-13T10:00:00Z",
    error_code: "META_DELIVERY_UNKNOWN",
  };
  render(<MessageBubble message={message} />);
  expect(screen.getByText("Сайн уу")).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent(
    "Messenger дээр шалгана уу",
  );
  expect(screen.queryByRole("button")).toBeNull();
});
