
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
