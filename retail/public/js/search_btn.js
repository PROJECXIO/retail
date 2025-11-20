window.retailAwesomebarListViewSearch = function (listview, opts) {
  opts = opts || {};
  const DOCTYPE = listview.doctype;
  const STORAGE_KEY =
    (opts.storageKeyPrefix || "retail_subseq_last_q_") + DOCTYPE;
  const FILTER_FIELD = opts.filterField || "item_code";
  const API = opts.api || "retail.utils.awesomebar.find_closest_items";
  let reqSeq = 0;

  function debounce(fn, ms) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function bindOnce(target, event, namespace, handler) {
    $(target)
      .off(event + "." + namespace)
      .on(event + "." + namespace, handler);
  }

  if (!document.getElementById("retail-subseq-styles")) {
    $("head").append(`
            <style id="retail-subseq-styles">
            .retail-subseq-wrap {
                position: relative;
                margin-left: 8px;
                display: inline-block;
                margin: var(--margin-xs) 0 var(--margin-xs) var(--margin-xs);
            }
            .retail-subseq-clear-btn {
                position: absolute;
                right: 6px;
                top: 50%;
                transform: translateY(-50%);
                border: 0;
                background: transparent;
                padding: 0;
                line-height: 1;
                cursor: pointer;
                display: none;
            }
            </style>
        `);
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

  function get_other_filters(listview) {
    try {
      const fa = listview.filter_area;
      const curr = fa.get() || [];
      return curr.filter(
        (f) => !(Array.isArray(f) && f[0] === DOCTYPE && f[1] === FILTER_FIELD)
      );
    } catch (e) {
      console.warn("Failed to get filters", e);
      return [];
    }
  }

  function reset_filters_with_field(
    listview,
    otherFilters,
    fieldVals,
    useNotSet = false
  ) {
    const fa = listview.filter_area;
    try {
      if (fa && typeof fa.clear === "function") {
        fa.clear();
      } else if (
        fa &&
        typeof fa.get === "function" &&
        typeof fa.remove === "function"
      ) {
        const curr = fa.get() || [];
        curr.forEach((f) => {
          try {
            fa.remove([f]);
          } catch (e) {
            console.warn("Filter remove failed", f, e);
          }
        });
      }
      if (otherFilters && otherFilters.length && typeof fa.add === "function")
        fa.add(otherFilters);
      if (useNotSet && typeof fa.add === "function") {
        fa.add([[DOCTYPE, FILTER_FIELD, "is", "not set"]]);
      } else if (
        fieldVals &&
        fieldVals.length &&
        typeof fa.add === "function"
      ) {
        fa.add([[DOCTYPE, FILTER_FIELD, "in", fieldVals]]);
      }
      listview.refresh();
    } catch (e) {
      console.warn("Filter rebuild failed", e);
      listview.refresh();
    }
  }

  function run_subsequence_search(listview, query, limit) {
    const q = (query || "").trim();
    const mySeq = ++reqSeq;
    const others = get_other_filters(listview);

    if (!q) {
      reset_filters_with_field(listview, others, []);
      return;
    }

    return frappe
      .call({
        method: API,
        args: { q, limit },
      })
      .then((r) => {
        if (mySeq !== reqSeq) return;
        const ids = r.message || [];
        if (!ids.length) {
          reset_filters_with_field(listview, others, [], true);
        } else {
          reset_filters_with_field(listview, others, ids, false);
        }
      })
      .catch((err) => {
        console.warn("Subsequence search failed", err);
      });
  }

  // Input with inline clear button using CSS classes
  const $wrap = $(`
      <div class="retail-subseq-wrap">
        <input type="text"
               class="form-control input-sm retail-subseq-input"
               placeholder="${__("Search...")} ">
        <button type="button" aria-label="${__("Clear")}"
                class="retail-subseq-clear-btn">×</button>
      </div>
    `);
  mount_in_page_form(listview, $wrap);

  const $input = $wrap.find(".retail-subseq-input");
  const $clear = $wrap.find(".retail-subseq-clear-btn");

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
      run_subsequence_search(listview, last, listview.page_length);
    }
  } catch (e) {
    console.warn("LocalStorage get failed", e);
  }

  const debouncedApply = debounce(function () {
    const val = $input.val() || "";
    try {
      localStorage.setItem(STORAGE_KEY, val.trim());
    } catch (e) {
      console.warn("LocalStorage set failed", e);
    }
    run_subsequence_search(listview, val, listview.page_length);
  }, 250);

  $input.on("input", function () {
    toggleClear();
    const val = ($input.val() || "").trim();
    if (!val) {
      reqSeq++;
      const others = get_other_filters(listview);
      reset_filters_with_field(listview, others, []);
      try {
        localStorage.setItem(STORAGE_KEY, "");
      } catch (e) {}
      return;
    }
    debouncedApply();
  });

  $input.on("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      try {
        localStorage.setItem(STORAGE_KEY, ($input.val() || "").trim());
      } catch (e) {}
      run_subsequence_search(listview, $input.val(), listview.page_length);
    }
  });

  $clear.on("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    $input.val("");
    toggleClear();
    try {
      localStorage.setItem(STORAGE_KEY, "");
    } catch (e) {}
    reqSeq++;
    const others = get_other_filters(listview);
    reset_filters_with_field(listview, others, []);
    $input.focus();
  });

  // Clear input value when .filter-x-button is clicked (user closes any filter)
  const $header = listview.$page ? listview.$page : $(listview.page.wrapper);
  bindOnce($header, "click", "retail_subseq_filter_x", function (e) {
    if ($(e.target).closest(".filter-x-button").length) {
      $input.val("");
      toggleClear();
      try {
        localStorage.setItem(STORAGE_KEY, "");
      } catch (e) {}
    }
  });

  bindOnce(document, "keydown", "retail_subseq", function (e) {
    if (e.ctrlKey && (e.key === "g" || e.key === "G")) {
      e.preventDefault();
      $input.focus().select();
    }
    if (e.ctrlKey && e.key === "Backspace") {
      e.preventDefault();
      $clear.click();
    }
  });
};
