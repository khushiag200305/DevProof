import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Navbar } from "./Navbar";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";

describe("Navbar phone menu", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 1, email: "k@thapar.edu", name: "Khushi", picture_url: null, role: "student" },
      loading: false, login: vi.fn(), logout: vi.fn(),
    });
    vi.spyOn(api, "apiGet").mockResolvedValue({ unread: 0, items: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("opens the menu, lists the student's pages, and closes after navigating", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/upload"]}>
        <Routes>
          <Route path="*" element={<Navbar />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByRole("navigation", { name: "Menu" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open menu" }));
    const menu = screen.getByRole("navigation", { name: "Menu" });
    expect(within(menu).getByRole("link", { name: "My resumes" })).toBeInTheDocument();
    await user.click(within(menu).getByRole("link", { name: "Practice" }));
    expect(screen.queryByRole("navigation", { name: "Menu" })).not.toBeInTheDocument();
  });
});
