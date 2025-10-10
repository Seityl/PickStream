import frappe
import pick_stream


def validate_exists(doctype:str, id:str, child:bool = False, field:str = None) -> None:
    """Raises an exception if document does not exist in the database"""
    if not child and not field:
        if not frappe.db.exists(doctype, id):
            raise pick_stream.exceptions.DoesNotExistError(f"{doctype} '{id}' does not exist.")
        return
    if not frappe.db.exists(doctype, {field:id}):
        raise pick_stream.exceptions.DoesNotExistError(f"{doctype} '{id}' does not exist.")


def validate_permission(user:str, workflow:str) -> None:
    """Raises an exception if user does not have permission for specified workflow"""
    allowed_permissions = {'picking', 'transit', 'verification', 'receiving'}
    if workflow not in allowed_permissions:
        raise pick_stream.exceptions.PermissionError(
            f"Invalid workflow permission: '{workflow}'. "
            f"Expected one of {', '.join(allowed_permissions)}."
        )
    access = pick_stream.utils.get_user_workflow_access(user)
    if not access.get(workflow, False):
        raise pick_stream.exceptions.PermissionError(
            f"User '{user}' does not have permission for '{workflow}' workflow."
        )
        
     
def validate_user_assigned_to_item_group(user:str, id:str) -> None:
    """Raises an exception if user is not assigned to item group"""
    validate_exists('Item Group', id)
    if not frappe.db.exists('User Group Member', {'user': user, 'parent':id}):
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not assigned to item group '{id}'. Contact Supervisor.")


def validate_user_assigned_to_mr(mr_name:str, user:str) -> None:
    """Raises an exception if user is not assigned to Material Request"""
    if not frappe.db.exists('ToDo', {
        'allocated_to': user,
        'reference_name': mr_name,
        'status': 'Open'
    }):
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not assigned to Material Request '{mr_name}'. Contact Supervisor.")

    
def validate_scan_params(scanned_qty: int, crate_code: str, as_box: bool, as_other: bool, skipped: bool, crates: bool) -> None:
    active_flags = sum(1 for flag in [as_box, as_other, skipped, crates, crate_code is not None] if flag)
    if active_flags < 1:
        raise pick_stream.exceptions.SystemError('Scan action must be selected. Contact IT.')
    if active_flags > 1:
        raise pick_stream.exceptions.SystemError('Only one scan action allowed. Contact IT.')
    if not skipped and not crates and scanned_qty <= 0:
        raise pick_stream.exceptions.SystemError('Scanned quantity must be greater than 0. Contact IT.')
    if skipped:
        if scanned_qty > 0:
            raise pick_stream.exceptions.SystemError('Cannot skip with quantity. Contact IT.')
        if crate_code is not None:
            raise pick_stream.exceptions.SystemError('Cannot skip with crate code. Contact IT.')
    if crate_code is not None:
        if as_box:
            raise pick_stream.exceptions.SystemError('Cannot scan both crate code and box. Contact IT.')
        if as_other:
            raise pick_stream.exceptions.SystemError('Cannot scan both crate code and other. Contact IT.')
    if crates:
        if as_box or as_other:
            raise pick_stream.exceptions.SystemError('Cannot scan crates with box/other. Contact IT.')
        if crate_code:
            raise pick_stream.exceptions.SystemError('Cannot scan crates and crate. Contact IT.')
        if scanned_qty > 0:
            raise pick_stream.exceptions.SystemError('Cannot scan crates with scanned quantity. Contact IT.')
        
        
def validate_workflow_is_active(target_warehouse:str) -> None:
    active = frappe.db.get_value('Pick Stream Workflow', {'target_warehouse': target_warehouse}, 'is_active')
    if not active:
        raise pick_stream.exceptions.ValidationError(f"{target_warehouse} workflow is not active. Contact Supervisor.")


def validate_role(user:str, role:str) -> None:
    """Raises an exception if user does not have a specific role"""
    if not frappe.db.exists('Has Role', {'parent': user, 'role': role}):
        raise pick_stream.exceptions.ValidationError(f"User '{user}' does not have role {role}. Contact Supervisor.")


def validate_printer_exists(printer:str) -> None:
    printers = get_printers()
    if printer not in printers:
        raise pick_stream.exceptions.ValidationError(f"Printer '{printer}' not found. Contact IT.")


def validate_item_type(item_type:str, settings:dict) -> None:
    item_types = [item.item_type for item in settings.item_types]
    if item_type not in item_types:
        raise pick_stream.exceptions.ValidationError(f"Item type '{item_type}' not in valid item types. Contact IT.")