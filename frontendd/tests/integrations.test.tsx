import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { CommentAutomationSettings } from "@/components/integrations";
import { api } from "@/lib/api";
import type { Account, CommentAutomationRule } from "@/lib/types";

vi.mock("@/lib/api", () => ({ api: vi.fn(), post: vi.fn(), API_URL: "" }));

const account: Account = {
  id: "account",
  platform: "FACEBOOK_PAGE",
  display_name: "Демо дэлгүүр",
  status: "ACTIVE",
  last_synced_at: null,
  sync_status: "IDLE",
  last_error: "",
  webhook_subscribed_at: null,
};
const rule: CommentAutomationRule = {
  is_enabled: false,
  public_reply_enabled: true,
  public_reply_text: "Нийтийн хариу",
  private_reply_enabled: true,
  private_reply_text: "Хувийн мессеж",
  created_at: null,
  updated_at: null,
};

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(api).mockImplementation(async (_path, init) =>
    init?.method === "PUT" ? { ...rule, is_enabled: true } : rule,
  );
});

it("loads and saves the static comment automation configuration", async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <CommentAutomationSettings account={account} />
    </QueryClientProvider>,
  );
  await screen.findByRole("heading", { name: "Сэтгэгдлийн автомат хариу" });
  fireEvent.click(screen.getByRole("checkbox", { name: /Унтраалттай/ }));
  fireEvent.change(screen.getByLabelText("Демо дэлгүүр нийтийн хариу"), {
    target: { value: "Чатаа шалгаарай 😊" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Хадгалах" }));
  await screen.findByText("Тохиргоо хадгалагдлаа.");
  expect(api).toHaveBeenLastCalledWith(
    "/api/meta/accounts/account/comment-automation/",
    expect.objectContaining({
      method: "PUT",
      body: expect.stringContaining("Чатаа шалгаарай 😊"),
    }),
  );
});
