import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ResumeBullets, type BulletReport } from "./ResumeBullets";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";

const report: BulletReport = {
  job_match: {
    skills: ["PostgreSQL", "Python", "React"],
    proven: ["Python"],
    claimed_only: ["React"],
    missing: ["PostgreSQL"],
    readiness: 33,
    tips: ["React: on your resume, but no repository shows it yet - add a small project that uses it, or remove it from the resume."],
  },
  projects: [
    {
      name: "shop-api",
      title: "Shop API",
      url: "https://github.com/octocat/shop-api",
      matched_skills: ["Python"],
      bullets: [
        { text: "Built Shop API, REST API for an online shop using Python and Docker.", skills: ["Python", "Docker"] },
        { text: "Wrote automated tests for the core functionality.", skills: [] },
      ],
    },
  ],
};

describe("ResumeBullets page", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 1, email: "s@thapar.edu", name: "S", picture_url: null, role: "student" },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={["/candidate/7/bullets"]}>
        <Routes>
          <Route path="/candidate/:candidateId/bullets" element={<ResumeBullets />} />
        </Routes>
      </MemoryRouter>
    );
  }

  it("sends the job description and shows the job match and project lines", async () => {
    const post = vi.spyOn(api, "apiPost").mockResolvedValue(report);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/job description/i), "Backend intern: Python, React, PostgreSQL");
    await user.click(screen.getByRole("button", { name: /generate resume lines/i }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/candidates/7/resume-bullets", {
        job_description: "Backend intern: Python, React, PostgreSQL",
      })
    );
    expect(await screen.findByText("33% of the job's skills proven")).toBeInTheDocument();
    expect(screen.getByText("Proven on GitHub")).toBeInTheDocument();
    expect(screen.getByText("Missing from your resume")).toBeInTheDocument();

    const project = screen.getByRole("region", { name: "Shop API" });
    expect(within(project).getByText(/Built Shop API, REST API for an online shop/)).toBeInTheDocument();
    expect(within(project).getByText("Matches the job: Python")).toBeInTheDocument();
    expect(within(project).getByRole("button", { name: "Copy all" })).toBeInTheDocument();
  });

  it("works without a job description", async () => {
    const post = vi.spyOn(api, "apiPost").mockResolvedValue({ ...report, job_match: null });
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /generate resume lines/i }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/candidates/7/resume-bullets", { job_description: null })
    );
    expect(await screen.findByText(/Wrote automated tests/)).toBeInTheDocument();
    expect(screen.queryByText("Job match")).not.toBeInTheDocument();
  });

  it("shows the server's message when no analysis has been run", async () => {
    vi.spyOn(api, "apiPost").mockRejectedValue(
      new api.ApiError(400, "Run the GitHub analysis first - resume lines are built from your repositories.")
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /generate resume lines/i }));
    expect(await screen.findByText(/Run the GitHub analysis first/)).toBeInTheDocument();
  });
});
