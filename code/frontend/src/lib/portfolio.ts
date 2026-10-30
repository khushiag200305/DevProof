/** Shapes returned by the portfolio endpoints (backend: app/services/portfolio.py). */

export interface PortfolioSkill {
  name: string;
  score: number | null;
  status: string;
}

export interface PortfolioProject {
  name: string;
  url: string;
  description: string | null;
  language: string | null;
  topics: string[];
  homepage: string | null;
  stars: number;
  technologies: string[];
  highlights: string[];
  commit_count: number;
  active: string | null;
}

export interface PortfolioData {
  name: string;
  headline: string | null;
  github_username: string | null;
  github_url: string | null;
  analyzed: boolean;
  skill_groups: { category: string; skills: PortfolioSkill[] }[];
  also_listed: string[];
  projects: PortfolioProject[];
  stats: {
    verified_skills: number;
    original_repos: number;
    commits: number;
    top_languages: string[];
  };
}

export interface PortfolioSettings {
  is_public: boolean;
  slug: string | null;
  headline: string | null;
  portfolio: PortfolioData;
}

export function portfolioUrl(slug: string): string {
  return `${window.location.origin}/p/${slug}`;
}
