Object.assign(frappe.utils, {
    map_defaults: {
		center: [24.48, 54.45],
		zoom: 10,
		tiles: "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
		options: {
			attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
		},
		image_path: "/assets/frappe/images/leaflet/",
	},
});