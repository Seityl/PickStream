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