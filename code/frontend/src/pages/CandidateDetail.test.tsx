import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CandidateDetail } from "./CandidateDetail";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";

const baseCandidate = {
  candidate_id: 7,
  name: "Aditi Sharma",
  email: "aditi@thapar.edu",
  github_username: "aditisharma-dev",
  created_at: "2026-09-20T10:00:00Z",
  skill_count: 2,
  repos_analyzed: 0,
  analyzed: false,
  skills: [
    { skill_name: "Docker", status: null, score: null, reasons: [], interview_question: null, supporting_repos: [] },
    { skill_name: "React", status: null, score: null, reasons: [], interview_question: null, supporting_repos: [] },
  ],
  projects: [],
};

const analyzedCandidate = {
  ...baseCandidate,
  repos_analyzed: 3,
  analyzed: true,
  skills: [
    {
      skill_name: "Docker",
      status: "Strong Evidence",
      score: 80,
      reasons: ["shop-api: Dockerfile present", "shop-api: original repository, not a fork"],
      interview_question: null,
      supporting_repos: [
        { repo: "docker-practice", score: 60 },
        { repo: "DevProof", score: 40 },
      ],
    },
    {
      skill_name: "React",
      status: "Needs Verification",
      score: 0,
      reasons: ["No supporting evidence found in analyzed repositories"],
      interview_question: "Walk me through how you structured components in one of your React projects.",
      supporting_repos: [],
    },
  ],
};

describe("CandidateDetail page", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 2, email: "r@acme.com", name: "R", picture_url: null, role: "recruiter" },
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
      <MemoryRouter initialEntries={["/candidate/7"]}>
        <Routes>
          <Route path="/candidate/:candidateId" element={<CandidateDetail />} />
        </Routes>
      </MemoryRouter>
    );
  }

  it("shows skills as pending before any analysis has run", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(baseCandidate);
    renderPage();

    await waitFor(() => expect(screen.getByText("Aditi Sharma")).toBeInTheDocument());
    expect(screen.getAllByText("Pending Analysis")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /analyze github evidence/i })).toBeEnabled();
    expect(api.apiGet).toHaveBeenCalledWith("/api/candidates/7");
  });

  it("runs the analysis and shows scores, reasons and interview questions", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(baseCandidate);
    vi.spyOn(api, "apiPost").mockResolvedValue(analyzedCandidate);

    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /analyze github evidence/i }));

    await waitFor(() => expect(screen.getByText(/Strong Evidence · 80\/100/)).toBeInTheDocument());
    expect(api.apiPost).toHaveBeenCalledWith("/api/candidates/7/analyze");
    expect(screen.getByText("shop-api: Dockerfile present")).toBeInTheDocument();
    expect(screen.getByText(/Needs Verification · 0\/100/)).toBeInTheDocument();
    expect(screen.getByText(/structured components in one of your React projects/)).toBeInTheDocument();
    expect(screen.getByText(/Scored against 3 public GitHub repositories/)).toBeInTheDocument();
    expect(screen.getByText("docker-practice (60), DevProof (40)")).toBeInTheDocument();
    expect(screen.getAllByText(/Also supported by/)).toHaveLength(1);
    expect(screen.getByRole("button", { name: /re-run analysis/i })).toBeInTheDocument();
  });

  it("shows the API error when the analysis fails", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(baseCandidate);
    vi.spyOn(api, "apiPost").mockRejectedValue(
      new api.ApiError(502, "GitHub API error 403 (rate limit reached: set GITHUB_TOKEN in .env)")
    );

    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: /analyze github evidence/i }));

    await waitFor(() => expect(screen.getByText(/rate limit reached/)).toBeInTheDocument());
  });

  it("hides the analyze button when the resume has no GitHub username", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue({ ...baseCandidate, github_username: null });
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("No GitHub username on this resume")).toBeInTheDocument()
    );
    expect(screen.queryByRole("button", { name: /analyze/i })).not.toBeInTheDocument();
  });
});
