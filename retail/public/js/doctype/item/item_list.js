(function () {
    const DOCTYPE = "Item";
    const API = "retail.utils.awesomebar.custom_search_subsequence";
    const STORAGE_KEY = "retail_subseq_last_q";

    if (window.__retail_subseq_mounted__) return;
    window.__retail_subseq_mounted__ = true;

    let reqSeq = 0;

    // --- utils ---
    function debounce(fn, ms) {
        let t;
        return function () {
            clearTimeout(t);
            const a = arguments,
                c = this;
            t = setTimeout(() => fn.apply(c, a), ms);
        };
    }

    function mount_in_page_form(listview, $el) {
        let $form;
        if (listview.$page && listview.$page.find(".page-form").length) {
            $form = listview.$page.find(".page-form");
        } else if (listview.page && listview.page.wrapper) {
            $form = $(listview.page.wrapper).find(".page-form");
        }
        if (!$form || !$form.length) {
            (listview.$page || $(listview.page.wrapper))
                .find(".page-head")
                .append($el);
        } else {
            $form.append($el);
        }
    }

    // Read all current filters except Item.item_code
    function get_other_filters(listview) {
        try {
            const fa = listview.filter_area;
            const curr = fa.get() || [];
            return curr.filter(
                (f) => !(Array.isArray(f) && f[0] === DOCTYPE && f[1] === "item_code")
            );
        } catch (e) {
            return [];
        }
    }

    // Rebuild filters: keep others; set item_code IN values, or IS NOT SET, or clear it.
    function reset_filters_with_item_code(
        listview,
        otherFilters,
        itemCodes,
        useNotSet = false
    ) {
        const fa = listview.filter_area;
        try {
            if (fa && typeof fa.clear === "function") fa.clear();
            else {
                const curr = (fa && fa.get && fa.get()) || [];
                curr.forEach((f) => {
                    try {
                        fa.remove([f]);
                    } catch (e) { }
                });
            }
            if (otherFilters && otherFilters.length) fa.add(otherFilters);
            if (useNotSet) {
                fa.add([[DOCTYPE, "item_code", "is", "not set"]]);
            } else if (itemCodes && itemCodes.length) {
                fa.add([[DOCTYPE, "item_code", "in", itemCodes]]);
            }
            listview.refresh();
        } catch (e) {
            listview.refresh();
        }
    }

    // Server call + rebuild filters
    function run_subsequence_search(listview, query, limit = 500) {
        const q = (query || "").trim();
        const mySeq = ++reqSeq;
        const others = get_other_filters(listview);

        if (!q) {
            reset_filters_with_item_code(listview, others, []); // clear item_code
            return;
        }

        return frappe
            .call({
                method: API,
                args: { q, limit },
            })
            .then((r) => {
                if (mySeq !== reqSeq) return; // ignore stale responses
                const ids = r.message || [];
                if (!ids.length) {
                    reset_filters_with_item_code(listview, others, [], true); // IS NOT SET
                } else {
                    reset_filters_with_item_code(listview, others, ids, false); // IN [...]
                }
            })
            .catch(() => { });
    }

    frappe.listview_settings[DOCTYPE] = $.extend(
        {},
        frappe.listview_settings[DOCTYPE] || {},
        {
            onload(listview) {
                // Input with inline clear button
                const $wrap = $(`
        <div class="retail-subseq-wrap" style="position:relative; margin-left:8px; display:inline-block;
        margin: var(--margin-xs) 0 var(--margin-xs) var(--margin-xs);">
          <input type="text"
                 class="form-control input-sm retail-subseq-input"
                 placeholder="${__("Search...")} "
                 style="padding-right:28px;">
          <button type="button" aria-label="${__("Clear")}"
                  class="retail-subseq-clear-btn"
                  style="
                    position:absolute; right:6px; top:13px; transform:translateY(-50%);
                    border:0; background:transparent; padding:0; line-height:1; cursor:pointer;
                    display:none; /* hidden until there's text */
                  ">
            ×
          </button>
        </div>
      `);
                mount_in_page_form(listview, $wrap);

                const $input = $wrap.find(".retail-subseq-input");
                const $clear = $wrap.find(".retail-subseq-clear-btn");

                // helper to toggle clear button visibility
                function toggleClear() {
                    const has = ($input.val() || "").length > 0;
                    $clear.css("display", has ? "inline" : "none");
                }

                // Restore last query (and apply)
                try {
                    const last = localStorage.getItem(STORAGE_KEY);
                    if (last) {
                        $input.val(last);
                        toggleClear();
                        run_subsequence_search(listview, last);
                    }
                } catch (e) { }

                // Debounced auto-apply; empty input clears immediately
                const debouncedApply = debounce(function () {
                    const val = $input.val() || "";
                    try {
                        localStorage.setItem(STORAGE_KEY, val.trim());
                    } catch (e) { }
                    run_subsequence_search(listview, val);
                }, 250);

                $input.on("input", function () {
                    toggleClear();
                    const val = ($input.val() || "").trim();
                    if (!val) {
                        reqSeq++; // invalidate inflight
                        const others = get_other_filters(listview);
                        reset_filters_with_item_code(listview, others, []); // clear item_code
                        try {
                            localStorage.setItem(STORAGE_KEY, "");
                        } catch (e) { }
                        return;
                    }
                    debouncedApply();
                });

                // Enter = immediate apply
                $input.on("keydown", function (e) {
                    if (e.key === "Enter") {
                        e.preventDefault();
                        try {
                            localStorage.setItem(STORAGE_KEY, ($input.val() || "").trim());
                        } catch (e) { }
                        run_subsequence_search(listview, $input.val());
                    }
                });

                // Inline clear button
                $clear.on("click", function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    $input.val("");
                    toggleClear();
                    try {
                        localStorage.setItem(STORAGE_KEY, "");
                    } catch (e) { }
                    reqSeq++;
                    const others = get_other_filters(listview);
                    reset_filters_with_item_code(listview, others, []); // clear item_code
                    $input.focus();
                });

                // Shortcuts
                $(document).on("keydown", function (e) {
                    if (e.ctrlKey && (e.key === "g" || e.key === "G")) {
                        e.preventDefault();
                        $input.focus().select();
                    }
                    if (e.ctrlKey && e.key === "Backspace") {
                        e.preventDefault();
                        $clear.click();
                    }
                });

                listview.page.add_inner_button(__("Print Stickers"), async () => {
                    const checked = listview.get_checked_items().map((d) => d.name);
                    if (!checked.length) {
                        frappe.msgprint(__("Please select at least one Item."));
                        return;
                    }
                    let dialog = new frappe.ui.Dialog({
                        title: __("Sticker Options"),
                        fields: [
                            {
                                fieldname: "label_size",
                                label: __("Label Size"),
                                fieldtype: "Select",
                                options: [
                                    "size-30x20",
                                    "size-38x25",
                                    "size-50x25",
                                    "size-60x25",
                                    "size-60x30",
                                ],
                                default: "size-30x20",
                                reqd: 1,
                            },
                            {
                                fieldname: "copies",
                                label: __("Copies per Item"),
                                fieldtype: "Int",
                                default: 1,
                                reqd: 1,
                            },
                            {
                                fieldname: "price_source",
                                label: __("Price Source"),
                                fieldtype: "Select",
                                options: [
                                    "standard_rate",
                                    "valuation_rate",
                                    "last_purchase_rate",
                                    "price_list_rate",
                                ],
                                default: "standard_rate",
                                reqd: 1,
                            },
                            {
                                fieldname: "barcode_type",
                                label: __("Barcode Type"),
                                fieldtype: "Select",
                                options: ["Code128", "EAN13", "QRCode"],
                                default: "Code128",
                                reqd: 1,
                            },
                            {
                                fieldname: "barcode_source",
                                label: __("Barcode Value From"),
                                fieldtype: "Select",
                                options: ["item_code", "first_item_barcode"],
                                default: "item_code",
                                reqd: 1,
                            },
                            {
                                fieldname: "barcode_height",
                                label: __("Barcode Height (px)"),
                                fieldtype: "Int",
                                default: 40,
                                reqd: 1,
                            },
                            {
                                fieldname: "barcode_width",
                                label: __("Narrow Bar Width (px)"),
                                fieldtype: "Int",
                                default: 2,
                                reqd: 1,
                            },
                        ],
                        primary_action(values) {
                            const qs = $.param({
                                doctype: "Item",
                                names: JSON.stringify(checked),
                                label_size: values.label_size,
                                copies: values.copies,
                                price_source: values.price_source,
                                barcode_type: values.barcode_type,
                                barcode_source: values.barcode_source,
                                barcode_height: values.barcode_height,
                                barcode_width: values.barcode_width,
                            });
                            const url = `/api/method/retail.utils.print.stickers?${qs}`;
                            dialog.hide();
                            window.open(url, "_blank");
                        },
                        primary_action_label: __("Print"),
                    });
                    dialog.show();
                });
            },
        }
    );
})();
