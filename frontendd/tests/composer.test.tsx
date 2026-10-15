import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Composer } from "@/components/ui";
describe("Composer", () => {
  it("submits once and disables while sending", async () => {
    let resolve: () => void = () => {};
    const send = vi.fn(
      () =>
        new Promise<void>((r) => {
          resolve = r;
        }),
    );
    render(<Composer onSend={send} />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Сайн байна уу?" },
    });
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toBeDisabled();
    expect(send).toHaveBeenCalledWith("Сайн байна уу?");
    resolve();
    await waitFor(() => expect(screen.getByRole("textbox")).toHaveValue(""));
  });
  it("preserves draft after API failure", async () => {
    render(
      <Composer
        onSend={async () => {
          throw new Error("Холболтын алдаа");
        }}
      />,
    );
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Хариу" },
    });
    fireEvent.click(screen.getByRole("button"));
    await screen.findByRole("alert");
    expect(screen.getByRole("textbox")).toHaveValue("Хариу");
  });
});

it("enforces message length and blocks a disabled form", () => {
  const send = vi.fn();
  render(<Composer onSend={send} disabled maxLength={2000} />);
  expect(screen.getByRole("textbox")).toHaveAttribute("maxlength", "2000");
  expect(screen.getByRole("button")).toBeDisabled();
  expect(send).not.toHaveBeenCalled();
});
