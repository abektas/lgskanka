"""Narrow trust rules for official-page discovered PDF targets."""
from dataclasses import dataclass
from urllib.parse import urlparse

from validate_source_registry import official_host

CDN_HOST = "cdn.eba.gov.tr"


@dataclass(frozen=True)
class DiscoveredPdf:
    source_id: str
    discovered_from: str
    source_page_url: str
    pdf_url: str
    discovery_redirect_chain: list[str]
    anchor_text: str


def is_cdn_host(host: str) -> bool:
    return host.lower() == CDN_HOST


def is_allowed_pdf_host(host: str) -> bool:
    return official_host(host.lower()) or is_cdn_host(host)


def require_https(url: str, label: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{label} must use HTTPS")


def validate_discovered_pdf(discovery: DiscoveredPdf) -> None:
    if not isinstance(discovery, DiscoveredPdf):
        raise ValueError("PDF target requires official-page discovery evidence")
    if not discovery.source_id:
        raise ValueError("PDF discovery must include source_id")
    for field, url in (("discovered_from", discovery.discovered_from), ("source_page_url", discovery.source_page_url)):
        require_https(url, field)
        if not official_host((urlparse(url).hostname or "").lower()):
            raise ValueError(f"{field} must be an official MEB page")
    if discovery.discovered_from != discovery.source_page_url:
        raise ValueError("PDF discovery source page does not match its registered page")
    require_https(discovery.pdf_url, "PDF URL")
    if not is_allowed_pdf_host((urlparse(discovery.pdf_url).hostname or "").lower()):
        raise ValueError("PDF URL is outside the official MEB/CDN target policy")
    if not discovery.discovery_redirect_chain or discovery.discovery_redirect_chain[-1] != discovery.source_page_url:
        raise ValueError("official-page redirect chain is incomplete")
    for url in discovery.discovery_redirect_chain:
        require_https(url, "official-page redirect")
        if not official_host((urlparse(url).hostname or "").lower()):
            raise ValueError("official-page redirect left the MEB allowlist")


def validate_pdf_redirect(previous_url: str, next_url: str) -> None:
    require_https(previous_url, "PDF redirect source")
    require_https(next_url, "PDF redirect target")
    if not is_allowed_pdf_host((urlparse(next_url).hostname or "").lower()):
        raise ValueError("PDF redirect target is outside the official MEB/CDN allowlist")
