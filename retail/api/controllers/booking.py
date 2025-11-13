from retail.api.utils.endpoints import create_doc
def create_booking():
    doctype = "Booking Request"
    create_doc(doctype, ignore_permissions=True)
