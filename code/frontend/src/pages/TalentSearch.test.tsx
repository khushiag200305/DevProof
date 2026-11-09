import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TalentSearch } from "./TalentSearch";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";
import type { Comparison, SavedSearch, TalentResult } from "../lib/talent";

const aditi: TalentResult = {
  candidate_id: 1,
  name: "Aditi Sharma",
  email: "aditi@thapar.edu",
  github_username: "aditi",
  created_at: "2026-11-01T10:00:00Z",
  skill_count: 9,
  original_repos: 4,
  last_active: "2026-11-01T10:00:00Z",
  matched: [{ skill: "Python", status: "Strong Evidence", score: 100 }],
  missing: [],
  match_score: 100,
  shortlisted: false,
};

const rohit: TalentResult = {
  ...aditi,
  candidate_id: 2,
  name: "Rohit Singhal",
  github_username: "rohit",
  matched: [{ skill: "Python", status: "Good Evidence", score: 70 }],
  match_score: 70,
};

const saved: SavedSearch = {
  search_id: 5,
  name: "Backend interns",
  query: { skills: ["Python"], min_level: "good", match: "all", has_github: false, min_repos: 0, active_months: null, text: "" },
  created_at: "2026-11-01T10:00:00Z",
  last_run_at: "2026-11-01T10:00:00Z",
  match_count: 2,
  new_count: 1,
};

describe("TalentSearch page", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 9, email: "hr@acme.com", name: "HR", picture_url: null, role: "recruiter" },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
    vi.spyOn(api, "apiGet").mockImplementation(async (path: string) => {
      if (path === "/api/talent/skills") return ["Python", "React"];
      if (path === "/api/talent/saved-searches") return [saved];
      if (path === "/api/talent/shortlist") return [];
      if (path.startsWith("/api/talent/compare")) {
        const data: Comparison = {
          candidates: [
            { candidate_id: 1, name: "Aditi Sharma", github_username: "aditi", original_repos: 4, last_active: null, backed_skills: 5, skill_count: 9 },
            { candidate_id: 2, name: "Rohit Singhal", github_username: "rohit", original_repos: 2, last_active: null, backed_skills: 3, skill_count: 7 },
          ],
          rows: [{ skill: "Python", cells: [{ status: "Strong Evidence", score: 100 }, null] }],
        };
        return data;
      }
      throw new Error(`unexpected GET ${path}`);
    });
    vi.spyOn(api, "apiPost").mockImplementation(async (path: string) => {
      if (path === "/api/talent/search") return [aditi, rohit];
      if (path === "/api/talent/saved-searches/5/run") return { search: saved, results: [{ ...rohit, is_new: true }] };
      throw new Error(`unexpected POST ${path}`);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderPage() {
    return render(
      <MemoryRouter>
        <TalentSearch />
      </MemoryRouter>
    );
  }

  it("searches by the skills added, at the chosen evidence level", async () => {
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByRole("listitem", { name: "Aditi Sharma" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Skills"), "python{Enter}");
    await user.click(screen.getByRole("button", { name: "Strong" }));
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() =>
      expect(api.apiPost).toHaveBeenLastCalledWith(
        "/api/talent/search",
        expect.objectContaining({ skills: ["Python"], min_level: "strong", match: "all" })
      )
    );
    const row = await screen.findByRole("listitem", { name: "Aditi Sharma" });
    expect(within(row).getByText("Python")).toBeInTheDocument();
    expect(within(row).getByText("Strong 100")).toBeInTheDocument();
  });

  it("re-runs a saved search and marks new matches", async () => {
    const user = userEvent.setup();
    renderPage();
    const savedList = await screen.findByRole("region", { name: "Saved searches" });
    expect(within(savedList).getByText("Backend interns")).toBeInTheDocument();

    await user.click(within(savedList).getByText("Backend interns"));

    const row = await screen.findByRole("listitem", { name: "Rohit Singhal" });
    expect(within(row).getByText("New")).toBeInTheDocument();
    expect(screen.queryByRole("listitem", { name: "Aditi Sharma" })).not.toBeInTheDocument();
  });

  it("stars a candidate into the shortlist", async () => {
    const put = vi.spyOn(api, "apiPut").mockResolvedValue({});
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Add Aditi Sharma to shortlist" }));

    expect(put).toHaveBeenCalledWith("/api/talent/shortlist/1", { note: null });
    expect(screen.getByRole("button", { name: "Remove Aditi Sharma from shortlist" })).toBeInTheDocument();
  });

  it("compares the selected candidates side by side", async () => {
    const user = userEvent.setup();
    renderPage();
    const aditiRow = await screen.findByRole("listitem", { name: "Aditi Sharma" });
    const rohitRow = screen.getByRole("listitem", { name: "Rohit Singhal" });

    await user.click(within(aditiRow).getByRole("checkbox", { name: "Compare" }));
    expect(screen.getByRole("button", { name: /compare 1/i })).toBeDisabled();
    await user.click(within(rohitRow).getByRole("checkbox", { name: "Compare" }));
    await user.click(screen.getByRole("button", { name: /compare 2/i }));

    const table = await screen.findByRole("region", { name: "Compare candidates" });
    expect(api.apiGet).toHaveBeenCalledWith("/api/talent/compare?ids=1,2");
    expect(within(table).getByText("Not on resume")).toBeInTheDocument();
  });
});
