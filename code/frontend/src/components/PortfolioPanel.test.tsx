import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PortfolioPanel } from "./PortfolioPanel";
import * as api from "../lib/api";
import type { PortfolioSettings } from "../lib/portfolio";
import { samplePortfolio } from "../lib/portfolio.fixtures";

const privateSettings: PortfolioSettings = {
  is_public: false,
  slug: null,
  headline: null,
  portfolio: samplePortfolio,
};

describe("PortfolioPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("publishes the portfolio with a headline and shows the public link", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(privateSettings);
    const put = vi.spyOn(api, "apiPut").mockResolvedValue({
      ...privateSettings,
      is_public: true,
      slug: "aditi-sharma-abc123",
      headline: "Backend developer",
    });

    const user = userEvent.setup();
    render(<PortfolioPanel candidateId={7} refreshKey={0} />);

    expect(await screen.findByText("Private")).toBeInTheDocument();
    expect(api.apiGet).toHaveBeenCalledWith("/api/candidates/7/portfolio");

    await user.type(screen.getByLabelText("Headline"), "Backend developer");
    await user.click(screen.getByRole("button", { name: "Publish portfolio" }));

    await waitFor(() =>
      expect(put).toHaveBeenCalledWith("/api/candidates/7/portfolio", {
        is_public: true,
        headline: "Backend developer",
      })
    );
    expect(await screen.findByText("Public")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /\/p\/aditi-sharma-abc123$/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Make private" })).toBeInTheDocument();
  });

  it("shows a preview of the page on request", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(privateSettings);
    const user = userEvent.setup();
    render(<PortfolioPanel candidateId={7} refreshKey={0} />);

    await user.click(await screen.findByRole("button", { name: "Preview" }));
    expect(screen.getByRole("heading", { name: "Aditi Sharma" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide preview" })).toBeInTheDocument();
  });

  it("shows the server's error if publishing fails", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(privateSettings);
    vi.spyOn(api, "apiPut").mockRejectedValue(
      new api.ApiError(403, "Only the student can publish their portfolio.")
    );
    const user = userEvent.setup();
    render(<PortfolioPanel candidateId={7} refreshKey={0} />);

    await user.click(await screen.findByRole("button", { name: "Publish portfolio" }));
    expect(await screen.findByText(/Only the student can publish/)).toBeInTheDocument();
  });
});
