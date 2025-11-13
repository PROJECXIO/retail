import json
from math import ceil

import frappe
from frappe.utils import cint

from retail.api.utils import (
    get_request_form_data,
    format_data,
    upload_file,
    delete_duplicated_or_after_error,
)
from retail.api.utils.response import (
    build_error_response,
    build_success_response,
    handle_exception_response,
)


def load_extra_list_data(data, doctype, table_fields=[]):
    if not isinstance(data, list):
        return
    if doctype == "Pet Service":
        for d in data:
            name = d.get("name")
            d.update({
                "features": frappe.get_all("Pet Service Feature Table", filters={"parent": name, "parentfield": "features", "parenttype": "Pet Service"}, pluck="feature")
            })

def order_data_by_most_view(doctype, data, limit_page_length):
    most_viewed = frappe.db.get_all(
        "View Log",
        fields=["reference_name", "COUNT(*) as view_count"],
        filters={"reference_doctype": doctype, "viewed_by": ["!=", "Administrator"]},
        group_by="reference_name",
        order_by="view_count desc",
        limit_page_length=limit_page_length,
    )
    order_map = {
        order["reference_name"]: index for index, order in enumerate(most_viewed)
    }
    return sorted(data, key=lambda x: order_map.get(x["name"], float("inf")))


def document_list(
    doctype: str,
    fields: list | str,
    table_fields=[],
    filters=[],
    or_filters=[],
    order_by="modified",
    order="desc",
    ignore_permissions=False,
):
    order_by = f"{order_by} {order}"
    limit_start = 0
    limit_page_length = 20
    parent = None
    if "name" not in fields:
        fields = ["name"] + fields
    try:
        if "limit_page_length" in frappe.request.args:
            limit_page_length = cint(frappe.request.args["limit_page_length"])
        if "limit" in frappe.request.args:
            limit_page_length = cint(frappe.request.args["limit"])
        if "limit_start" in frappe.request.args:
            limit_start = cint(frappe.request.args["limit_start"]) - 1
            if limit_start < 0:
                limit_start = 1
        if "page" in frappe.request.args:
            limit_start = cint(frappe.request.args["page"]) - 1
            if limit_start < 0:
                limit_start = 1

        limit_start = limit_start * limit_page_length

        fields_to_select = list(filter(lambda x: x in table_fields, fields))
        fields = list(filter(lambda x: x not in table_fields, fields))
        args = frappe._dict(
            parent_doctype=parent,
            fields=fields,
            filters=filters,
            or_filters=or_filters,
            order_by=order_by,
            limit_start=limit_start,
            limit_page_length=limit_page_length,
            as_list=False,
            ignore_permissions=ignore_permissions,
        )
        totalCount = len(
            frappe.get_all(
                doctype,
                ignore_permissions=ignore_permissions,
                filters=filters,
                or_filters=or_filters,
                limit_page_length=999999999,
            )
        )
        # evaluate frappe.get_list
        data = frappe.get_all(doctype, **args)
        load_extra_list_data(data, doctype, fields_to_select)
        response_data = frappe._dict()

        page = limit_start + 1
        currentPageCount = len(data)
        perPage = limit_page_length
        pageCount = 0
        if perPage > totalCount:
            pageCount = 1
        elif perPage > 0:
            pageCount = ceil(totalCount / perPage)
        response_data.update(
            {
                "data_list": data,
                "page": page,
                "currentPageCount": currentPageCount,
                "perPage": perPage,
                "totalCount": totalCount,
                "pageCount": pageCount,
            }
        )
        return build_success_response(200, f"{doctype} fetched", response_data)
    except Exception as exc:
        print(frappe.get_traceback())
        http_status_code = 500
        message = exc
        if hasattr(exc, "http_status_code"):
            http_status_code = exc.http_status_code
        if hasattr(exc, "args"):
            args = exc.args
            if len(args) > 1 and isinstance(args[0], int):
                message = args[1]
            elif len(args) > 0:
                message = args[0].split(":")[0]
        return build_error_response(
            http_status_code, f"failed to read {doctype}", message
        )

def create_doc(doctype: str, default_data={}, ignore_permissions=False):
    uploaded_files = []
    doc = None
    try:
        data = get_request_form_data()
        if not isinstance(data, bytes):
            data.pop("doctype", None)
            data = format_data(data, doctype)
            doc = frappe.new_doc(doctype, **data)
        else:
            doc = frappe.new_doc(doctype)
        
        uploaded_files = handle_files(doc, ignore_permissions=ignore_permissions)
        for file in uploaded_files:
            fieldname = file.get("fieldname")
            doc.update(
                {
                    f"{fieldname}": file.get("file_url"),
                }
            )
        print(doc)
        print(doc)
        print(doc)
        print(doc)
        doc.update(default_data)
        doc.insert(ignore_permissions=ignore_permissions)
        delete_duplicated_or_after_error(
            uploaded_files, ignore_permissions=ignore_permissions
        )
        return build_success_response(201, f"{doctype} created", doc)
    except Exception as exc:
        print(frappe.get_traceback())
        resp = handle_exception_response(
            doc,
            doctype,
            exc,
            uploaded_files=uploaded_files,
            ignore_permissions=ignore_permissions,
        )
        try:
            frappe.get_doc({
                "doctype": "API Error Logs",
                "source": f"create_doc:{doctype}",
                "error_message": frappe.get_traceback(),
                "data": frappe.as_json(get_request_form_data(), indent=2,)
            }).insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            frappe.get_doc({
                "doctype": "API Error Logs",
                "data": frappe.as_json(get_request_form_data(), indent=2,)
            }).insert(ignore_permissions=True)
            frappe.log_error(frappe.get_traceback(), "Failed writing to API Error Logs (create_doc)")

        return resp


def handle_files(doc, ignore_permissions=False):
    meta = frappe.get_meta(doc.doctype)
    uploaded_files = []
    for field in meta.fields:
        if field.fieldtype not in ["Attach", "Attach Image"]:
            continue
        file_doc_name = upload_file(
            field.fieldname, ignore_permissions=ignore_permissions
        )
        if file_doc_name is not None:
            uploaded_files.append(file_doc_name)
    return uploaded_files

def load_extra_data(doctype, name):
    extra_data = {}
    return extra_data

def get_next(
    doctype, value, prev, filters=None, sort_order="desc", sort_field="modified"
):
    prev = int(prev)
    if not filters:
        filters = []
    if isinstance(filters, str):
        filters = json.loads(filters)

    # # condition based on sort order
    condition = ">" if sort_order.lower() == "asc" else "<"

    # switch the condition
    if prev:
        sort_order = "asc" if sort_order.lower() == "desc" else "desc"
        condition = "<" if condition == ">" else ">"

    # # add condition for next or prev item
    filters.append(
        [doctype, sort_field, condition, frappe.get_value(doctype, value, sort_field)]
    )

    res = frappe.get_all(
        doctype,
        fields=["name"],
        filters=filters,
        order_by=f"`tab{doctype}`.{sort_field}" + " " + sort_order,
        limit_start=0,
        limit_page_length=1,
        as_list=True,
    )

    if not res:
        return None
    else:
        return res[0][0]


def update_viewing(doctype, name):
    view = frappe.new_doc("View Log")
    view.viewed_by = frappe.session.user or "Guest"
    view.reference_doctype = doctype
    view.reference_name = name
    view.save(ignore_permissions=True)
    frappe.db.commit()


def read_doc(
    doctype: str,
    name: str,
    origin_fields: list = [],
    force_fields=False,
    ignore_perms=False,
    inject_next_prev=False,
    track_viewing=False,
    user_filters=[],
):
    try:
        doc = frappe.get_doc(doctype, name)
        if not ignore_perms and not doc.has_permission("read"):
            raise frappe.PermissionError
        doc.apply_fieldlevel_read_permissions()
        for f in user_filters:
            field = f[0]
            value = f[2]
            if doc.get(field) != value:
                raise frappe.DoesNotExistError("CRM Unit {} not found".format(name))

        extra_data = load_extra_data(doc.doctype, doc.name)

        user_fields = origin_fields
        if not force_fields:
            if "fields" in frappe.request.args:
                _fields = frappe.request.args["fields"]
                if isinstance(_fields, list):
                    user_fields = _fields
                else:
                    user_fields = frappe.parse_json(_fields)

                if isinstance(_fields, list):
                    user_fields = _fields

            if "*" in user_fields:
                user_fields = []
        if doc:
            doc = doc.as_dict()
        if len(user_fields) > 0:
            result = frappe._dict()
            for field in user_fields:
                if hasattr(doc, field):
                    result.update({field: getattr(doc, field)})
            doc = result
        if inject_next_prev:
            next = get_next(doctype, name, 1)
            prev = get_next(doctype, name, 0)
            doc.update(
                {
                    "next": next,
                    "prev": prev,
                }
            )
        if track_viewing:
            update_viewing(doctype, name)
        return build_success_response(200, f"{doctype} fetched", doc, extra_data)
    except Exception as exc:
        http_status_code = 500
        message = exc
        if hasattr(exc, "http_status_code"):
            http_status_code = exc.http_status_code
        if hasattr(exc, "args"):
            args = exc.args
            if len(args) > 0 and isinstance(args[0], str):
                message = args[0].split(":")[0]
            elif len(args) > 1 and isinstance(args[0], int):
                message = args[1]
        return build_error_response(
            http_status_code, f"failed to read {doctype}", message
        )


def update_doc(
    doctype: str, name: str, default_data={}, ignore_perms=False, keys_to_update=[]
):
    uploaded_files = []
    find_by = {"name": name}
    if default_data:
        find_by.update(default_data)
    doc = None
    try:
        data = get_request_form_data()
        doc = frappe.get_doc(doctype, find_by, for_update=True)
        if not isinstance(data, bytes):
            if "flags" in data:
                del data["flags"]
            data = format_data(data, doctype, keys_to_update=keys_to_update)
            doc.update(data)
        uploaded_files = handle_files(doc, ignore_permissions=ignore_perms)
        for file in uploaded_files:
            fieldname = file.get("fieldname")
            doc.update(
                {
                    f"{fieldname}": file.get("file_url"),
                }
            )
        doc.update(default_data)
        doc.save()
        delete_duplicated_or_after_error(
            uploaded_files, ignore_permissions=ignore_perms
        )
        # check for child table doctype
        if doc.get("parenttype"):
            frappe.get_doc(doc.parenttype, doc.parent).save()
        return build_success_response(200, f"{doctype} updated", doc)
    except Exception as exc:
        return handle_exception_response(
            doc,
            doctype,
            exc,
            uploaded_files=uploaded_files,
            for_update=True,
            ignore_permissions=ignore_perms,
        )


def delete_doc(doctype: str, name: str):
    try:
        doc = frappe.delete_doc(doctype, name, ignore_missing=False)
        # frappe.response.http_status_code = 202
        return build_success_response(202, f"{doctype} deleted", doc)
    except Exception as exc:
        return handle_exception_response(
            None, doctype, exc, uploaded_files=[], for_delete=True
        )


def handle_call(method: str):
    import frappe.handler

    method = method.split("/")[0]
    frappe.form_dict.cmd = method
    return frappe.handler.handle()
