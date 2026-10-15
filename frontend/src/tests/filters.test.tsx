import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Filters from "@/components/social/Filters";
import type { Account } from "@/types/api";

const account: Account = {
  id: "account-1",
  platform: "FACEBOOK_PAGE",
  external_account_id: "page-1",
  display_name: "Nyabo Store",
  status: "ACTIVE",
  last_synced_at: null,
  last_token_check_at: null,
  sync_status: "IDLE",
  last_error: "",
  webhook_subscribed_at: null,
};

describe("social filters", () => {
  it("renders backend accounts and emits controlled filter changes", () => {
    const onPlatformChange = vi.fn();
    const onAccountChange = vi.fn();
    const onSearchChange = vi.fn();
    render(
      <Filters
        accounts={[account]}
        platform=""
        account=""
        search=""
        searchPlaceholder="Нийтлэл хайх..."
        onPlatformChange={onPlatformChange}
        onAccountChange={onAccountChange}
        onSearchChange={onSearchChange}
      />,
    );
    expect(screen.getByRole("option", { name: "Nyabo Store" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Суваг"), {
      target: { value: "FACEBOOK_PAGE" },
    });
    fireEvent.change(screen.getByLabelText("Хаяг"), {
      target: { value: "account-1" },
    });
    fireEvent.change(screen.getByLabelText("Нийтлэл хайх..."), {
      target: { value: "linen" },
    });
    expect(onPlatformChange).toHaveBeenCalledWith("FACEBOOK_PAGE");
    expect(onAccountChange).toHaveBeenCalledWith("account-1");
    expect(onSearchChange).toHaveBeenCalledWith("linen");
  });
});
