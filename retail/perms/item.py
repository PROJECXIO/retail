import frappe

# Role if user has it will restrict items access
RESTRICTED_ROLE = "Accounts Viewer"

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    has_role = (user != "Administrator") and (RESTRICTED_ROLE in frappe.get_roles(user))
    if has_role:
        companies = frappe.get_list("Company", pluck="name")
        ItemDefault = frappe.qb.DocType("Item Default")
        data = (
            frappe.qb.from_(ItemDefault)
            .select(ItemDefault.parent)
            .where(ItemDefault.company.isin(companies))
        ).run(pluck="parent")
        if len(data) > 0:
            data = [f"'{d}'" for d in data]
            data = ", ".join(data)
            return "`tabItem`.name IN ({})".format(data)
    if frappe.has_permission(doctype="Item", user=frappe.session.user):
        return
    return "1!=1"
