import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MatchJob } from "./MatchJob";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";

describe("Match a job page", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 1, email: "k@thapar.edu", name: "K", picture_url: null, role: "student" },
      loading: false, login: vi.fn(), logout: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the role picker once the student has a resume", async () => {
    vi.spyOn(api, "apiGet").mockImplementation(async (path: string) => {
      if (path === "/api/candidates/me") return [{ candidate_id: 8, visible_to_recruiters: true }];
      if (path === "/api/job-fit/roles") return [{ name: "Data Analyst", skills: ["Python", "SQL"] }];
      return { unread: 0, items: [] };
    });
    render(<MemoryRouter><MatchJob /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Choose a job or role" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Pick a role" })).toBeInTheDocument();
  });

  it("asks for a resume first when there are none", async () => {
    vi.spyOn(api, "apiGet").mockImplementation(async (path: string) =>
      path === "/api/candidates/me" ? [] : { unread: 0, items: [] }
    );
    render(<MemoryRouter><MatchJob /></MemoryRouter>);
    expect(await screen.findByText("Upload a resume first")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to My resumes" })).toHaveAttribute("href", "/upload");
  });
});
