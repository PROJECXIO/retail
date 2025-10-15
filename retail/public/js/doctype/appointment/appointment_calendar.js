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
		defaultView: "agendaDay",
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
		resourceRender: function (resourceObj, labelTds) {
			// labelTds is a jQuery <td> element for the header
			const color = resourceObj.color || "#3788d8";
			labelTds.css("padding-top", "10px");
			$(labelTds).append(`
				<div style="
							background-color: ${color};
							max-height: 4px;
							height: 4px;
							max-width: 75%;
							margin: auto;">
				</div>`);
		},
		select: function (startDate, endDate, jsEvent, view, resource) {
			if (view.name === "month" && endDate - startDate === 86400000) {
				// detect single day click in month view
				return;
			}
			function get_system_datetime(date) {
				date._offset = moment(date).tz(frappe.sys_defaults.time_zone)._offset;
				return frappe.datetime.convert_to_system_tz(moment(date).locale("en"));
			}
			var doc = frappe.model.get_new_doc("Appointment");
			doc.scheduled_time = get_system_datetime(startDate);
			doc.custom_vehicle = resource && resource.id !== "unassigned" ? resource.id : null;
			frappe.set_route("Form", "Appointment", doc.name);
		},
	},
};
