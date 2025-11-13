import frappe
from erpnext.projects.doctype.timesheet.timesheet import OverlapError
from retail.api.utils import delete_duplicated_or_after_error


def build_error_response(status_code, message, error, missing_data=None):
    return build_response(
        status="failed",
        status_code=status_code,
        message=message,
        error=error,
        missing_data=missing_data,
    )


def build_success_response(status_code, message, data, extra_data={}):
    if extra_data:
        data.update(extra_data)
    return build_response(
        status="success", status_code=status_code, message=message, data=data
    )


def build_response(
    status=None,
    status_code=None,
    data=None,
    error=None,
    message=None,
    missing_data=None,
):
    frappe.local.response["status"] = status
    frappe.local.response["statusCode"] = status_code
    frappe.local.response["http_status_code"] = status_code
    frappe.local.response["data"] = data
    frappe.local.response["error"] = error
    frappe.local.response["message"] = message
    if missing_data:
        frappe.local.response["missing_data"] = missing_data
    # frappe.local.response["type"] = "json"
    frappe.local.message_log = []
    frappe.local.debug_log = None
    frappe.flags.error_message = None


def handle_exception_response(
    doc,
    doctype,
    exception,
    uploaded_files=[],
    for_update=False,
    for_delete=False,
    ignore_permissions=False,
):
    http_status_code = 500
    message = exception
    delete_duplicated_or_after_error(
        uploaded_files, ignore_permissions=ignore_permissions
    )
    if for_delete:
        title = f"failed to update {doctype}"
    else:
        title = (
            f"failed to update {doctype}"
            if for_update
            else f"failed to create {doctype}"
        )
    if hasattr(exception, "http_status_code"):
        http_status_code = exception.http_status_code
    # extract mandatory message
    if isinstance(exception, frappe.MandatoryError):
        errors = doc._get_missing_mandatory_fields()
        missing_fields = [er[0] for er in errors]
        return build_error_response(
            http_status_code, title, "Required values are missing", missing_fields
        )
    elif isinstance(exception, frappe.LinkValidationError):
        if hasattr(exception, "args"):
            args = exception.args
            if len(args) > 0:
                message = args[0]
        message = message.strip()
        return build_error_response(http_status_code, title, message)
    elif isinstance(exception, frappe.DoesNotExistError):
        message = "Does not exist"
        return build_error_response(http_status_code, title, message)

    # General exceptions
    if hasattr(exception, "args"):
        args = exception.args
        if len(args) > 0:
            if isinstance(exception, OverlapError):
                return build_error_response(http_status_code, title, args[0])
            message = args[0].split(":")[0]
            if message == "Cannot link cancelled document":
                message = args[0]
            if ". It should be one of " in message:
                # general select issue!
                message = message.replace('"', "'")
            message = message.strip()

    return build_error_response(http_status_code, title, message)
