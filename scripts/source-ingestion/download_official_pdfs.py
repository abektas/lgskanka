#!/usr/bin/env python3
"""Resolve and download a small number of PDF links from one registered MEB page."""
import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from validate_source_registry import REGISTRY, official_host
from create_ingestion_manifest import create_manifest
from source_trust import DiscoveredPdf, is_allowed_pdf_host, validate_discovered_pdf, validate_pdf_redirect

MAX_PDF_BYTES = 100 * 1024 * 1024


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self._anchor = None
        self._page_text = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = next((value for key, value in attrs if key.lower() == "href" and value), None)
            self._anchor = {"href": href, "text": [], "context_start": len("".join(self._page_text))} if href else None
    def handle_data(self, data):
        self._page_text.append(data)
        if self._anchor is not None:
            self._anchor["text"].append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._anchor is not None:
            label = " ".join(self._anchor["text"])
            page_text = "".join(self._page_text)
            before = page_text[max(0, self._anchor["context_start"] - 180):self._anchor["context_start"]]
            self.hrefs.append((self._anchor["href"], label, before))
            self._anchor = None


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self, kind="official_page"):
        super().__init__()
        self.kind = kind
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if self.kind == "official_page":
            host = urlparse(newurl).hostname or ""
            if urlparse(newurl).scheme != "https" or not official_host(host.lower()):
                raise URLError(f"official-page redirect outside MEB HTTPS allowlist blocked: {host}")
        else:
            try:
                validate_pdf_redirect(req.full_url, newurl)
            except ValueError as exc:
                raise URLError(str(exc)) from exc
        self.chain.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_opener(kind="official_page"):
    handler = SafeRedirect(kind)
    opener = build_opener(handler)
    opener.redirect_handler = handler
    return opener


def registered_source(source_id):
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    source = next((row for row in data["sources"] if row["id"] == source_id), None)
    if not source:
        raise ValueError(f"source id is not registered: {source_id}")
    return source


def resolve_pdfs(source, opener=None):
    opener = opener or safe_opener()
    index_url = source["official_index_url"]
    host = urlparse(index_url).hostname or ""
    if urlparse(index_url).scheme != "https" or not official_host(host.lower()):
        raise ValueError("registry page must use an allowlisted official MEB HTTPS host")
    request = Request(index_url, headers={"User-Agent": "LGS-AI-Coach-source-ingestion/1.0"})
    with opener.open(request, timeout=30) as response:
        final = response.geturl()
        if not official_host((urlparse(final).hostname or "").lower()):
            raise ValueError("registry page resolved outside official MEB host allowlist")
        html = response.read(5 * 1024 * 1024 + 1)
    if len(html) > 5 * 1024 * 1024:
        raise ValueError("official index HTML exceeds 5 MiB limit")
    parser = Links()
    parser.feed(html.decode("utf-8", errors="replace"))
    page_chain = [index_url]
    if final != index_url:
        page_chain.append(final)
    found, skipped = [], []
    for href, label, context in parser.hrefs:
        if not re.search(r"(?:soru|kitap[cç]|cevap anahtar|[oö]rnek soru|lgs)", context + " " + label, re.I):
            continue
        url = urljoin(final, href.strip())
        parsed = urlparse(url)
        if not parsed.path.lower().endswith(".pdf"):
            continue
        if parsed.scheme != "https" or not parsed.hostname or not is_allowed_pdf_host(parsed.hostname.lower()):
            skipped.append({"url": url, "reason": "PDF link host is outside the official MEB/CDN target policy"})
            continue
        if not any(item.pdf_url == url for item in found):
            found.append(DiscoveredPdf(
                source_id=source.get("id", ""),
                discovered_from=final,
                source_page_url=final,
                pdf_url=url,
                discovery_redirect_chain=page_chain,
                anchor_text=" ".join((context, label)).strip(),
            ))
    return found, skipped


# Kitapçık kodu -> resmî sayfa bağlantı metnindeki ders anahtarı.
BOOKLET_SUBJECTS = {"SAYISAL": "sayisal", "SOZEL": "sozel"}
# Türkçe karakterleri ASCII'ye indirger; eşleşme aksan/harf duyarsız olur.
_DIACRITIC_MAP = str.maketrans("ıİöÖüÜşŞçÇğĞâÂîÎûÛ", "iIoOuUsScCgGaAiIuU")


def normalize_anchor_text(text):
    """Bağlantı metnini karşılaştırma için sadeleştirir (küçük harf + ASCII)."""
    return str(text or "").translate(_DIACRITIC_MAP).lower()


def select_discoveries(discoveries, booklet):
    """Keşfedilen PDF'leri resmî sayfa bağlantı metnine göre seçer (ör. SAYISAL_A).

    Kanıt yalnızca resmî sayfadan okunan bağlantı metnidir; eşleşme yoksa boş
    liste döner ve tahmin yapılmaz. `booklet` verilmezse tüm keşifler korunur.
    """
    if not booklet:
        return list(discoveries)
    parts = [part for part in normalize_anchor_text(booklet).replace("-", "_").split("_") if part]
    if not parts:
        return list(discoveries)
    subject = BOOKLET_SUBJECTS.get(parts[0].upper(), parts[0])
    letters = {part for part in parts[1:] if len(part) == 1}
    selected = []
    for discovery in discoveries:
        haystack = normalize_anchor_text(discovery.anchor_text)
        if subject not in haystack:
            continue
        if letters and not (letters & set(re.findall(r"[a-z0-9]+", haystack))):
            continue
        selected.append(discovery)
    return selected


def response_content_type(response):
    headers = getattr(response, "headers", {})
    value = headers.get("Content-Type", "") if hasattr(headers, "get") else ""
    return value.split(";", 1)[0].strip().lower()


def download_pdf(discovery, destination, opener=None):
    validate_discovered_pdf(discovery)
    opener = opener or safe_opener("pdf")
    request = Request(discovery.pdf_url, headers={"User-Agent": "LGS-AI-Coach-source-ingestion/1.0"})
    digest, size, signature = hashlib.sha256(), 0, bytearray()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".meb-ingest-", suffix=".part", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as out, opener.open(request, timeout=60) as response:
            final = response.geturl()
            validate_pdf_redirect(discovery.pdf_url, final)
            content_type = response_content_type(response)
            if content_type != "application/pdf":
                raise ValueError("PDF response Content-Type must be application/pdf")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_PDF_BYTES:
                    raise ValueError("PDF exceeds 100 MiB download limit")
                if len(signature) < 5:
                    signature.extend(chunk[:5-len(signature)])
                out.write(chunk)
                digest.update(chunk)
        if not bytes(signature).startswith(b"%PDF-"):
            raise ValueError("registered link did not return a PDF signature")
        file_hash = digest.hexdigest()
        if destination.exists():
            existing_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
            if existing_hash != file_hash:
                raise ValueError("archive destination already contains different bytes; refusing to overwrite immutable source")
            temporary.unlink(missing_ok=True)
        else:
            try:
                os.link(temporary, destination)
            except FileExistsError:
                existing_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
                if existing_hash != file_hash:
                    raise ValueError("archive destination was concurrently created with different bytes")
            temporary.unlink(missing_ok=True)
        redirect_chain = [discovery.pdf_url]
        handler = getattr(opener, "redirect_handler", None)
        if handler:
            redirect_chain.extend(handler.chain)
        if redirect_chain[-1] != final:
            redirect_chain.append(final)
        return {
            "bytes": size,
            "size_bytes": size,
            "sha256": file_hash,
            "source_file_url": discovery.pdf_url,
            "pdf_url": discovery.pdf_url,
            "final_url": final,
            "content_type": content_type,
            "redirect_chain": redirect_chain,
            "source_page_url": discovery.source_page_url,
            "discovered_from": discovery.discovered_from,
            "discovery_redirect_chain": discovery.discovery_redirect_chain,
        }
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--max-pdfs", type=int, default=1)
    parser.add_argument("--booklet", default=None, help="Resmî bağlantı metnine göre kitapçık seçimi, ör. SAYISAL_A")
    parser.add_argument("--archive-dir", type=Path, default=Path("data/questions/archive"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/questions/manifests"))
    args = parser.parse_args()
    if not 1 <= args.max_pdfs <= 3:
        parser.error("pilot is limited to 1–3 PDFs per run")
    source = registered_source(args.source_id)
    registered_booklets = {str(code).upper() for code in source.get("booklets", [])}
    if args.booklet and registered_booklets and args.booklet.upper() not in registered_booklets:
        parser.error(f"booklet {args.booklet} is not registered for {args.source_id}")
    try:
        discoveries, skipped = resolve_pdfs(source)
        selected = select_discoveries(discoveries, args.booklet)[:args.max_pdfs]
        if args.booklet and not selected:
            raise ValueError(f"no discovered PDF matched the registered booklet {args.booklet}")
        downloaded = []
        for index, discovery in enumerate(selected, 1):
            path = args.archive_dir / source["id"] / f"{index:02d}-{Path(urlparse(discovery.pdf_url).path).name}"
            metadata = download_pdf(discovery, path)
            manifest = create_manifest(path, source, metadata)
            manifest.update({"archive_path": str(path), "parser_version": "source-ingestion-pipeline-v1"})
            manifest_path = args.manifest_dir / f"{source['id']}__{metadata['sha256'][:12]}.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            metadata.update({"path": str(path), "manifest_path": str(manifest_path), "source_id": source["id"], "official_index_url": source["official_index_url"]})
            downloaded.append(metadata)
        print(json.dumps({"source_id": source["id"], "booklet": args.booklet, "resolved_pdf_count": len(discoveries), "selected_pdf_count": len(selected), "downloaded": downloaded, "skipped": skipped, "status": "NEEDS_REVIEW"}, ensure_ascii=False, indent=2))
    except (ValueError, HTTPError, URLError, OSError) as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
