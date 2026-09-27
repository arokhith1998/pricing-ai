// @vitest-environment jsdom
//
// Component-level coverage for the "success without navigation" bug: a
// 200 from /api/lead that never actually carries the visitor off the
// gated page (the honeypot returns this response on purpose, and a real
// save can succeed while the Set-Cookie is dropped). Written as plain
// React.createElement calls (no JSX) so this file can stay a .ts file and
// does not need to touch vitest.config.mts's test-file glob.
import { act } from "react";
import { createElement } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const replaceMock = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import LeadForm, { UNLOCK_TIMEOUT_MS } from "@/components/LeadForm";

function fillRequiredFields() {
  fireEvent.change(screen.getByPlaceholderText("Company email"), {
    target: { value: "person@acme.com" },
  });
  fireEvent.change(screen.getByPlaceholderText("Company"), {
    target: { value: "Acme Inc" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
}

describe("LeadForm", () => {
  beforeEach(() => {
    replaceMock.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("does not spin forever when the API returns 200 but the redirect bounces back (honeypot fake-success or a cookie that did not stick)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    );

    render(createElement(LeadForm));
    fillRequiredFields();

    const button = screen.getByRole("button", { name: /unlock the full diagnostic/i });
    fireEvent.click(button);

    // router.replace was called optimistically...
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/diagnostic"));
    // ...but in this test it never actually navigates anywhere (proxy.ts
    // bounced back and Next.js did not remount us), so the busy state must
    // eventually clear on its own instead of spinning forever. getByText
    // throws if the spinner label is not present, which is assertion enough.
    screen.getByText(/unlocking/i);

    await waitFor(
      () => screen.getByText(/that did not unlock/i),
      { timeout: UNLOCK_TIMEOUT_MS + 1500 },
    );

    const buttonAfter = screen.getByRole("button", { name: /unlock the full diagnostic/i });
    expect((buttonAfter as HTMLButtonElement).disabled).toBe(false);
  });

  it("does not touch state (and does not throw) once the component has unmounted after a real, successful unlock", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })),
    );
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { unmount } = render(createElement(LeadForm));
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /unlock the full diagnostic/i }));

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/diagnostic"));

    // Simulate the real-success case: the navigation actually left the
    // page, so React tears the component down before the watchdog fires.
    unmount();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, UNLOCK_TIMEOUT_MS + 500));
    });

    expect(errorSpy).not.toHaveBeenCalled();
  });

  it("names the honeypot field so autofill will not recognize it, while keeping it hidden from real visitors", () => {
    const { container } = render(createElement(LeadForm));
    const honeypot = container.querySelector('input[aria-hidden="true"]') as HTMLInputElement;

    expect(honeypot).toBeTruthy();
    // Password managers and Chrome autofill match on name/id/autocomplete
    // heuristics like "website", "url", "homepage". None of those may
    // appear in the honeypot's name.
    expect(honeypot.name.toLowerCase()).not.toMatch(/website|url|homepage/);
    expect(honeypot.autocomplete).toBe("new-password");
    expect(honeypot.tabIndex).toBe(-1);
  });
});
