import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { JobFitPanel, type JobFitResult } from "./JobFitPanel";
import * as api from "../lib/api";

const result: JobFitResult = {
  skills: ["Docker", "PostgreSQL", "Python"],
  best_candidate_id: 1,
  reason: "Proves 2 of the 3 skills this job asks for. Your next best resume doesn't mention PostgreSQL.",
  tips: ["Docker: on this resume but not proven yet - push a project that uses it, or be ready to show it in the interview."],
  resumes: [
    {
      candidate_id: 1, name: "Backend resume", created_at: "2026-10-01T10:00:00Z", analyzed: true,
      visible_to_recruiters: false, proven: ["PostgreSQL", "Python"], claimed_only: ["Docker"], missing: [], fit: 80, best: true,
    },
    {
      candidate_id: 2, name: "Frontend resume", created_at: "2026-11-01T10:00:00Z", analyzed: true,
      visible_to_recruiters: true, proven: ["Python"], claimed_only: [], missing: ["Docker", "PostgreSQL"], fit: 33, best: false,
    },
  ],
};

describe("JobFitPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("ranks the resumes for a job and makes the best one visible", async () => {
    const post = vi.spyOn(api, "apiPost").mockResolvedValue(result);
    const onMakeVisible = vi.fn().mockResolvedValue(true);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <JobFitPanel onMakeVisible={onMakeVisible} />
      </MemoryRouter>
    );

    expect(screen.getByRole("button", { name: /find my best resume/i })).toBeDisabled();
    await user.type(screen.getByLabelText("Job description"), "Backend intern: Python, PostgreSQL, Docker.");
    await user.click(screen.getByRole("button", { name: /find my best resume/i }));

    expect(post).toHaveBeenCalledWith("/api/job-fit", { job_description: "Backend intern: Python, PostgreSQL, Docker." });
    const best = await screen.findByRole("listitem", { name: /^Backend resume/ });
    expect(within(best).getByText("Best for this job")).toBeInTheDocument();
    expect(within(best).getByText("80")).toBeInTheDocument();
    expect(within(best).getByText("Docker")).toBeInTheDocument();
    expect(screen.getByText(/Your next best resume doesn't mention PostgreSQL/)).toBeInTheDocument();

    await user.click(within(best).getByRole("button", { name: "Make visible" }));
    expect(onMakeVisible).toHaveBeenCalledWith(1);
    expect(await within(best).findByText("Visible to recruiters")).toBeInTheDocument();
    const other = screen.getByRole("listitem", { name: /^Frontend resume/ });
    expect(within(other).getByRole("button", { name: "Make visible" })).toBeInTheDocument();
  });

  it("says so when the job mentions no known skills", async () => {
    vi.spyOn(api, "apiPost").mockResolvedValue({ skills: [], resumes: [], best_candidate_id: null, reason: null, tips: [] });
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <JobFitPanel onMakeVisible={vi.fn()} />
      </MemoryRouter>
    );
    await user.type(screen.getByLabelText("Job description"), "Great communicator");
    await user.click(screen.getByRole("button", { name: /find my best resume/i }));
    expect(await screen.findByText(/No skills from DevProof's catalog/)).toBeInTheDocument();
  });
});
