import frappe

PET_ROLES = [
    "Pet Manager",
    "Pet User",
]
def prepare_pet_roles():
    for role in PET_ROLES:
        if frappe.db.exists("Role", role):
            continue
        role_doc = frappe.new_doc("Role")
        role_doc.role_name = role
        role_doc.save()
    frappe.db.commit()
