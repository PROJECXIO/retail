from retail.api.utils.endpoints import document_list
def services_list():
    doctype = "Pet Service"
    document_list(doctype, ["service", "working_hours", "features"], table_fields=["features"], ignore_permissions=True)
