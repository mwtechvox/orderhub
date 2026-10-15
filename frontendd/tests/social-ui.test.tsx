import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { AccountSelector, PlatformBadge } from "@/components/social-ui";

it("renders a provider-neutral platform badge", () => {
  render(<PlatformBadge platform="FACEBOOK_PAGE" />);
  expect(screen.getByText("Facebook")).toBeInTheDocument();
});

it("limits account choices to the selected channel", () => {
  const onChange = vi.fn();
  render(
    <AccountSelector
      value=""
      platform="FACEBOOK_PAGE"
      onChange={onChange}
      accounts={[
        {
          id: "facebook",
          platform: "FACEBOOK_PAGE",
          display_name: "Page",
          status: "ACTIVE",
          last_synced_at: null,
          sync_status: "IDLE",
          last_error: "",
          webhook_subscribed_at: null,
        },
        {
          id: "instagram",
          platform: "INSTAGRAM",
          display_name: "IG",
          status: "ACTIVE",
          last_synced_at: null,
          sync_status: "IDLE",
          last_error: "",
          webhook_subscribed_at: null,
        },
      ]}
    />,
  );
  expect(screen.getByRole("option", { name: "Page" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "IG" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Хаяг"), {
    target: { value: "facebook" },
  });
  expect(onChange).toHaveBeenCalledWith("facebook");
});
