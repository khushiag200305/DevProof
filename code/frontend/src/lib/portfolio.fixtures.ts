/** Sample portfolio data shared by the portfolio tests. */
import type { PortfolioData } from "./portfolio";

export const samplePortfolio: PortfolioData = {
  name: "Aditi Sharma",
  headline: "Backend developer",
  github_username: "aditisharma-dev",
  github_url: "https://github.com/aditisharma-dev",
  analyzed: true,
  skill_groups: [
    {
      category: "Programming Languages",
      skills: [{ name: "Python", score: 100, status: "Strong Evidence" }],
    },
    {
      category: "Cloud & DevOps",
      skills: [{ name: "Docker", score: 60, status: "Good Evidence" }],
    },
  ],
  also_listed: ["Object-Oriented Programming"],
  projects: [
    {
      name: "shop-api",
      url: "https://github.com/aditisharma-dev/shop-api",
      description: "REST API for an online shop",
      language: "Python",
      topics: ["fastapi"],
      homepage: "https://shop.example.com",
      stars: 4,
      technologies: ["Docker", "Python"],
      highlights: ["Automated tests", "Continuous integration"],
      commit_count: 38,
      active: "Mar 2026 - Oct 2026",
    },
  ],
  stats: { verified_skills: 2, original_repos: 3, commits: 52, top_languages: ["Python", "TypeScript"] },
};
