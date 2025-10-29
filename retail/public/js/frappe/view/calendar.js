frappe.views.Calendar = class Calendar extends frappe.views.Calendar {
	prepare_events(events) {
		var me = this;

		return (events || []).map((d) => {
			d.id = d.name;
			d.editable = frappe.model.can_write(d.doctype || me.doctype);

			// do not allow submitted/cancelled events to be moved / extended
			if (d.docstatus && d.docstatus > 0) {
				d.editable = false;
			}

			$.each(me.field_map, function (target, source) {
				d[target] = d[source];
			});

			if (typeof d.allDay === "undefined") {
				d.allDay = me.field_map.allDay;
			}

			if (!me.field_map.convertToUserTz) d.convertToUserTz = 1;

			// convert to user tz
			if (d.convertToUserTz) {
				d.start = frappe.datetime.convert_to_user_tz(d.start);
				d.end = frappe.datetime.convert_to_user_tz(d.end);
			}

			// show event on single day if start or end date is invalid
			if (!frappe.datetime.validate(d.start) && d.end) {
				d.start = frappe.datetime.add_days(d.end, -1);
			}

			if (d.start && !frappe.datetime.validate(d.end)) {
				d.end = frappe.datetime.add_days(d.start, 1);
			}

			me.fix_end_date_for_event_render(d);
			me.prepare_colors(d);

			d.title = frappe.utils.html2text(d.title);

			return d;
		});
	}
	get_update_args(event) {
		var me = this;
		var args = {
			name: event[this.field_map.id],
		};
		const resourceId = event.resourceId == "unassigned" ? null : event.resourceId;
		if(resourceId != event.resource){
			args[this.field_map.resource] = resourceId;
		}
		args[this.field_map.start] = me.get_system_datetime(event.start);

		if (this.field_map.allDay)
			args[this.field_map.allDay] = event.start._ambigTime && event.end._ambigTime ? 1 : 0;

		if (this.field_map.end) {
			if (!event.end) {
				event.end = event.start.add(1, "hour");
			}

			args[this.field_map.end] = me.get_system_datetime(event.end);

			if (args[this.field_map.allDay]) {
				args[this.field_map.end] = me.get_system_datetime(
					moment(event.end).subtract(1, "s")
				);
			}
		}

		args.doctype = event.doctype || this.doctype;
		return { args: args, field_map: this.field_map };
	}
}

frappe.views.CalendarView = class CalendarView extends frappe.views.CalendarView {
    get required_libs() {
		let assets = [
			"assets/frappe/js/lib/fullcalendar/fullcalendar.min.css",
			"assets/frappe/js/lib/fullcalendar/fullcalendar.min.js",
            "assets/retail/js/frappe/view/scheduler.min.js",
            "assets/retail/js/frappe/view/scheduler.min.css",
		];
		let user_language = frappe.boot.lang;
		if (user_language && user_language !== "en") {
			assets.push("assets/frappe/js/lib/fullcalendar/locale-all.js");
		}
		return assets;
	}
};
