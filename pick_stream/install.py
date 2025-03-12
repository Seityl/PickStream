import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

@frappe.whitelist()
def after_install():
    pass

def custom_field_user_group():
    create_custom_field(
        'User Group', {
            "label": _("Is Item Group"),
            "fieldname": "is_item_group",
            "fieldtype": "Check",
            "insert_after": "user_group_members"
        }
    )

def custom_field_assign_warehouse_staff():
    create_custom_field(
        'User Group', {
            "label": _("Assign Warehouse Staff"),
            "fieldname": "assign_warehouse_staff",
            "fieldtype": "Check",
            "insert_after": "schedule_date"

        }
    )