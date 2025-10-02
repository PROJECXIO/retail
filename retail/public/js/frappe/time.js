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
                if (
                    moment(this.get_value(), time_format).format(time_format) !=
                    moment(this.value, time_format).format(time_format)
                ) {
                    this.$input.trigger("change");
                }
            },
            onShow: (dp) => {
                let $dp = $(dp.$datepicker);
                $dp.find(".datepicker--button:visible").text(__("Now"));
                if (!$dp.find(`.custom-time-selects-${this.df.fieldname}`).length) {
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

        let sysdefaults = frappe.boot.sysdefaults;
        let time_format =
            sysdefaults && sysdefaults.time_format
                ? sysdefaults.time_format
                : "HH:mm:ss";

        let is12h = /a|A/.test(time_format);
        let hasSeconds = /s{1,2}/.test(time_format);

        // wrapper with unique class for each field
        let wrapperClass = `custom-time-selects-${this.df.fieldname}`;

        // AM/PM toggle buttons
        let ampmHtml = "";
        if (is12h) {
            ampmHtml = `
        <div class="am-pm" style="display:flex; flex-direction:column; margin-left:8px; gap:5px;">
            <button type="button" class="btn-am btn btn-default btn-sm">${__("AM")}</button>
            <button type="button" class="btn-pm btn btn-default btn-sm">${__("PM")}</button>
        </div>`;
        }

        // Wrapper
        let $wrapper = $(`
        <div class="${wrapperClass}" style="margin:10px auto; text-align:center;">
            <div class="time-boxes" style="display:flex; align-items:center; justify-content:center; gap:6px;">
                <div class="time-scroll hour-scroll"></div>
                <span style="font-size:15px; font-weight:bold;">:</span>
                <div class="time-scroll minute-scroll"></div>
                ${hasSeconds
                    ? '<span style="font-size:15px; font-weight:bold;">:</span><div class="time-scroll second-scroll"></div>'
                    : ""
                }
                ${ampmHtml}
            </div>
        </div>
        `);

        $container.append($wrapper);

        // helper to build scroll list
        function buildScroll($el, max, min = 0) {
            let html = "";
            for (let i = min; i <= max; i++) {
                let val = i.toString().padStart(2, "0");
                html += `<div class="time-option btn" data-val="${i}">${val}</div>`;
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

        // 🔹 store meridian per field instance
        this.meridian = this.meridian || "AM";

        const updateFromInputs = () => {
            let h = parseInt($wrapper.find(".hour-scroll .btn-primary").data("val")) || 0;
            let m = parseInt($wrapper.find(".minute-scroll .btn-primary").data("val")) || 0;
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

        // handle option clicks
        $wrapper.find(".time-option").on("click", (e) => {
            e.stopPropagation();
            let $opt = $(e.currentTarget);
            let $list = $opt.closest(".time-scroll");
            $list.find(".time-option").removeClass("btn-primary");
            $opt.addClass("btn-primary");

            updateFromInputs();
        });

        // AM/PM toggle
        if (is12h) {
            $btnAM.on("click", (e) => {
                e.stopPropagation();
                this.meridian = "AM";
                $btnAM.removeClass("btn-default").addClass("btn-primary");
                $btnPM.removeClass("btn-primary").addClass("btn-default");
                updateFromInputs();
            });

            $btnPM.on("click", (e) => {
                e.stopPropagation();
                this.meridian = "PM";
                $btnPM.removeClass("btn-default").addClass("btn-primary");
                $btnAM.removeClass("btn-primary").addClass("btn-default");
                updateFromInputs();
            });
        }

        // Initialize with current selected time
        if (dp.selectedDates[0]) {
            let d = dp.selectedDates[0];
            let h = d.getHours();
            let m = d.getMinutes();
            let s = d.getSeconds();

            if (is12h) {
                this.meridian = h >= 12 ? "PM" : "AM";
                h = h % 12 || 12;
            }

            $wrapper.find(".hour-scroll .time-option")
                .filter(`[data-val='${h}']`).addClass("btn-primary");
            $wrapper.find(".minute-scroll .time-option")
                .filter(`[data-val='${m}']`).addClass("btn-primary");

            if (hasSeconds) {
                $wrapper.find(".second-scroll .time-option")
                    .filter(`[data-val='${s}']`).addClass("btn-primary");
            }

            if (is12h) {
                if (this.meridian === "PM") $btnPM.trigger("click");
                else $btnAM.trigger("click");
            }
        }

        // scroll to active values
        scrollToActive($wrapper.find(".hour-scroll"));
        scrollToActive($wrapper.find(".minute-scroll"));
        if (hasSeconds) scrollToActive($wrapper.find(".second-scroll"));
    }
};
