app_name = "retail"
app_title = "Retail"
app_publisher = "Projecx Team"
app_description = "Retail Customizations"
app_email = "support@projecx.io"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "retail",
# 		"logo": "/assets/retail/logo.png",
# 		"title": "Retail",
# 		"route": "/retail",
# 		"has_permission": "retail.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
    "retail.bundle.css",
]
app_include_js = [
    "retail.bundle.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/retail/css/retail.css"
# web_include_js = "/assets/retail/js/retail.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "retail/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
page_js = {
    "point-of-sale": "public/js/page/point_of_sale.js",
}

# include js in doctype views
doctype_js = {
    "POS Invoice" : "public/js/doctype/pos_invoice/pos_invoice.js",
    "POS Closing Entry" : "public/js/doctype/pos_closing_entry/pos_closing_entry.js",
    "Item" : "public/js/doctype/item/item.js",
    "Appointment" : "public/js/doctype/appointment/appointment.js",
    "Customer" : "public/js/doctype/customer/customer.js",
}
doctype_list_js = {
    "POS Invoice" : "public/js/doctype/pos_invoice/pos_invoice_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
doctype_calendar_js = {
    "Appointment" : "public/js/doctype/appointment/appointment_calendar.js",
}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "retail/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "retail.utils.jinja_methods",
# 	"filters": "retail.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "retail.install.before_install"
# after_install = "retail.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "retail.uninstall.before_uninstall"
# after_uninstall = "retail.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "retail.utils.before_app_install"
# after_app_install = "retail.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "retail.utils.before_app_uninstall"
# after_app_uninstall = "retail.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "retail.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"POS Invoice": "retail.overrides.doctype.pos_invoice.POSInvoice",
	"POS Closing Entry": "retail.overrides.doctype.pos_closing_entry.POSClosingEntry",
	"Sales Invoice": "retail.overrides.doctype.sales_invoice.SalesInvoice",
	"Appointment": "retail.overrides.doctype.appointment.Appointment",
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"retail.tasks.all"
# 	],
# 	"daily": [
# 		"retail.tasks.daily"
# 	],
# 	"hourly": [
# 		"retail.tasks.hourly"
# 	],
# 	"weekly": [
# 		"retail.tasks.weekly"
# 	],
# 	"monthly": [
# 		"retail.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "retail.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
    # "erpnext.accounts.doctype.pos_invoice.pos_invoice.get_stock_availability": "retail.overrides.whitelist.pos_invoice.get_stock_availability",
    # "retail.overrides.page.point_of_sale.point_of_sale.get_items": "retail.overrides.whitelist.pos_invoice.get_items",
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "retail.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["retail.utils.before_request"]
# after_request = ["retail.utils.after_request"]

# Job Events
# ----------
# before_job = ["retail.utils.before_job"]
# after_job = ["retail.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"retail.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
