"""Minimal HTTP client for the SakbeLab API, used by the CLI and the SDK.

Only the standard library: the SDK installs on a student's machine without the
server dependencies.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_SERVER = "http://localhost"


class SakbeError(RuntimeError):
    """An error returned by the SakbeLab server, with its message in Spanish."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class Client:
    def __init__(
        self, server: str = DEFAULT_SERVER, token: str | None = None, timeout: float = 300
    ):
        self.server = server.rstrip("/")
        self.token = token  # reserved for authentication in a future version
        self.timeout = timeout

    def url(self, path: str) -> str:
        return f"{self.server}/api/v1{path}"

    def request(
        self,
        method: str,
        path: str,
        body=None,
        raw=None,
        content_type: str = "application/json",
        params: dict | None = None,
    ):
        url = self.url(path)
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", content_type)
        if hasattr(data, "fileno"):  # stream big files instead of loading them in memory
            req.add_header("Content-Length", str(os.fstat(data.fileno()).st_size))
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                payload = res.read()
                if res.headers.get_content_type() == "application/json":
                    return json.loads(payload) if payload else None
                return payload
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read()).get("detail")
            except (ValueError, AttributeError):
                detail = None
            if isinstance(detail, list):
                detail = "; ".join(str(d.get("msg", d)) for d in detail)
            raise SakbeError(detail or f"{exc.code} {exc.reason}", exc.code) from None
        except urllib.error.URLError as exc:
            raise SakbeError(f"No se pudo conectar con {self.server}: {exc.reason}") from None

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body=body, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)


def quote(name: str) -> str:
    return urllib.parse.quote(name, safe="")
