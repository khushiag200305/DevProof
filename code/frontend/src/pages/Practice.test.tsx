import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Practice } from "./Practice";
import * as AuthContextModule from "../context/AuthContext";
import * as api from "../lib/api";
import type { QuizInProgress, QuizResult } from "../lib/quiz";

const attempt: QuizInProgress = {
  attempt_id: 3, kind: "practice", status: "in_progress", skills: ["Docker"],
  started_at: "2026-11-14T10:00:00Z", deadline: null, time_limit_seconds: null,
  questions: [
    { id: "docker-1", skill: "Docker", question: "What is a container?", options: ["A file", "A running image", "A VM", "A port"] },
    { id: "docker-2", skill: "Docker", question: "Which file builds an image?", options: ["Dockerfile", "README", "Makefile", "package.json"] },
  ],
};

const result: QuizResult = {
  attempt_id: 3, kind: "practice", status: "submitted", skills: ["Docker"], started_at: "", submitted_at: "", over_time: false,
  score: 1, total: 2, percent: 50, per_skill: [{ skill: "Docker", correct: 1, total: 2 }],
  questions: [
    { ...attempt.questions[0], chosen: 1, correct: 1, is_correct: true, explanation: "Containers run images." },
    { ...attempt.questions[1], chosen: 2, correct: 0, is_correct: false, explanation: "A Dockerfile lists the build steps." },
  ],
};

describe("Practice page", () => {
  beforeEach(() => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      user: { user_id: 1, email: "k@thapar.edu", name: "K", picture_url: null, role: "student" },
      loading: false, login: vi.fn(), logout: vi.fn(),
    });
    vi.spyOn(api, "apiGet").mockImplementation(async (path: string) => {
      if (path === "/api/quiz/skills") {
        return {
          skills: [{ name: "Docker", category: "Cloud & DevOps", questions: 5 }, { name: "Python", category: "Programming Languages", questions: 5 }],
          suggested: ["Docker"], counts: [5, 10, 15],
        };
      }
      if (path === "/api/quiz/attempts") return [];
      return { unread: 0, items: [] };
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("practises unproven skills, answers, and shows the explanations", async () => {
    const post = vi.spyOn(api, "apiPost").mockImplementation(async (path: string) => {
      if (path === "/api/quiz/practice") return attempt;
      if (path === "/api/quiz/attempts/3/submit") return result;
      throw new Error(path);
    });
    const user = userEvent.setup();
    render(<MemoryRouter><Practice /></MemoryRouter>);

    expect(await screen.findByText(/From the resume visible to recruiters: Docker/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /practise these/i }));
    expect(post).toHaveBeenCalledWith("/api/quiz/practice", { skills: ["Docker"], count: 10, timed: false });

    expect(await screen.findByText("Question 1 of 2")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /A running image/ }));
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("radio", { name: /A VM/ }));
    await user.click(screen.getByRole("button", { name: "Submit answers" }));

    expect(post).toHaveBeenCalledWith("/api/quiz/attempts/3/submit", { answers: { "docker-1": 1, "docker-2": 2 } });
    const results = await screen.findByRole("region", { name: "Quiz result" });
    expect(within(results).getByText("50%")).toBeInTheDocument();
    expect(within(results).getByText("A Dockerfile lists the build steps.")).toBeInTheDocument();
    expect(within(results).getByText(/Dockerfile \(correct answer\)/)).toBeInTheDocument();
  });

  it("needs at least one skill picked to start", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Practice /></MemoryRouter>);
    const startButton = await screen.findByRole("button", { name: "Start practice" });
    expect(startButton).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Python" }));
    expect(startButton).toBeEnabled();
  });
});
