import "../../../../../frappe/frappe/public/js/frappe/form/controls/time";

frappe.ui.form.ControlTime = class ControlTime extends frappe.ui.form.ControlTime {
    set_time_options() {
        const sysdefaults = frappe.boot.sysdefaults;
        const me = this;
        const time_format = (sysdefaults && sysdefaults.time_format) || "HH:mm:ss";
        const parseInput = (val) => (val ? frappe.datetime.user_to_obj(val) : null);
        this.time_format = time_format;

        this.datepicker_options = {
            language: "en",
            timepicker: true,
            onlyTimepicker: true,
            autoClose: false,
            timeFormat: time_format.toLowerCase().replace("mm", "ii").replace("a", "AA"),
            // Don’t force “now” — use input value if present
            onSelect: () => {
                if (
                    moment(this.get_value(), time_format).format(time_format) !==
                    moment(this.value, time_format).format(time_format)
                ) {
                    this.$input.trigger("change");
                }
            },
            onShow: (dp) => {
                const $dp = $(dp.$datepicker);
                $dp.find(".datepicker--button:visible").text(__("Now"));

                // If input has value but no selection yet, seed picker from input
                if (!dp.selectedDates.length && this.value) {
                    const dt = parseInput(this.value);
                    if (dt) dp.selectDate(dt);
                }

                if (!$dp.find(`.custom-time-selects-${this.df.fieldname}`).length) {
                    $dp.find(".datepicker--buttons, .datepicker--time-sliders, .datepicker--time-current").hide();
                    me.injectTimeSelects(dp);
                }

                setTimeout(() => {
                    me.scrollAllToActive(dp);
                }, 0);

                this.update_datepicker_position();
            },
            keyboardNav: false,
            todayButton: true,
        };
    }

    scrollToActive($list) {
        const $active = $list.find(".time-option.btn-primary");
        if ($active.length) {
            $list.stop().animate({
                scrollTop:
                    $active.position().top +
                    $list.scrollTop() -
                    $list.height() / 2 +
                    $active.outerHeight() / 2,
            }, 200);
        }
    }

    scrollAllToActive(dp) {
        const $dp = $(dp.$datepicker);
        this.scrollToActive($dp.find(".hour-scroll"));
        this.scrollToActive($dp.find(".minute-scroll"));
        this.scrollToActive($dp.find(".second-scroll"));
    }

    injectTimeSelects(dp) {
        const $dp = $(dp.$datepicker);
        const $container = $dp.find(".datepicker--time");

        const sysdefaults = frappe.boot.sysdefaults;
        const time_format = (sysdefaults && sysdefaults.time_format) || "HH:mm:ss";
        const is12h = /a|A/.test(time_format);
        const hasSeconds = /s{1,2}/.test(time_format);

        const wrapperClass = `custom-time-selects-${this.df.fieldname}`;
        if ($container.find(`.${wrapperClass}`).length) return;

        const ampmHtml = is12h
            ? `<div class="am-pm" style="display:flex; flex-direction:column; margin-left:8px; gap:5px;">
                   <button type="button" class="btn-am btn btn-default btn-sm">${__("AM")}</button>
                   <button type="button" class="btn-pm btn btn-default btn-sm">${__("PM")}</button>
               </div>`
            : "";

        const $wrapper = $(`
            <div class="${wrapperClass}" style="margin:10px auto; text-align:center;">
                <div class="time-boxes" style="display:flex; align-items:center; justify-content:center; gap:6px;">
                    <div class="time-scroll hour-scroll" style="max-height:120px; overflow-y:auto;"></div>
                    <span style="font-size:15px; font-weight:bold;">:</span>
                    <div class="time-scroll minute-scroll" style="max-height:120px; overflow-y:auto;"></div>
                    ${hasSeconds ? '<span style="font-size:15px; font-weight:bold;">:</span><div class="time-scroll second-scroll" style="max-height:120px; overflow-y:auto;"></div>' : ""}
                    ${ampmHtml}
                </div>
                <div class="action-buttons" style="margin-top:12px; display:flex; justify-content:center; gap:5px;">
                    <button type="button" class="btn-now btn btn-default btn-sm">${frappe.utils.icon("select","sm")} ${__("Now")}</button>
                </div>
            </div>
        `);

        $container.append($wrapper);

        const buildScroll = ($el, max, min = 0) => {
            let html = "";
            for (let i = min; i <= max; i++) {
                const val = i.toString().padStart(2, "0");
                html += `<div class="time-option btn" data-val="${i}" style="padding:4px; cursor:pointer;">${val}</div>`;
            }
            $el.html(html);
        };

        buildScroll($wrapper.find(".hour-scroll"), is12h ? 12 : 23, is12h ? 1 : 0);
        buildScroll($wrapper.find(".minute-scroll"), 59);
        if (hasSeconds) buildScroll($wrapper.find(".second-scroll"), 59);

        const $btnAM  = $wrapper.find(".am-pm .btn-am");
        const $btnPM  = $wrapper.find(".am-pm .btn-pm");
        const $btnNow = $wrapper.find(".action-buttons .btn-now");

        this.meridian = this.meridian || "AM";

        const updateFromUI = () => {
            let h = parseInt($wrapper.find(".hour-scroll   .btn-primary").data("val")) || 0;
            let m = parseInt($wrapper.find(".minute-scroll .btn-primary").data("val")) || 0;
            let s = hasSeconds ? (parseInt($wrapper.find(".second-scroll .btn-primary").data("val")) || 0) : 0;

            if (is12h) {
                if (this.meridian === "PM" && h < 12) h += 12;
                if (this.meridian === "AM" && h === 12) h = 0;
            }

            const date = dp.selectedDates[0] || new Date();
            date.setHours(h, m, s);
            dp.selectDate(date);
        };

        $wrapper.on("click", ".time-option", (e) => {
            e.stopPropagation();
            const $opt  = $(e.currentTarget);
            const $list = $opt.closest(".time-scroll");
            $list.find(".time-option").removeClass("btn-primary");
            $opt.addClass("btn-primary");
            updateFromUI();
            this.scrollToActive($list);
        });

        if (is12h) {
            $btnAM.on("click", (e) => {
                e.stopPropagation();
                this.meridian = "AM";
                $btnAM.addClass("btn-primary").removeClass("btn-default");
                $btnPM.addClass("btn-default").removeClass("btn-primary");
                updateFromUI();
            });
            $btnPM.on("click", (e) => {
                e.stopPropagation();
                this.meridian = "PM";
                $btnPM.addClass("btn-primary").removeClass("btn-default");
                $btnAM.addClass("btn-default").removeClass("btn-primary");
                updateFromUI();
            });
        }

        $btnNow.on("click", (e) => {
            e.stopPropagation();
            const now = new Date();
            let h = now.getHours(), m = now.getMinutes(), s = now.getSeconds();

            if (is12h) {
                this.meridian = h >= 12 ? "PM" : "AM";
                h = h % 12 || 12;
            }

            $wrapper.find(".hour-scroll   .time-option").removeClass("btn-primary").filter(`[data-val='${h}']`).addClass("btn-primary");
            $wrapper.find(".minute-scroll .time-option").removeClass("btn-primary").filter(`[data-val='${m}']`).addClass("btn-primary");
            if (hasSeconds) $wrapper.find(".second-scroll .time-option").removeClass("btn-primary").filter(`[data-val='${s}']`).addClass("btn-primary");

            if (is12h) {
                (this.meridian === "PM" ? $btnPM : $btnAM).addClass("btn-primary").removeClass("btn-default");
            }

            dp.selectDate(now);
            this.scrollAllToActive(dp);
        });

        // initialize from existing value (not "now")
        const initDate = dp.selectedDates[0]
            || (this.value ? frappe.datetime.user_to_obj(this.value) : null);

        if (initDate) {
            let ih = initDate.getHours(), im = initDate.getMinutes(), is = initDate.getSeconds();
            if (is12h) {
                this.meridian = ih >= 12 ? "PM" : "AM";
                ih = ih % 12 || 12;
            }

            $wrapper.find(".hour-scroll   .time-option").filter(`[data-val='${ih}']`).addClass("btn-primary");
            $wrapper.find(".minute-scroll .time-option").filter(`[data-val='${im}']`).addClass("btn-primary");
            if (hasSeconds) $wrapper.find(".second-scroll .time-option").filter(`[data-val='${is}']`).addClass("btn-primary");

            if (is12h) {
                (this.meridian === "PM" ? $btnPM : $btnAM).addClass("btn-primary").removeClass("btn-default");
            }

            this.scrollAllToActive(dp);
        }
    }
};
