"""GitHub client cache and rate-limit detection (no network)."""
import asyncio
import time

import httpx
import pytest

from app.services import fingerprinting, github_client
from app.services.analysis import rate_limit_message
from app.services.github_client import GitHubRateLimitError, cache_clear, cache_get, cache_put, check_rate_limit


def setup_function():
    cache_clear()


def test_cache_put_get_and_expiry():
    cache_put(("a",), [1], ttl=60)
    assert cache_get(("a",)) == [1]
    cache_put(("b",), [2], ttl=-1)
    assert cache_get(("b",)) is None


def test_rate_limit_detection():
    req = httpx.Request("GET", "https://api.github.com/x")
    reset = str(int(time.time()) + 600)
    with pytest.raises(GitHubRateLimitError) as info:
        check_rate_limit(httpx.Response(403, request=req, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset}))
    assert 9 <= info.value.minutes_left <= 10
    assert "try again in about" in rate_limit_message(info.value)
    with pytest.raises(GitHubRateLimitError):
        check_rate_limit(httpx.Response(429, request=req))
    # A plain 403 (e.g. a blocked repo) and a 200 are not rate limits.
    check_rate_limit(httpx.Response(403, request=req, headers={"x-ratelimit-remaining": "12"}))
    check_rate_limit(httpx.Response(200, request=req))


def test_inspection_is_cached_until_the_repo_is_pushed_again(monkeypatch):
    calls = []

    async def fake_tree(owner, repo, client):
        calls.append(repo)
        return ["Dockerfile"]

    async def fake_file(owner, repo, path, client):
        return ""

    async def fake_commits(owner, repo, client):
        return 3

    monkeypatch.setattr(fingerprinting, "fetch_repo_tree", fake_tree)
    monkeypatch.setattr(fingerprinting, "fetch_file_content", fake_file)
    monkeypatch.setattr(fingerprinting, "fetch_commit_count", fake_commits)

    first = asyncio.run(fingerprinting.inspect_repo("me", "app", "2026-11-01T00:00:00Z"))
    again = asyncio.run(fingerprinting.inspect_repo("me", "app", "2026-11-01T00:00:00Z"))
    assert first == again and calls == ["app"]
    asyncio.run(fingerprinting.inspect_repo("me", "app", "2026-11-14T00:00:00Z"))
    assert calls == ["app", "app"]


def test_repo_list_is_cached(monkeypatch):
    hits = []

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, **kw):
            hits.append(url)
            req = httpx.Request("GET", url)
            return httpx.Response(200, request=req, json=[{
                "name": "x", "language": "Python", "fork": False, "stargazers_count": 0,
                "updated_at": "2026-11-01T00:00:00Z", "html_url": "https://github.com/me/x",
            }])

    monkeypatch.setattr(github_client.httpx, "AsyncClient", FakeClient)
    assert asyncio.run(github_client.fetch_github_repos("Me"))[0]["name"] == "x"
    asyncio.run(github_client.fetch_github_repos("me"))
    assert len(hits) == 1
