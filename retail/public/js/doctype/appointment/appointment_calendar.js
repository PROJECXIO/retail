frappe.views.calendar["Appointment"] = {
	field_map: {
		start: "scheduled_time",
		end: "custom_ends_on",
		id: "name",
		// allDay: "all_day",
		title: "subject",
		status: "status",
		color: "color",
		resource: "custom_vehicle",
	},
	style_map: {
		Closed: "success",
		Unverified: "info",
		Open: "warning",
	},
	update_event_method:
		"retail.overrides.doctype.appointment.update_appointment",
	get_events_method: "retail.overrides.doctype.appointment.get_appointments",
	options: {
		schedulerLicenseKey: "GPL-My-Project-Is-Open-Source",
		resourceLabelText: __("Resources"),
		resourceAreaWidth: "15%",
		defaultView: "agendaDay",
		eventResourceEditable: true,
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
      const color = resourceObj.color || "#3788d8";

      // Build label + tiny button
      const html = `
        <a class="fc-res-label btn-export">
          ${frappe.utils.escape_html(resourceObj.title)} ${frappe.utils.icon("link-url", "sm")}
        </a>
        <div style="
          background-color: ${color};
          max-height: 4px; height: 4px; max-width: 75%; margin: 6px auto 0;">
        </div>
      `;

      labelTds.css("padding-top", "10px").html(html);

      // Wire the button
      $(labelTds).find(".btn-export").on("click", (e) => {
        e.preventDefault();
        e.stopPropagation();

        const $fc = $(labelTds).closest(".fc");
        const center = $fc.fullCalendar("getDate").format("YYYY-MM-DD");

        // const view = $fc.fullCalendar("getView");
        // const rangeStart = view.start.format("YYYY-MM-DD");
        // const rangeEnd   = view.end.format("YYYY-MM-DD");
		const qs = $.param({
			resource_id: resourceObj.id,
			current_date: center,
			// range_start, range_end
		});

		const url = `/api/method/retail.overrides.doctype.appointment.export_vehicle_bookings_direct?${qs}`;
		window.open(url, "_blank");
        // frappe.call({
        //   method: "retail.overrides.doctype.appointment.export_vehicle_bookings",
        //   args: {
        //     resource_id: resourceObj.id,
        //     current_date: center,
        //     // range_start: rangeStart,
        //     // range_end: rangeEnd,
        //   },
        //   freeze: true,
        //   callback() {
        //     frappe.show_alert({
        //       message: __("Exported for {0}", [resourceObj.id]),
        //       indicator: "green",
        //     });
        //   },
        // });
      });
    },
		eventAfterAllRender: function () {
			$("body .container").css({
				width: "90%",
				"max-width": "100%",
			});
			$(".footnote-area").hide();
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
			doc.custom_vehicle =
				resource && resource.id !== "unassigned" ? resource.id : null;
			frappe.set_route("Form", "Appointment", doc.name);
		},
	},
};
