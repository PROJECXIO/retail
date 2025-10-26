Object.assign(frappe.utils, {
    map_defaults: {
		center: [24.28, 54.22],
		zoom: 11,
		tiles: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
		options: {
			attribution:
				'&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
		},
		image_path: "/assets/frappe/images/leaflet/",
	},
});