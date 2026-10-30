"""
Portfolio endpoints.

- GET  /api/candidates/{id}/portfolio   preview + settings (owner or recruiter)
- PUT  /api/candidates/{id}/portfolio   publish/unpublish, headline (owner only)
- GET  /api/portfolio/{slug}            the public page - no login needed,
                                        404 unless the owner published it
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import get_current_user
from ..services.portfolio import make_slug, portfolio_from_candidate
from .candidates import _get_visible_candidate

router = APIRouter(tags=["portfolio"])


class PortfolioSettings(BaseModel):
    is_public: bool
    headline: str | None = Field(default=None, max_length=120)


def _settings(candidate: models.Candidate) -> dict:
    portfolio = candidate.portfolio
    return {
        "is_public": bool(portfolio and portfolio.is_public),
        "slug": portfolio.slug if portfolio else None,
        "headline": portfolio.headline if portfolio else None,
        "portfolio": portfolio_from_candidate(candidate),
    }


@router.get("/api/candidates/{candidate_id}/portfolio")
def get_portfolio_settings(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Preview of the portfolio page plus whether it is published."""
    return _settings(_get_visible_candidate(candidate_id, db, current_user))


@router.put("/api/candidates/{candidate_id}/portfolio")
def update_portfolio_settings(
    candidate_id: int,
    body: PortfolioSettings,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Only the student who owns the candidate record can publish, unpublish
    or change the headline. The link (slug) is created on first save and
    kept afterwards, so a shared link keeps working if the page is
    unpublished and published again.
    """
    candidate = _get_visible_candidate(candidate_id, db, current_user)
    if candidate.user_id != current_user.user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the student can publish their portfolio.")

    portfolio = candidate.portfolio
    if portfolio is None:
        portfolio = models.Portfolio(
            candidate_id=candidate.candidate_id,
            slug=make_slug(candidate.name, candidate.candidate_id),
        )
        db.add(portfolio)

    portfolio.is_public = body.is_public
    headline = (body.headline or "").strip()
    portfolio.headline = headline or None
    db.commit()
    db.refresh(candidate)
    return _settings(candidate)


@router.get("/api/portfolio/{slug}")
def get_public_portfolio(slug: str, db: Session = Depends(get_db)):
    """The public portfolio page. Unpublished and unknown links look the same (404)."""
    portfolio = db.query(models.Portfolio).filter_by(slug=slug).first()
    if portfolio is None or not portfolio.is_public:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portfolio not found.")
    return portfolio_from_candidate(portfolio.candidate)
