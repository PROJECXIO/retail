import "../../../../../frappe/frappe/public/js/frappe/form/controls/datetime";

frappe.ui.form.ControlDatetime = class ControlDatetime extends frappe.ui.form.ControlDatetime {
    set_datepicker() {
		super.set_datepicker();
		if (this.datepicker.opts.timeFormat.indexOf("s") == -1) {
			// No seconds in time format
			const $tp = this.datepicker.timepicker;
			$tp.$seconds.parent().css("display", "none");
			$tp.$secondsText.css("display", "none");
			$tp.$secondsText.prev().css("display", "none");
		}
		$(".datepicker--buttons").css("display", "none");
		$(".datepicker--time-sliders").css("display", "none");
		$(".datepicker--time-current").css("display", "none");
		this.injectTimeSelects(this.datepicker);
	}
	injectTimeSelects(dp) {
		let $container = $(dp.$datepicker).find(".datepicker--time");
		if ($container.find(".custom-time-selects").length) return;

		// detect time format
		let sysdefaults = frappe.boot.sysdefaults;
		let time_format =
			sysdefaults && sysdefaults.time_format ? sysdefaults.time_format : "HH:mm:ss";

		let is12h = /a|A/.test(time_format);
		let hasSeconds = /s{1,2}/.test(time_format);

		// dynamic HTML
		let ampmHtml = is12h
			? `
        <div class="am-pm" style="display:flex; flex-direction:column; margin-left:8px; gap:5px;">
            <button type="button" class="btn-am btn btn-default btn-sm">${__("AM")}</button>
            <button type="button" class="btn-pm btn btn-default btn-sm">${__("PM")}</button>
        </div>`
			: "";

		let secondsHtml = hasSeconds
			? `
        <span style="font-size:15px; font-weight:bold;">:</span>
        <input type="number" class="time-second input-with-feedback form-control bold" min="0" max="59" step="1" placeholder="SS">`
			: "";

		let $wrapper = $(`
        <div class="custom-time-selects" style="margin:10px auto; text-align:center;">
            <div class="time-boxes" style="display:flex; align-items:center; justify-content:center; gap:6px;">
                <input type="number" class="time-hour input-with-feedback form-control bold" 
                    ${is12h ? 'min="1" max="12"' : 'min="0" max="23"'} placeholder="HH">
                <span style="font-size:15px; font-weight:bold;">:</span>
                <input type="number" class="time-minute input-with-feedback form-control bold" min="0" max="59" step="1" placeholder="MM">
                ${secondsHtml}
                ${ampmHtml}
            </div>
            <div class="action-buttons" style="margin-top:12px; display:flex; justify-content:center; gap:5px;">
                <button type="button" class="btn-cancel btn btn-default btn-sm">${frappe.utils.icon("close", "sm")}</button>
                <button type="button" class="btn-now btn btn-default btn-sm">${frappe.utils.icon("select", "sm")}</button>
                <button type="button" class="btn-ok btn btn-primary btn-sm">${frappe.utils.icon("check", "sm")}</button>
            </div>
        </div>
    `);

		$container.append($wrapper);

		let $hour = $wrapper.find(".time-hour");
		let $minute = $wrapper.find(".time-minute");
		let $second = $wrapper.find(".time-second");
		let $btnAM = $wrapper.find(".am-pm .btn-am");
		let $btnPM = $wrapper.find(".am-pm .btn-pm");
		// helper to fill inputs
		let updateInputsFromDate = (d) => {
			if (!d) return;
			let h = d.getHours(), m = d.getMinutes(), s = d.getSeconds();
			if (is12h) {
				meridian = h >= 12 ? "PM" : "AM";
				h = h % 12 || 12;
			}
			$hour.val(h);
			$minute.val(m.toString().padStart(2, "0"));
			if (hasSeconds) $second.val(s.toString().padStart(2, "0"));
			if (is12h) {
				if (meridian === "PM") $btnPM.addClass("btn-primary").removeClass("btn-default");
				else $btnAM.addClass("btn-primary").removeClass("btn-default");
			}
		};
		let initialDate = null;
		if (this.value) {
			initialDate = frappe.datetime.user_to_obj(this.value);
		}
		if (!initialDate || isNaN(initialDate.getTime())) {
			initialDate = new Date();
		}
		console.log(initialDate)
		updateInputsFromDate(initialDate);
		let meridian = "AM";

		// AM/PM toggle
		if (is12h) {
			$btnAM.on("click", () => {
				meridian = "AM";
				$btnAM.addClass("btn-primary").removeClass("btn-default");
				$btnPM.addClass("btn-default").removeClass("btn-primary");
			});
			$btnPM.on("click", () => {
				meridian = "PM";
				$btnPM.addClass("btn-primary").removeClass("btn-default");
				$btnAM.addClass("btn-default").removeClass("btn-primary");
			});
		}

		// OK → update datetime
		$wrapper.find(".btn-ok").on("click", () => {
			let h = parseInt($hour.val()) || 0;
			let m = parseInt($minute.val()) || 0;
			let s = hasSeconds ? parseInt($second.val()) || 0 : 0;

			if (is12h) {
				if (meridian === "PM" && h < 12) h += 12;
				if (meridian === "AM" && h === 12) h = 0;
			}

			let date = dp.selectedDates[0] || new Date();
			date.setHours(h, m, s);
			dp.selectDate(date);
			dp.hide();
		});

		// Cancel
		$wrapper.find(".btn-cancel").on("click", () => dp.hide());

		// NOW
		$wrapper.find(".btn-now").on("click", () => {
			let now = new Date();
			let h = now.getHours(),
				m = now.getMinutes(),
				s = now.getSeconds();

			if (is12h) {
				meridian = h >= 12 ? "PM" : "AM";
				h = h % 12 || 12;
			}

			$hour.val(h);
			$minute.val(m.toString().padStart(2, "0"));
			if (hasSeconds) $second.val(s.toString().padStart(2, "0"));

			if (is12h) (meridian === "PM" ? $btnPM : $btnAM).trigger("click");

			dp.selectDate(now);
			dp.hide();
		});

		// Initialize with current value
		if (dp.selectedDates[0]) {
			let d = dp.selectedDates[0];
			let h = d.getHours(),
				m = d.getMinutes(),
				s = d.getSeconds();

			if (is12h) {
				meridian = h >= 12 ? "PM" : "AM";
				h = h % 12 || 12;
			}

			$hour.val(h);
			$minute.val(m.toString().padStart(2, "0"));
			if (hasSeconds) $second.val(s.toString().padStart(2, "0"));

			if (is12h) (meridian === "PM" ? $btnPM : $btnAM).trigger("click");
		}
	}
}