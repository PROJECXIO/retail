frappe.listview_settings["Customer"] = {
    onload: function (listview) {
        // Use defaults, or override filterField/api if needed
        window.retailAwesomebarListViewSearch(listview, {
            filterField: "name",
            api: "retail.utils.awesomebar.find_closest_customers",
            storageKeyPrefix: "retail_subseq_last_q_",
        });
    },
};
