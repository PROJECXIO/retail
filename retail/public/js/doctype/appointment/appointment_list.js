frappe.listview_settings["Appointment"] = {
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
  onload: function (listview) {},
};
