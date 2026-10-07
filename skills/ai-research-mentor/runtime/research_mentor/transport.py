"""Bounded HTTPS transport; public-DNS pinning is the normal mode."""
from __future__ import annotations
import hashlib
import http.client
import ipaddress
import queue
import re
import socket
import ssl
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone

class TransportError(ValueError):
    pass

@dataclass
class Response:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    mode: str = "public_dns_pinned_tls"

    def receipt(self, provider: str) -> dict:
        return {"provider": provider, "url": self.url, "http_status": self.status,
                "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "raw_sha256": hashlib.sha256(self.body).hexdigest(), "bytes": len(self.body),
                "transport_mode": self.mode, "content_type": self.headers.get("content-type", "application/octet-stream").split(";")[0].lower()}

def public_address(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
        return parsed.is_global and not parsed.is_multicast
    except ValueError:
        return False

def checked_url(value: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(value)
    host = (parsed.hostname or "").lower()
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    try:
        port = parsed.port
    except ValueError as exc:
        raise TransportError("invalid URL port") from exc
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in (None, 443) or \
       is_ip or "." not in host or host.endswith((".local", ".internal", ".localhost")):
        raise TransportError("only public HTTPS domain URLs without credentials or custom ports are accepted")
    if any(name.lower() in {"key", "api_key", "apikey", "token", "access_token", "secret", "password"}
           for name, _ in urllib.parse.parse_qsl(parsed.query)):
        raise TransportError("credential-bearing URLs cannot be fetched or recorded")
    return parsed._replace(fragment="")

class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: int):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)

class Transport:
    def __init__(self, *, timeout: int = 15, max_bytes: int = 2 * 1024 * 1024,
                 byte_budget: int = 10 * 1024 * 1024, request_budget: int = 8,
                 trusted_provider_transport: bool = False):
        if not 1 <= timeout <= 60 or not 1 <= max_bytes <= 20 * 1024 * 1024 or \
           not max_bytes <= byte_budget <= 100 * 1024 * 1024 or not 1 <= request_budget <= 20:
            raise TransportError("invalid timeout/byte/request budget")
        self.timeout, self.max_bytes = timeout, max_bytes
        self.byte_budget, self.request_budget = byte_budget, request_budget
        self.trusted_provider_transport = trusted_provider_transport
        self.requests, self.bytes_received = [], 0

    def get(self, url: str, *, allowed_hosts: set[str], trusted_provider: bool = False) -> Response:
        # Socket timeouts bound a single receive, not the complete HTTP parse:
        # slow headers/chunk framing can keep buffered reads alive indefinitely.
        # The observation worker cannot publish a response after this deadline.
        # On timeout, interrupt its active socket; only that worker closes the
        # buffered response, whose close() can otherwise wait on a read lock.
        deadline = time.monotonic() + self.timeout
        completed = queue.Queue(maxsize=1)
        cancelled = threading.Event()
        active = {}

        def observe():
            try:
                result = self._get(url, allowed_hosts=allowed_hosts, trusted_provider=trusted_provider,
                                   deadline=deadline, active=active, cancelled=cancelled)
                completed.put((True, result))
            except Exception as exc:
                completed.put((False, exc))
            finally:
                for name in ("response", "connection"):
                    resource = active.get(name)
                    if resource is not None:
                        try:
                            resource.close()
                        except OSError:
                            pass

        threading.Thread(target=observe, daemon=True).start()
        try:
            ok, result = completed.get(timeout=max(0.001, deadline - time.monotonic()))
        except queue.Empty as exc:
            cancelled.set()
            connection, response = active.get("connection"), active.get("response")
            sockets = [getattr(connection, "sock", None)]
            # urllib HTTPError may wrap an HTTPResponse in another .fp layer.
            for _ in range(3):
                if response is None:
                    break
                sockets.append(getattr(getattr(response, "raw", None), "_sock", None))
                response = getattr(response, "fp", None)
            for sock in sockets:
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
            raise TransportError("request timeout") from exc
        if not ok:
            raise result
        if time.monotonic() >= deadline:
            raise TransportError("request timeout")
        return result

    def _get(self, url: str, *, allowed_hosts: set[str], trusted_provider: bool,
             deadline: float, active: dict, cancelled: threading.Event) -> Response:
        parsed = checked_url(url)
        for _ in range(4):
            remaining_time = deadline - time.monotonic()
            if cancelled.is_set() or remaining_time <= 0:
                raise TransportError("request timeout")
            host = parsed.hostname.lower()
            if host not in allowed_hosts:
                raise TransportError("redirect outside explicitly permitted source host")
            if len(self.requests) >= self.request_budget:
                raise TransportError("request budget exhausted")
            # Proxy transport is allowed only for URLs constructed internally for
            # fixed providers.  It never weakens TLS certificate verification.
            proxy_mode = self.trusted_provider_transport and trusted_provider
            fixed_provider = (host == "export.arxiv.org" and parsed.path == "/api/query") or \
                (host == "api.crossref.org" and (parsed.path == "/works" or re.match(r"^/works/10\.\d{4,9}%2[fF].+", parsed.path))) or \
                (host == "arxiv.org" and re.match(r"^/html/(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+/\d{7})(?:v[1-9]\d*)?$", parsed.path))
            if proxy_mode and not fixed_provider:
                raise TransportError("trusted-provider transport requires a fixed official API/resource path")
            if self.trusted_provider_transport and not trusted_provider:
                raise TransportError("trusted-provider transport cannot fetch arbitrary URLs")
            mode = "trusted_provider_tls" if proxy_mode else "public_dns_pinned_tls"
            record = {"url": parsed.geturl(), "status": None, "bytes": 0, "transport_mode": mode}
            self.requests.append(record)
            if proxy_mode:
                opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
                request = urllib.request.Request(parsed.geturl(), headers={"User-Agent": "AI-Research-Mentor/0.1 Python evidence core"})
                remaining_time = deadline - time.monotonic()
                if cancelled.is_set() or remaining_time <= 0:
                    raise TransportError("request timeout")
                try:
                    response = opener.open(request, timeout=remaining_time)
                except urllib.error.HTTPError as exc:
                    response = exc
                active["response"] = response
                connection = None
                status, headers = response.code, dict(response.headers.items())
            else:
                addresses = _bounded_lookup(host, deadline)
                if not addresses or any(not public_address(item[4][0]) for item in addresses):
                    raise TransportError("source DNS returned a non-public address")
                if cancelled.is_set() or time.monotonic() >= deadline:
                    raise TransportError("request timeout")
                connection = _PinnedHTTPS(host, addresses[0][4][0], max(0.001, deadline - time.monotonic()))
                active["connection"] = connection
                target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
                if cancelled.is_set() or time.monotonic() >= deadline:
                    raise TransportError("request timeout")
                connection.request("GET", target, headers={"User-Agent": "AI-Research-Mentor/0.1 Python evidence core"})
                if cancelled.is_set():
                    raise TransportError("request timeout")
                response = connection.getresponse()
                active["response"] = response
                status, headers = response.status, dict(response.getheaders())
            if cancelled.is_set() or time.monotonic() >= deadline:
                raise TransportError("request timeout")
            headers = {key.lower(): value for key, value in headers.items()}
            record["status"] = status
            try:
                if status in {301, 302, 303, 307, 308}:
                    location = headers.get("location")
                    if not location:
                        raise TransportError("redirect has no location")
                    parsed = checked_url(urllib.parse.urljoin(parsed.geturl(), location))
                    continue
                remaining = min(self.max_bytes, self.byte_budget - self.bytes_received)
                if remaining <= 0:
                    raise TransportError("byte budget exhausted")
                chunks, received = [], 0
                while True:
                    remaining_time = deadline - time.monotonic()
                    if cancelled.is_set() or remaining_time <= 0:
                        raise TransportError("request timeout while reading body")
                    # Keep individual reads within the same absolute deadline.
                    sock = connection.sock if connection else None
                    if sock is None:
                        sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                    if sock is not None:
                        sock.settimeout(remaining_time)
                    # read(n) can internally perform many receives, each of
                    # which resets the socket idle timeout. read1 permits the
                    # absolute deadline to be checked between ordinary reads.
                    reader = getattr(response, "read1", None)
                    chunk = (reader if reader is not None else response.read)(min(65536, remaining + 1 - received))
                    if chunk:
                        received += len(chunk)
                        record["bytes"] = received
                        self.bytes_received += len(chunk)
                    if cancelled.is_set() or time.monotonic() >= deadline:
                        raise TransportError("request timeout while reading body")
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if received > remaining:
                        raise TransportError("response exceeded byte budget")
                body = b"".join(chunks)
                record["bytes"] = len(body)
                if len(body) > remaining:
                    raise TransportError("response exceeded byte budget")
                return Response(parsed.geturl(), status, headers, body, mode)
            finally:
                response.close()
                if connection:
                    connection.close()
        raise TransportError("redirect limit exhausted")

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None

def _bounded_lookup(host: str, deadline: float):
    # DNS itself has no cross-platform socket timeout. A daemon observation
    # thread prevents an unresponsive resolver from blocking the CLI forever.
    results = queue.Queue(maxsize=1)
    def lookup():
        try:
            results.put((True, socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
        except OSError as exc:
            results.put((False, exc))
    threading.Thread(target=lookup, daemon=True).start()
    try:
        ok, result = results.get(timeout=max(0.001, deadline - time.monotonic()))
    except queue.Empty as exc:
        raise TransportError("DNS lookup timeout") from exc
    if not ok:
        raise TransportError("DNS lookup failed") from result
    return result
