frappe.views.calendar["Appointment"] = {
	field_map: {
		start: "scheduled_time",
		end: "ends_on",
		id: "name",
		// allDay: "all_day",
		title: "subject",
		status: "status",
		color: "color",
	},
	style_map: {
		Closed: "success",
		Unverified: "info",
		Open: "warning",
	},
	get_events_method: "retail.overrides.doctype.appointment.get_appointments",
};
