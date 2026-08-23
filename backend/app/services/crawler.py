"""
Zero to GEO — Website crawler service (Phase 4).

Fetches the website with:
- Configurable timeout
- Redirect following (max 10 hops)
- SSL error handling
- robots.txt compliance
- Sensible User-Agent
- Proper error classification

Uses httpx (sync) since the pipeline runs in a background thread.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import httpx


@dataclass
class CrawlResult:
    success: bool
    url: str                   # Final URL after redirects
    html: str = ""
    status_code: Optional[int] = None
    error: Optional[str] = None
    robots_blocked: bool = False


def crawl_website(
    url: str,
    user_agent: str = "ZeroToGEO/0.1",
    timeout: int = 15,
    respect_robots: bool = True,
) -> CrawlResult:
    """
    Fetch a website and return its HTML content.

    Handles:
    - HTTP and HTTPS
    - Redirect chains
    - SSL errors
    - Timeout
    - robots.txt (when respect_robots=True)
    - Connection errors
    - Non-200 responses
    """
    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Check robots.txt first
    if respect_robots:
        blocked, robots_error = _check_robots(url, user_agent, timeout)
        if blocked:
            return CrawlResult(
                success=False,
                url=url,
                error=f"Crawl blocked by robots.txt on {url}",
                robots_blocked=True,
            )

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            verify=True,
            headers=headers,
            max_redirects=10,
        ) as client:
            response = client.get(url)

        final_url = str(response.url)
        status_code = response.status_code

        if status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower() and "text" not in content_type.lower():
                return CrawlResult(
                    success=False,
                    url=final_url,
                    status_code=status_code,
                    error=f"URL returned non-HTML content ({content_type}). Expected a web page.",
                )
            return CrawlResult(
                success=True,
                url=final_url,
                html=response.text,
                status_code=status_code,
            )
        elif status_code in (401, 403):
            return CrawlResult(
                success=False,
                url=final_url,
                status_code=status_code,
                error=f"Website returned {status_code} (access denied). The page may require authentication.",
            )
        elif status_code == 404:
            return CrawlResult(
                success=False,
                url=final_url,
                status_code=status_code,
                error=f"Website returned 404 Not Found. Check the URL.",
            )
        elif status_code >= 500:
            return CrawlResult(
                success=False,
                url=final_url,
                status_code=status_code,
                error=f"Website server returned {status_code} error. The site may be down.",
            )
        else:
            return CrawlResult(
                success=False,
                url=final_url,
                status_code=status_code,
                error=f"Website returned unexpected status {status_code}.",
            )

    except httpx.TimeoutException:
        return CrawlResult(
            success=False,
            url=url,
            error=f"Website did not respond within {timeout} seconds. It may be slow or unavailable.",
        )
    except httpx.SSLError as exc:
        return CrawlResult(
            success=False,
            url=url,
            error=f"SSL certificate error: {str(exc)[:200]}. The site may have an invalid certificate.",
        )
    except httpx.TooManyRedirects:
        return CrawlResult(
            success=False,
            url=url,
            error="Website has too many redirects (>10). Could not reach the final page.",
        )
    except httpx.ConnectError:
        return CrawlResult(
            success=False,
            url=url,
            error="Could not connect to the website. Check that the URL is correct and the site is online.",
        )
    except httpx.RequestError as exc:
        return CrawlResult(
            success=False,
            url=url,
            error=f"Request error: {str(exc)[:200]}",
        )
    except Exception as exc:
        return CrawlResult(
            success=False,
            url=url,
            error=f"Unexpected error while fetching website: {str(exc)[:200]}",
        )


def _check_robots(url: str, user_agent: str, timeout: int) -> tuple[bool, Optional[str]]:
    """
    Fetch and parse robots.txt. Returns (blocked, error_message).
    If robots.txt cannot be fetched, assume not blocked (fail open).
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)

        # Fetch robots.txt manually so we can apply timeout
        with httpx.Client(timeout=min(timeout, 5), follow_redirects=True) as client:
            try:
                resp = client.get(robots_url)
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                else:
                    # No robots.txt found — not blocked
                    return False, None
            except Exception:
                # Can't fetch robots.txt — fail open (not blocked)
                return False, None

        blocked = not rp.can_fetch(user_agent, url)
        # Also check with common bot names
        if not blocked:
            blocked = not rp.can_fetch("*", url)

        return blocked, None

    except Exception:
        return False, None  # Fail open
