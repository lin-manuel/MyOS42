import hashlib


def get_client_ip(request) -> str:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def generate_device_fingerprint(request) -> str:
    """
    Creates a fingerprint from IP + User-Agent + Accept-Language.
    In production you can enrich this with JS-collected canvas/WebGL data.
    """

    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")
    lang = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    raw = f"{ip}|{ua}|{lang}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_device_name(request) -> str:
    ua = request.META.get("HTTP_USER_AGENT", "").lower()
    if "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"
    elif "edge" in ua:
        browser = "Edge"
    else:
        browser = "Browser"

    if "windows" in ua:
        os_name = "Windows"
    elif "mac" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua:
        os_name = "iPhone"
    else:
        os_name = "Device"

    return f"{browser} on {os_name}"
