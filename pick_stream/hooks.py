from . import __version__ as app_version

app_name = "pick_stream"
app_title = "Pick Stream"
app_publisher = "Jollys Pharmacy Limited"
app_description = "A robust, efficient, and accurate inventory management module that simplifies the replenishment process, reduces errors, and enhances operational efficiency across stores."
app_email = "cdgrant@jollysonline.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/pick_stream/css/pick_stream.css"
# app_include_js = "/assets/pick_stream/js/pick_stream.js"

# include js, css files in header of web template
# web_include_css = "/assets/pick_stream/css/pick_stream.css"
# web_include_js = "/assets/pick_stream/js/pick_stream.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "pick_stream/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views

doctype_js = {"Material Request" : "public/js/custom_Material Request.js"}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "pick_stream/public/icons.svg"

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
# 	"methods": "pick_stream.utils.jinja_methods",
# 	"filters": "pick_stream.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "pick_stream.install.before_install"
# after_install = "pick_stream.install.after_install"

after_migrate = "pick_stream.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "pick_stream.uninstall.before_uninstall"
# after_uninstall = "pick_stream.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "pick_stream.utils.before_app_install"
# after_app_install = "pick_stream.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "pick_stream.utils.before_app_uninstall"
# after_app_uninstall = "pick_stream.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "pick_stream.notifications.get_notification_config"

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

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    'Material Request': {
        'on_submit': 'pick_stream.core.assign_users_to_mr'
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"pick_stream.tasks.all"
# 	],
# 	"daily": [
# 		"pick_stream.tasks.daily"
# 	],
# 	"hourly": [
# 		"pick_stream.tasks.hourly"
# 	],
# 	"weekly": [
# 		"pick_stream.tasks.weekly"
# 	],
# 	"monthly": [
# 		"pick_stream.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "pick_stream.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "pick_stream.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "pick_stream.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["pick_stream.utils.before_request"]
# after_request = ["pick_stream.utils.after_request"]

# Job Events
# ----------
# before_job = ["pick_stream.utils.before_job"]
# after_job = ["pick_stream.utils.after_job"]

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
# 	"pick_stream.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }