import frappe
from frappe import request, _

from retail.api.utils.jwt import check_token_and_set_user
from retail.api.utils.response import build_error_response

WHITELIST_PATHS = [
    "/api/v1/user/auth/login",
    "/api/v1/user/auth/refresh-token",
]


def before_request():
    if request.path.startswith("/api/v1/") and request.path not in WHITELIST_PATHS:
        auth_header = frappe.get_request_header("Authorization", "")
        if auth_header and auth_header.startswith("Bearer "):
            jwt_token = auth_header.split(" ")[1]
            user_d = check_token_and_set_user(jwt_token)
            if not user_d:
                return
        else:
            build_error_response(
                401,
                "Authentication failed: Access token is no longer valid",
                "The provided access token is invalid",
            )
