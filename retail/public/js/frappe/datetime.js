import "../../../../../frappe/frappe/public/js/frappe/form/controls/datetime";

frappe.ui.form.ControlDatetime = class ControlDatetime extends (
	frappe.ui.form.ControlDatetime
) {
	set_date_options() {
		super.set_date_options();
		this.today_text = __("Now");
		let sysdefaults = frappe.boot.sysdefaults;
		this.date_format = frappe.defaultDatetimeFormat;
		let time_format =
			sysdefaults && sysdefaults.time_format
				? sysdefaults.time_format
				: "HH:mm:ss";

		$.extend(this.datepicker_options, {
			timepicker: true,
			autoClose: false,
			timeFormat: time_format
				.toLowerCase()
				.replace("mm", "ii")
				.replace("a", "AA"),
		});
	}
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

		// unique wrapper per field
		let wrapperClass = `custom-datetime-selects-${this.df.fieldname}`;
		if ($container.find(`.${wrapperClass}`).length) return;

		// detect format
		let sysdefaults = frappe.boot.sysdefaults;
		let time_format =
			sysdefaults && sysdefaults.time_format
				? sysdefaults.time_format
				: "HH:mm:ss";

		let is12h = /a|A/.test(time_format);
		let hasSeconds = /s{1,2}/.test(time_format);

		// AM/PM buttons
		let ampmHtml = is12h
			? `
				<div class="am-pm" style="display:flex; flex-direction:column; margin-left:8px; gap:5px;">
					<button type="button" class="btn-am btn btn-default btn-sm">${__(
							"AM"
						)}</button>
					<button type="button" class="btn-pm btn btn-default btn-sm">${__(
							"PM"
						)}</button>
				</div>`
			: "";

		// wrapper
		let $wrapper = $(`
    <div class="${wrapperClass}" style="margin:10px auto; text-align:center;">
        <div class="time-boxes" style="display:flex; align-items:center; justify-content:center; gap:6px;">
            <div class="time-scroll hour-scroll" style="max-height:120px; overflow-y:auto;"></div>
            <span style="font-size:15px; font-weight:bold;">:</span>
            <div class="time-scroll minute-scroll" style="max-height:120px; overflow-y:auto;"></div>
            ${hasSeconds
				? '<span style="font-size:15px; font-weight:bold;">:</span><div class="time-scroll second-scroll" style="max-height:120px; overflow-y:auto;"></div>'
				: ""
			}
            ${ampmHtml}
        </div>
        <div class="action-buttons" style="margin-top:12px; display:flex; justify-content:center; gap:5px;">
            <button type="button" class="btn-now btn btn-default btn-sm">${frappe.utils.icon(
				"select",
				"sm"
			)} ${__("Now")}</button>
        </div>
    </div>`);

		$container.append($wrapper);

		// helpers
		function buildScroll($el, max, min = 0) {
			let html = "";
			for (let i = min; i <= max; i++) {
				let val = i.toString().padStart(2, "0");
				html += `<div class="time-option btn" data-val="${i}" style="padding:4px; cursor:pointer;">${val}</div>`;
			}
			$el.html(html);
		}
		function scrollToActive($list) {
			let $active = $list.find(".time-option.btn-primary");
			if ($active.length) {
				$list.scrollTop(
					$active.position().top +
					$list.scrollTop() -
					$list.height() / 2 +
					$active.outerHeight() / 2
				);
			}
		}

		buildScroll($wrapper.find(".hour-scroll"), is12h ? 12 : 23, is12h ? 1 : 0);
		buildScroll($wrapper.find(".minute-scroll"), 59);
		if (hasSeconds) buildScroll($wrapper.find(".second-scroll"), 59);

		let $btnAM = $wrapper.find(".am-pm .btn-am");
		let $btnPM = $wrapper.find(".am-pm .btn-pm");
		let $btnNow = $wrapper.find(".action-buttons .btn-now");

		// per-instance meridian
		this.meridian = this.meridian || "AM";

		const updateFromInputs = () => {
			let h = parseInt($wrapper.find(".hour-scroll .btn-primary").data("val")) || 0;
			let m =
				parseInt($wrapper.find(".minute-scroll .btn-primary").data("val")) || 0;
			let s = hasSeconds
				? parseInt($wrapper.find(".second-scroll .btn-primary").data("val")) || 0
				: 0;

			if (is12h) {
				if (this.meridian === "PM" && h < 12) h += 12;
				if (this.meridian === "AM" && h === 12) h = 0;
			}

			let date = dp.selectedDates[0] || new Date();
			date.setHours(h, m, s);

			dp.selectDate(date);
		};

		// option click → update instantly
		$wrapper.find(".time-option").on("click", (e) => {
			e.stopPropagation();
			let $opt = $(e.currentTarget);
			let $list = $opt.closest(".time-scroll");
			$list.find(".time-option").removeClass("btn-primary");
			$opt.addClass("btn-primary");
			updateFromInputs();
		});

		// AM/PM toggle → update instantly
		if (is12h) {
			$btnAM.on("click", () => {
				this.meridian = "AM";
				$btnAM.addClass("btn-primary").removeClass("btn-default");
				$btnPM.addClass("btn-default").removeClass("btn-primary");
				updateFromInputs();
			});
			$btnPM.on("click", () => {
				this.meridian = "PM";
				$btnPM.addClass("btn-primary").removeClass("btn-default");
				$btnAM.addClass("btn-default").removeClass("btn-primary");
				updateFromInputs();
			});
		}

		// NOW button
		$btnNow.on("click", () => {
			let now = new Date();
			let h = now.getHours();
			let m = now.getMinutes();
			let s = now.getSeconds();

			if (is12h) {
				this.meridian = h >= 12 ? "PM" : "AM";
				h = h % 12 || 12;
			}

			$wrapper
				.find(".hour-scroll .time-option")
				.removeClass("btn-primary")
				.filter(`[data-val='${h}']`)
				.addClass("btn-primary");
			$wrapper
				.find(".minute-scroll .time-option")
				.removeClass("btn-primary")
				.filter(`[data-val='${m}']`)
				.addClass("btn-primary");
			if (hasSeconds) {
				$wrapper
					.find(".second-scroll .time-option")
					.removeClass("btn-primary")
					.filter(`[data-val='${s}']`)
					.addClass("btn-primary");
			}

			if (is12h) {
				if (this.meridian === "PM") $btnPM.trigger("click");
				else $btnAM.trigger("click");
			}

			dp.selectDate(now); // update immediately
			dp.hide(); // close after "Now"
		});

		// Initialize with current value
		let initDate =
			dp.selectedDates[0] ||
			(this.value ? frappe.datetime.user_to_obj(this.value) : null) ||
			new Date();
		let h = initDate.getHours(),
			m = initDate.getMinutes(),
			s = initDate.getSeconds();

		if (is12h) {
			this.meridian = h >= 12 ? "PM" : "AM";
			h = h % 12 || 12;
		}

		$wrapper
			.find(".hour-scroll .time-option")
			.filter(`[data-val='${h}']`)
			.addClass("btn-primary");
		$wrapper
			.find(".minute-scroll .time-option")
			.filter(`[data-val='${m}']`)
			.addClass("btn-primary");
		if (hasSeconds) {
			$wrapper
				.find(".second-scroll .time-option")
				.filter(`[data-val='${s}']`)
				.addClass("btn-primary");
		}
		if (is12h) {
			if (this.meridian === "PM")
				$btnPM.addClass("btn-primary").removeClass("btn-default");
			else $btnAM.addClass("btn-primary").removeClass("btn-default");
		}

		// scroll lists to active value
		scrollToActive($wrapper.find(".hour-scroll"));
		scrollToActive($wrapper.find(".minute-scroll"));
		if (hasSeconds) scrollToActive($wrapper.find(".second-scroll"));
	}
};
