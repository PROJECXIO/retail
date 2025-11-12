frappe.listview_settings["Pet Service Package"] = {
  add_fields: ["status"],
  get_indicator: function (doc) {
    if (doc.docstatus == 0) {
      return [__("Draft"), "red", "docstatus,=,0"];
    } else if (doc.docstatus == 2) {
      return [__("Cancelled"), "red", "docstatus,=,2"];
    } else {
      if (doc.status === "Active") {
        return [__("Active"), "green", "status,=,Active"];
      } else if (doc.status === "Inactive") {
        return [__(doc.status), "yellow", "status,=,Inactive"];
      }
    }
  },
  onload(listview) {
    listview.page.add_action_item(__("Submit Selected"), function () {
      const selected = listview.get_checked_items();

      if (!selected.length) {
        frappe.msgprint(__("Please select at least one document."));
        return;
      }

      frappe.call({
        method: "retail.overrides.doctype.appointment.bulk_submit",
        args: {
          doctype: "Appointment",
          docnames: selected.map((d) => d.name),
        },
        callback: function (r) {
          if (r.message) {
            frappe.msgprint(
              `Submitted ${r.message.submitted.length} document(s).`
            );
            listview.refresh();
          }
        },
      });
    });
  },
};
