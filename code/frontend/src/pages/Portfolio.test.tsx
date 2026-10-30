import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Portfolio } from "./Portfolio";
import * as api from "../lib/api";
import { samplePortfolio } from "../lib/portfolio.fixtures";

function renderAt(slug: string) {
  return render(
    <MemoryRouter initialEntries={[`/p/${slug}`]}>
      <Routes>
        <Route path="/p/:slug" element={<Portfolio />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Public portfolio page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows verified skills, projects and stats", async () => {
    vi.spyOn(api, "apiGet").mockResolvedValue(samplePortfolio);
    renderAt("aditi-sharma-abc123");

    expect(await screen.findByRole("heading", { name: "Aditi Sharma" })).toBeInTheDocument();
    expect(api.apiGet).toHaveBeenCalledWith("/api/portfolio/aditi-sharma-abc123");
    expect(screen.getByText("Backend developer")).toBeInTheDocument();
    expect(screen.getByText(/Python · 100/)).toBeInTheDocument();
    expect(screen.getByText(/Docker · 60/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "shop-api" })).toHaveAttribute(
      "href",
      "https://github.com/aditisharma-dev/shop-api"
    );
    expect(screen.getByText(/Automated tests/)).toBeInTheDocument();
    expect(screen.getByText("38 commits")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live demo" })).toBeInTheDocument();
    expect(screen.getByText("Python, TypeScript")).toBeInTheDocument();
    expect(screen.getByText(/Object-Oriented Programming/)).toBeInTheDocument();
  });

  it("explains when a portfolio is private or missing", async () => {
    vi.spyOn(api, "apiGet").mockRejectedValue(new api.ApiError(404, "Portfolio not found."));
    renderAt("nope");

    expect(await screen.findByText(/private or doesn't exist/)).toBeInTheDocument();
  });
});
