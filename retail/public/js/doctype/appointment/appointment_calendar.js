frappe.views.calendar["Appointment"] = {
	field_map: {
		start: "scheduled_time",
		end: "ends_on",
		id: "name",
		// allDay: "all_day",
		title: "subject",
		status: "status",
		color: "color",
		resource: "vehicle",
	},
	style_map: {
		Closed: "success",
		Unverified: "info",
		Open: "warning",
	},
	get_events_method: "retail.overrides.doctype.appointment.get_appointments",
	options: {
		schedulerLicenseKey: "GPL-My-Project-Is-Open-Source",
		resourceLabelText: __("Resources"),
		resourceAreaWidth: "15%",
		resources: function (callback) {
			frappe.call({
				method: "frappe.client.get_list",
				args: {
					doctype: "Vehicle",
					fields: ["name", "custom_vehicle_name", "custom_color_2"],
					limit_page_length: 1000,
				},
				callback: function (r) {
					if (r.message) {
						const resources = r.message.map((v) => ({
							id: v.name,
							title: v.custom_vehicle_name || v.name,
							color: v.custom_color_2 || "#3788d8",
						}));
						callback([
							{ id: "unassigned", title: __("Unassigned") },
							...resources,
						]);
					} else {
						callback([{ id: "unassigned", title: __("Unassigned") }]);
					}
				},
				error: function () {
					callback([{ id: "unassigned", title: __("Unassigned") }]);
				},
			});
		},
		resourceRender: function(resourceObj, labelTds) {
			// labelTds is a jQuery <td> element for the header
			const color = resourceObj.color || "#3788d8";
			labelTds.css('padding-top', '10px');
			$(labelTds).append(`
				<div style="
							background-color: ${color};
							max-height: 4px;
							height: 4px;
							max-width: 75%;
							margin: auto;">
				</div>`);
		},
	},
};
