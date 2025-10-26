console.log(frappe.utils.map_defaults.center)
console.log(frappe.utils.map_defaults.center)
console.log(frappe.utils.map_defaults.center)
console.log(frappe.utils.map_defaults.center)
console.log(frappe.utils.map_defaults.center)
console.log(frappe.utils.map_defaults.center)
Object.assign(frappe.utils, {
    map_defaults: {
		center: [25.2048, 55.2708],
		zoom: 12,
		tiles: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
		options: {
			attribution:
				'&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
		},
		image_path: "/assets/frappe/images/leaflet/",
	},
});