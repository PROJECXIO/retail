import "../../../../../frappe/frappe/public/js/frappe/form/controls/time";

frappe.ui.form.ControlTime = class ControlTime extends (
    frappe.ui.form.ControlTime
) {
    set_time_options() {
        let sysdefaults = frappe.boot.sysdefaults;
        const me = this;
        let time_format =
            sysdefaults && sysdefaults.time_format
                ? sysdefaults.time_format
                : "HH:mm:ss";

        this.time_format = frappe.defaultTimeFormat;
        this.datepicker_options = {
            language: "en",
            timepicker: true,
            onlyTimepicker: true,
            timeFormat: time_format
                .toLowerCase()
                .replace("mm", "ii")
                .replace("a", "AA"),
            startDate: frappe.datetime.now_time(true),
            onSelect: () => {
                // ignore micro seconds
                if (
                    moment(this.get_value(), time_format).format(time_format) !=
                    moment(this.value, time_format).format(time_format)
                ) {
                    this.$input.trigger("change");
                }
            },
            onShow: (dp) => {
                let $dp = $(dp.$datepicker);
                $(".datepicker--button:visible").text(__("Now"));
                if (!$dp.find(".custom-time-selects").length) {
                    $dp.find(".datepicker--buttons").hide();
                    $dp.find(".datepicker--time-sliders").hide();
                    $dp.find(".datepicker--time-current").hide();
                    me.injectTimeSelects(dp);
                }
                this.update_datepicker_position();
            },
            keyboardNav: false,
            todayButton: true,
        };
    }
    injectTimeSelects(dp) {
        let $container = $(dp.$datepicker).find(".datepicker--time");
        // if ($container.find(".custom-time-selects").length) return;

        // detect time format from sysdefaults
        let sysdefaults = frappe.boot.sysdefaults;
        let time_format =
            sysdefaults && sysdefaults.time_format
                ? sysdefaults.time_format
                : "HH:mm:ss";

        let is12h = /a|A/.test(time_format); // check for AM/PM
        let hasSeconds = /s{1,2}/.test(time_format); // check for seconds

        // Build dynamic fields
        let ampmHtml = "";
        if (is12h) {
            ampmHtml = `
            <div class="am-pm" style="display:flex; flex-direction:column; margin-left:8px; gap:5px;">
                <button type="button" class="btn-am btn btn-default btn-sm">${__(
                "AM"
            )}</button>
                <button type="button" class="btn-pm btn btn-default btn-sm">${__(
                "PM"
            )}</button>
            </div>`;
        }

        let secondsHtml = "";
        if (hasSeconds) {
            secondsHtml = `
            <span style="font-size:15px; font-weight:bold;">:</span>
            <input type="number" class="time-second input-with-feedback form-control bold"
                min="0" max="59" step="1" placeholder="SS">`;
        }

        // Wrapper HTML
        let $wrapper = $(`
        <div class="custom-time-selects" style="margin:10px auto; text-align:center;">
            <div class="time-boxes" style="display:flex; align-items:center; justify-content:center; gap:6px;">
                <input type="number" class="time-hour input-with-feedback form-control bold" 
                    ${is12h ? 'min="1" max="12"' : 'min="0" max="23"'
            } placeholder="HH">
                <span style="font-size:15px; font-weight:bold;">:</span>
                <input type="number" class="time-minute input-with-feedback form-control bold" min="0" max="59" step="1" placeholder="MM">
                ${secondsHtml}
                ${ampmHtml}
            </div>
            <div class="action-buttons" style="margin-top:12px; display:flex; justify-content:center; gap:5px;">
                <button type="button" class="btn-cancel btn btn-default btn-sm">${frappe.utils.icon(
                "close",
                "sm"
            )}</button>
                <button type="button" class="btn-now btn btn-default btn-sm">${frappe.utils.icon(
                "select",
                "sm"
            )}</button>
                <button type="button" class="btn-ok btn btn-primary btn-sm">${frappe.utils.icon(
                "check",
                "sm"
            )}</button>
            </div>
        </div>
    `);

        $container.append($wrapper);

        let $hour = $wrapper.find(".time-hour");
        let $minute = $wrapper.find(".time-minute");
        let $second = $wrapper.find(".time-second");
        let $btnAM = $wrapper.find(".am-pm .btn-am");
        let $btnPM = $wrapper.find(".am-pm .btn-pm");
        let $btnCancel = $wrapper.find(".action-buttons .btn-cancel");
        let $btnNow = $wrapper.find(".action-buttons .btn-now");
        let $btnOk = $wrapper.find(".action-buttons .btn-ok");

        // AM/PM toggle
        let meridian = "AM";
        if (is12h) {
            $btnAM.on("click", (e) => {
                e.stopPropagation();
                meridian = "AM";
                $btnAM.removeClass("btn-default").addClass("btn-primary");
                $btnPM.removeClass("btn-primary").addClass("btn-default");
            });
            $btnPM.on("click", (e) => {
                e.stopPropagation();
                meridian = "PM";
                $btnPM.removeClass("btn-default").addClass("btn-primary");
                $btnAM.removeClass("btn-primary").addClass("btn-default");
            });
        }

        // OK button → update picker
        $btnOk.on("click", (e) => {
            e.stopPropagation();
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

        // Cancel → just close
        $btnCancel.on("click", (e) => {
            e.stopPropagation();
            dp.hide();
        });

        // NOW button → set current time
        $btnNow.on("click", (e) => {
            e.stopPropagation();
            let now = new Date();
            let h = now.getHours();
            let m = now.getMinutes();
            let s = now.getSeconds();

            if (is12h) {
                meridian = h >= 12 ? "PM" : "AM";
                h = h % 12 || 12;
            }

            $hour.val(h);
            $minute.val(m.toString().padStart(2, "0"));
            if (hasSeconds) $second.val(s.toString().padStart(2, "0"));

            if (is12h) {
                if (meridian === "PM") $btnPM.trigger("click");
                else $btnAM.trigger("click");
            }

            dp.selectDate(now);
            dp.hide();
        });

        // Initialize with current selected time
        if (dp.selectedDates[0]) {
            let d = dp.selectedDates[0];
            let h = d.getHours();
            let m = d.getMinutes();
            let s = d.getSeconds();

            if (is12h) {
                meridian = h >= 12 ? "PM" : "AM";
                h = h % 12 || 12;
            }

            $hour.val(h);
            $minute.val(m.toString().padStart(2, "0"));
            if (hasSeconds) $second.val(s.toString().padStart(2, "0"));

            if (is12h) {
                if (meridian === "PM") $btnPM.trigger("click");
                else $btnAM.trigger("click");
            }
        }
    }
};
