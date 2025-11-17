frappe.listview_settings["Appointment"] = {
  refresh: function(listview) {
    $(".layout-side-section").hide();
    $("body .container").css({
      width: "90%",
      "max-width": "100%",
    });

    $(document).ready(function() {
        let breadcrumbs = $('#navbar-breadcrumbs');
        breadcrumbs.find('a').first().text('Pets');
        breadcrumbs.find('a').first().attr('href', '/app/pets');
    });
  },
  add_fields: ["status", "order_type"],
  get_indicator: function (doc) {
    if (doc.status === "Closed") {
      return [__("Closed"), "yellow", "status,=,Closed"];
    } else if (["Open", "Completed Not Paid"].includes(doc.status)) {
      return [__(doc.status), "orange", "status,=,Open"];
    } else if (doc.status === "Completed") {
      return [__("Completed"), "green", "status,=,Completed"];
    } else if (doc.status == "Cancelled") {
      return [__("Cancelled"), "red", "status,=,Cancelled"];
    } else if (doc.status == "Draft") {
      return [__("Draft"), "red", "status,=,Draft"];
    }
  },
  onload(listview) {
        listview.page.add_action_item(__('Submit Selected'), function() {
            const selected = listview.get_checked_items();

            if (!selected.length) {
                frappe.msgprint(__('Please select at least one document.'));
                return;
            }

            frappe.call({
                method: 'retail.overrides.doctype.appointment.bulk_submit',
                args: {
                    doctype: 'Appointment',
                    docnames: selected.map(d => d.name),
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(`Submitted ${r.message.submitted.length} document(s).`);
                        listview.refresh();
                    }
                }
            });
        });
    }
};
