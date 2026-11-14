import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NotificationBell } from "./NotificationBell";
import * as api from "../lib/api";

const items = [
  {
    notification_id: 2, kind: "search_match", title: 'New match for "Python devs"', body: "Aarav Mehta matches your saved search.",
    link: "/candidate/7", created_at: new Date().toISOString(), read: false,
  },
  {
    notification_id: 1, kind: "recruiter_approved", title: "Your recruiter account was approved", body: null,
    link: "/dashboard", created_at: "2026-11-01T10:00:00Z", read: true,
  },
];

describe("NotificationBell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderBell() {
    return render(
      <MemoryRouter initialEntries={["/talent"]}>
        <NotificationBell />
        <Routes>
          <Route path="/talent" element={<p>Talent page</p>} />
          <Route path="/candidate/:id" element={<p>Candidate page</p>} />
        </Routes>
      </MemoryRouter>
    );
  }

  it("shows the unread count and opens the linked page", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue({ unread: 1, items });
    const post = vi.spyOn(api, "apiPost").mockResolvedValue({});
    const user = userEvent.setup();
    renderBell();

    const bell = await screen.findByRole("button", { name: "Notifications, 1 unread" });
    await user.click(bell);
    expect(screen.getByRole("dialog", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByText("Aarav Mehta matches your saved search.")).toBeInTheDocument();
    expect(screen.getByText("Just now")).toBeInTheDocument();

    await user.click(screen.getByText('New match for "Python devs"'));
    expect(post).toHaveBeenCalledWith("/api/notifications/2/read");
    expect(screen.getByText("Candidate page")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
  });

  it("marks everything as read", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue({ unread: 1, items });
    const post = vi.spyOn(api, "apiPost").mockResolvedValue({});
    const user = userEvent.setup();
    renderBell();

    await user.click(await screen.findByRole("button", { name: "Notifications, 1 unread" }));
    await user.click(screen.getByRole("button", { name: "Mark all as read" }));
    expect(post).toHaveBeenCalledWith("/api/notifications/read-all");
    expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
  });

  it("says when there is nothing new", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue({ unread: 0, items: [] });
    const user = userEvent.setup();
    renderBell();
    await user.click(screen.getByRole("button", { name: "Notifications" }));
    expect(await screen.findByText(/You're all caught up/)).toBeInTheDocument();
  });
});
