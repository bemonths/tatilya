"""Conservative identities for connector source URLs, without fetching URLs."""
from urllib.parse import urlsplit


def https_source_identity(url, *, host_aliases):
    """Return (explicit canonical host, path), or None for an unsafe/ambiguous URL.

    Only configured host aliases and one optional trailing slash are equivalent.
    Query/fragment delimiters (even empty), encoded paths, dot segments and
    repeated slashes are rejected rather than guessed or silently discarded.
    """
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        return None
    if any(c in url for c in ('?', '#', '\\')):
        return None
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.hostname not in host_aliases
                or parts.username is not None or parts.password is not None
                or parts.port not in (None, 443) or parts.netloc.endswith(':')):
            return None
    except ValueError:
        return None
    path = parts.path or '/'
    if '%' in path or '//' in path or any(segment in ('.', '..') for segment in path.split('/')):
        return None
    return host_aliases[parts.hostname], path.removesuffix('/') or '/'
