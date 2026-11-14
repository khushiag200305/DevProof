import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SkillTestsPanel } from "./SkillTestsPanel";
import * as api from "../lib/api";
import type { SkillTest } from "../lib/skillTests";

const done: SkillTest = {
  test_id: 2, skills: ["Python"], question_count: 5, time_limit_minutes: 10, message: null,
  created_at: "2026-11-10T09:00:00Z", expires_at: "2026-11-17T09:00:00Z", status: "done",
  score: 4, total: 5, submitted_at: "2026-11-11T09:00:00Z", attempt_id: 8,
  per_skill: [{ skill: "Python", correct: 4, total: 5 }], student_name: "Aditi", candidate_id: 7,
};

describe("SkillTestsPanel", () => {
  beforeEach(() => {
    vi.spyOn(api, "apiGet").mockImplementation(async (path: string) => {
      if (path === "/api/skill-tests/skills") return { skills: ["Python", "Docker", "React"], counts: [5, 10, 15] };
      if (path === "/api/skill-tests/candidate/7") return [done];
      throw new Error(path);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("offers only testable resume skills, preselects unproven ones, and sends a test", async () => {
    const post = vi.spyOn(api, "apiPost").mockImplementation(async () => ({
      ...done, test_id: 3, skills: ["Docker"], status: "waiting", score: null, per_skill: undefined, attempt_id: null,
    }));
    const user = userEvent.setup();
    render(<SkillTestsPanel candidateId={7} resumeSkills={["Python", "Docker", "Kubernetes"]} suggested={["Docker", "Kubernetes"]} />);

    expect(await screen.findByRole("button", { name: "Docker" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Python" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("button", { name: "Kubernetes" })).not.toBeInTheDocument();

    const existing = await screen.findByRole("listitem", { name: "Test on Python" });
    expect(within(existing).getByText("4/5")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Message/), "See you Friday");
    await user.click(screen.getByRole("button", { name: "Send test" }));
    expect(post).toHaveBeenCalledWith("/api/skill-tests", {
      candidate_id: 7, skills: ["Docker"], question_count: 10, time_limit_minutes: 15, message: "See you Friday",
    });
    expect(await screen.findByText(/The student has been notified/)).toBeInTheDocument();
    const sent = screen.getByRole("listitem", { name: "Test on Docker" });
    expect(within(sent).getByText("Not started")).toBeInTheDocument();
    expect(within(sent).getByRole("button", { name: "Cancel test" })).toBeInTheDocument();
  });
});
