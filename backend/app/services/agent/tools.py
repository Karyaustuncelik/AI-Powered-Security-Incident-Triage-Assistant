"""Concrete security tools the AI agent can invoke.

Each tool is a callable that takes structured parameters and returns a string
observation. Tools perform *real* network requests where safe (HTTP GET, DNS,
TLS handshake) and simulated results where live scanning would be inappropriate
for a portfolio project (port scanning, brute force).

Tool registry is a dict mapping tool names to SecurityTool instances so the
agent engine can look them up dynamically.
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib import error, request, parse


@dataclass
class SecurityTool:
    """A tool the agent can call."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema fragment
    func: Any  # Callable[[dict], str]

    def as_schema(self) -> dict:
        """Return an OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ── Helper ────────────────────────────────────────────────────────────────────

def _domain_from_url(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]


def _safe_request(url: str, timeout: int = 8) -> tuple[int, dict[str, str], str]:
    """Make a GET request and return (status, headers, body_excerpt)."""
    req = request.Request(url, headers={"User-Agent": "SiriusAI-Agent/2.0"})
    with request.urlopen(req, timeout=timeout) as resp:
        headers = {k: v for k, v in resp.headers.items()}
        body = resp.read(8000).decode("utf-8", errors="ignore")
        return resp.status, headers, body


# ── Tool implementations ──────────────────────────────────────────────────────

def tool_http_probe(params: dict) -> str:
    """Probe HTTP endpoint for status, headers, and technology fingerprints."""
    url = params["url"].rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        status, headers, body = _safe_request(url)
    except error.HTTPError as e:
        return json.dumps({"status": e.code, "error": str(e)[:200]}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)[:200]}, indent=2)

    # Extract interesting headers
    security_headers = {
        "Server": headers.get("Server", "not disclosed"),
        "X-Powered-By": headers.get("X-Powered-By", "not disclosed"),
        "Content-Security-Policy": headers.get("Content-Security-Policy", "MISSING"),
        "Strict-Transport-Security": headers.get("Strict-Transport-Security", "MISSING"),
        "X-Frame-Options": headers.get("X-Frame-Options", "MISSING"),
        "X-Content-Type-Options": headers.get("X-Content-Type-Options", "MISSING"),
        "X-XSS-Protection": headers.get("X-XSS-Protection", "MISSING"),
        "Referrer-Policy": headers.get("Referrer-Policy", "MISSING"),
        "Permissions-Policy": headers.get("Permissions-Policy", "MISSING"),
    }

    # Technology fingerprinting from body
    techs = []
    body_lower = body.lower()
    tech_signatures = [
        ("React", ["react", "_reactroot", "__next"]),
        ("Angular", ["ng-version", "ng-app", "angular"]),
        ("Vue.js", ["vue.js", "__vue__", "v-cloak"]),
        ("jQuery", ["jquery", "jquery.min.js"]),
        ("WordPress", ["wp-content", "wp-includes", "wordpress"]),
        ("Drupal", ["drupal", "sites/default"]),
        ("Laravel", ["laravel", "csrf-token"]),
        ("Django", ["csrfmiddlewaretoken", "django"]),
        ("ASP.NET", ["__viewstate", "asp.net", ".aspx"]),
        ("Express", []),  # Detected via header
        ("Nginx", []),
        ("Apache", []),
        ("PHP", ["php", ".php"]),
        ("Bootstrap", ["bootstrap"]),
        ("Tailwind", ["tailwind"]),
    ]
    for tech_name, sigs in tech_signatures:
        if any(s in body_lower for s in sigs):
            techs.append(tech_name)
    if "express" in headers.get("X-Powered-By", "").lower():
        techs.append("Express.js")

    # Extract forms for potential input vectors
    form_count = body_lower.count("<form")
    input_count = body_lower.count("<input")

    return json.dumps({
        "status_code": status,
        "security_headers": security_headers,
        "detected_technologies": techs,
        "form_count": form_count,
        "input_field_count": input_count,
        "title": _extract_title(body),
        "body_length": len(body),
    }, indent=2)


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip()[:120] if match else "N/A"


def tool_dns_lookup(params: dict) -> str:
    """Perform DNS resolution and gather address records."""
    domain = _domain_from_url(params["domain"])
    results: dict[str, Any] = {"domain": domain, "records": {}}
    try:
        # A records
        ips = socket.getaddrinfo(domain, None, socket.AF_INET)
        a_records = list({addr[4][0] for addr in ips})
        results["records"]["A"] = a_records
    except socket.gaierror:
        results["records"]["A"] = []

    try:
        # AAAA records
        ips6 = socket.getaddrinfo(domain, None, socket.AF_INET6)
        aaaa_records = list({addr[4][0] for addr in ips6})
        results["records"]["AAAA"] = aaaa_records[:3]
    except (socket.gaierror, OSError):
        results["records"]["AAAA"] = []

    # Reverse DNS on first A record
    if results["records"]["A"]:
        try:
            hostname = socket.gethostbyaddr(results["records"]["A"][0])
            results["reverse_dns"] = hostname[0]
        except socket.herror:
            results["reverse_dns"] = "N/A"

    return json.dumps(results, indent=2)


def tool_ssl_check(params: dict) -> str:
    """Check TLS/SSL certificate details and configuration."""
    host = _domain_from_url(params["host"])
    port = params.get("port", 443)
    result: dict[str, Any] = {"host": host, "port": port}

    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(8)
            s.connect((host, port))
            cert = s.getpeercert()
            cipher = s.cipher()
            version = s.version()

        if cert:
            result["subject"] = dict(x[0] for x in cert.get("subject", ()))
            result["issuer"] = dict(x[0] for x in cert.get("issuer", ()))
            result["serial_number"] = cert.get("serialNumber", "N/A")
            result["not_before"] = cert.get("notBefore", "N/A")
            result["not_after"] = cert.get("notAfter", "N/A")
            result["san"] = [
                entry[1] for entry in cert.get("subjectAltName", ())
            ][:10]

            # Check expiry
            not_after = cert.get("notAfter", "")
            if not_after:
                try:
                    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    days_left = (expiry - datetime.now()).days
                    result["days_until_expiry"] = days_left
                    result["expiry_warning"] = days_left < 30
                except ValueError:
                    pass

        if cipher:
            result["cipher_suite"] = cipher[0]
            result["tls_version"] = version
            result["key_bits"] = cipher[2]

        # Security checks
        warnings = []
        if version and version < "TLSv1.2":
            warnings.append(f"Weak TLS version: {version}")
        if cipher and cipher[2] < 128:
            warnings.append(f"Weak cipher key size: {cipher[2]} bits")
        result["security_warnings"] = warnings

    except ssl.SSLError as e:
        result["error"] = f"SSL Error: {e}"
    except (socket.timeout, OSError) as e:
        result["error"] = f"Connection failed: {e}"

    return json.dumps(result, indent=2, default=str)


def tool_subdomain_enum(params: dict) -> str:
    """Enumerate subdomains via Certificate Transparency logs (crt.sh)."""
    domain = _domain_from_url(params["domain"])
    url = f"https://crt.sh/?q=%.{parse.quote(domain)}&output=json"
    try:
        req = request.Request(url, headers={"User-Agent": "SiriusAI-Agent/2.0"})
        with request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return json.dumps({"domain": domain, "error": str(e)[:200], "subdomains": []})

    # Deduplicate and clean
    subs: set[str] = set()
    for entry in data:
        names = entry.get("name_value", "").split("\n")
        for name in names:
            name = name.strip().lower()
            if name and "*" not in name and name.endswith(domain):
                subs.add(name)

    sorted_subs = sorted(subs)
    return json.dumps({
        "domain": domain,
        "unique_subdomains": len(sorted_subs),
        "subdomains": sorted_subs[:50],
        "certificate_entries_found": len(data),
    }, indent=2)


def tool_cve_search(params: dict) -> str:
    """Search NVD for CVEs related to a keyword (technology, product, version)."""
    keyword = params["keyword"]
    encoded = parse.quote(keyword)
    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={encoded}&resultsPerPage=8"
    try:
        req = request.Request(url, headers={"User-Agent": "SiriusAI-Agent/2.0"})
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return json.dumps({"keyword": keyword, "error": str(e)[:200], "cves": []})

    cves = []
    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id", "")
        descs = cve.get("descriptions", [])
        desc = next((d["value"] for d in descs if d.get("lang") == "en"), "")[:300]
        score = None
        severity = None
        metrics = cve.get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if metrics.get(key):
                cvss_data = metrics[key][0].get("cvssData", {})
                score = cvss_data.get("baseScore")
                severity = cvss_data.get("baseSeverity")
                break
        cves.append({
            "cve_id": cve_id,
            "description": desc,
            "cvss_score": score,
            "severity": severity,
            "published": (cve.get("published") or "")[:10],
        })

    return json.dumps({
        "keyword": keyword,
        "total_results": data.get("totalResults", 0),
        "cves": cves,
    }, indent=2)


def tool_path_discovery(params: dict) -> str:
    """Probe common paths for interesting endpoints, admin panels, and sensitive files."""
    base_url = params["url"].rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    paths = [
        "/robots.txt", "/sitemap.xml", "/.env", "/.git/HEAD",
        "/admin", "/admin/login", "/login", "/api", "/api/docs",
        "/swagger", "/swagger-ui.html", "/graphql", "/wp-admin",
        "/wp-login.php", "/.well-known/security.txt", "/server-status",
        "/phpinfo.php", "/info.php", "/debug", "/console",
        "/actuator", "/actuator/health", "/metrics",
        "/.DS_Store", "/backup", "/config", "/test",
    ]

    results: dict[str, Any] = {"base_url": base_url, "probes": {}}
    accessible = []
    redirects = []
    sensitive = []

    for path in paths:
        try:
            req = request.Request(
                base_url + path,
                headers={"User-Agent": "SiriusAI-Agent/2.0"},
                method="GET",
            )
            with request.urlopen(req, timeout=5) as resp:
                status = resp.status
                results["probes"][path] = status
                if status == 200:
                    accessible.append(path)
                    if path in ("/.env", "/.git/HEAD", "/.DS_Store", "/phpinfo.php",
                                "/server-status", "/debug", "/console", "/actuator"):
                        sensitive.append(path)
                elif status in (301, 302, 303, 307, 308):
                    redirects.append(path)
        except error.HTTPError as e:
            results["probes"][path] = e.code
        except Exception:
            results["probes"][path] = "timeout/error"

    results["summary"] = {
        "accessible_paths": accessible,
        "redirects": redirects,
        "sensitive_findings": sensitive,
        "total_probed": len(paths),
    }
    return json.dumps(results, indent=2)


def tool_header_analysis(params: dict) -> str:
    """Deep analysis of HTTP security headers with OWASP recommendations."""
    url = params["url"].rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        status, headers, _ = _safe_request(url)
    except Exception as e:
        return json.dumps({"error": str(e)[:200]})

    findings = []
    score = 100  # Start at 100, deduct for issues

    checks = [
        ("Strict-Transport-Security", 15, "HSTS not set — vulnerable to protocol downgrade and cookie hijacking"),
        ("Content-Security-Policy", 20, "CSP not set — vulnerable to XSS, clickjacking, and code injection"),
        ("X-Frame-Options", 10, "X-Frame-Options not set — vulnerable to clickjacking"),
        ("X-Content-Type-Options", 10, "X-Content-Type-Options not set — vulnerable to MIME-type sniffing"),
        ("Referrer-Policy", 5, "Referrer-Policy not set — potential information leakage via Referer header"),
        ("Permissions-Policy", 5, "Permissions-Policy not set — browser features not restricted"),
        ("X-XSS-Protection", 5, "X-XSS-Protection not set (legacy but still useful for older browsers)"),
    ]

    for header_name, penalty, message in checks:
        if header_name not in headers:
            findings.append({"severity": "HIGH" if penalty >= 15 else "MEDIUM", "finding": message})
            score -= penalty

    # Check for information disclosure
    if headers.get("Server"):
        findings.append({
            "severity": "LOW",
            "finding": f"Server header discloses: {headers['Server']} — information leakage",
        })
        score -= 5
    if headers.get("X-Powered-By"):
        findings.append({
            "severity": "MEDIUM",
            "finding": f"X-Powered-By discloses: {headers['X-Powered-By']} — technology fingerprinting possible",
        })
        score -= 10

    # Check HSTS configuration quality
    hsts = headers.get("Strict-Transport-Security", "")
    if hsts:
        if "includeSubDomains" not in hsts:
            findings.append({"severity": "LOW", "finding": "HSTS missing includeSubDomains directive"})
            score -= 3
        if "preload" not in hsts:
            findings.append({"severity": "INFO", "finding": "HSTS missing preload directive"})

    # Check CSP quality
    csp = headers.get("Content-Security-Policy", "")
    if csp:
        if "'unsafe-inline'" in csp:
            findings.append({"severity": "MEDIUM", "finding": "CSP allows 'unsafe-inline' — weakens XSS protection"})
            score -= 8
        if "'unsafe-eval'" in csp:
            findings.append({"severity": "HIGH", "finding": "CSP allows 'unsafe-eval' — significant XSS risk"})
            score -= 12

    grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"

    return json.dumps({
        "url": url,
        "status": status,
        "security_score": max(0, score),
        "grade": grade,
        "findings": findings,
        "raw_headers": {k: v for k, v in headers.items()},
    }, indent=2)


def tool_whois_lookup(params: dict) -> str:
    """Perform WHOIS-style lookup via RDAP (REST-based WHOIS replacement)."""
    domain = _domain_from_url(params["domain"])
    url = f"https://rdap.org/domain/{parse.quote(domain)}"
    try:
        req = request.Request(url, headers={"User-Agent": "SiriusAI-Agent/2.0", "Accept": "application/rdap+json"})
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return json.dumps({"domain": domain, "error": str(e)[:200]})

    result: dict[str, Any] = {"domain": domain}

    # Registration dates
    for event in data.get("events", []):
        action = event.get("eventAction", "")
        date = event.get("eventDate", "")[:10]
        if action == "registration":
            result["registered"] = date
        elif action == "expiration":
            result["expires"] = date
        elif action == "last changed":
            result["last_updated"] = date

    # Nameservers
    ns_list = []
    for ns in data.get("nameservers", []):
        ns_list.append(ns.get("ldhName", ""))
    result["nameservers"] = ns_list

    # Status
    result["status"] = data.get("status", [])

    # Registrar
    for entity in data.get("entities", []):
        roles = entity.get("roles", [])
        if "registrar" in roles:
            vcards = entity.get("vcardArray", [None, []])[1] if entity.get("vcardArray") else []
            for card in vcards:
                if card[0] == "fn":
                    result["registrar"] = card[3]
                    break

    return json.dumps(result, indent=2)


# ── Tool Registry ─────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, SecurityTool] = {
    "http_probe": SecurityTool(
        name="http_probe",
        description="Probe an HTTP(S) endpoint to get status code, security headers, detected technologies, and form/input counts.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to probe (e.g. https://example.com)"},
            },
            "required": ["url"],
        },
        func=tool_http_probe,
    ),
    "dns_lookup": SecurityTool(
        name="dns_lookup",
        description="Resolve DNS records (A, AAAA) and reverse DNS for a domain.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain name to look up"},
            },
            "required": ["domain"],
        },
        func=tool_dns_lookup,
    ),
    "ssl_check": SecurityTool(
        name="ssl_check",
        description="Inspect TLS/SSL certificate: issuer, expiry, cipher suite, SAN entries, and security warnings.",
        parameters={
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "Hostname to check TLS certificate"},
                "port": {"type": "integer", "description": "Port (default 443)", "default": 443},
            },
            "required": ["host"],
        },
        func=tool_ssl_check,
    ),
    "subdomain_enum": SecurityTool(
        name="subdomain_enum",
        description="Enumerate subdomains via Certificate Transparency logs (crt.sh). Discovers hidden subdomains.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Root domain to enumerate subdomains for"},
            },
            "required": ["domain"],
        },
        func=tool_subdomain_enum,
    ),
    "cve_search": SecurityTool(
        name="cve_search",
        description="Search the NIST NVD for known CVEs by keyword (technology name, product, version).",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Search keyword (e.g. 'Apache 2.4.49', 'WordPress 6.0')"},
            },
            "required": ["keyword"],
        },
        func=tool_cve_search,
    ),
    "path_discovery": SecurityTool(
        name="path_discovery",
        description="Probe common paths for admin panels, API docs, sensitive files (.env, .git), and debug endpoints.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Base URL to probe paths on"},
            },
            "required": ["url"],
        },
        func=tool_path_discovery,
    ),
    "header_analysis": SecurityTool(
        name="header_analysis",
        description="Deep analysis of HTTP security headers with OWASP scoring (A+ to F grade) and specific vulnerability findings.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to analyze headers for"},
            },
            "required": ["url"],
        },
        func=tool_header_analysis,
    ),
    "whois_lookup": SecurityTool(
        name="whois_lookup",
        description="RDAP/WHOIS lookup for domain registration details: registrar, dates, nameservers, status.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Domain to look up"},
            },
            "required": ["domain"],
        },
        func=tool_whois_lookup,
    ),
}
