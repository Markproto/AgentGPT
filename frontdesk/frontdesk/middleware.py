"""
Custom middleware for J. Austin Front Desk CRM.
"""


class ScriptNameMiddleware:
    """
    Middleware to handle SCRIPT_NAME from reverse proxy headers.

    When Django is behind nginx with a path prefix (e.g., /frontdesk),
    this middleware reads the X-Script-Name header and adjusts the request
    so Django correctly handles URL routing and generation.

    nginx config should include:
        proxy_set_header X-Script-Name /frontdesk;
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        script_name = request.META.get("HTTP_X_SCRIPT_NAME", "")
        if script_name:
            request.META["SCRIPT_NAME"] = script_name
            # Strip the script name prefix from PATH_INFO
            path_info = request.META.get("PATH_INFO", "")
            if path_info.startswith(script_name):
                request.META["PATH_INFO"] = path_info[len(script_name):] or "/"

        return self.get_response(request)
