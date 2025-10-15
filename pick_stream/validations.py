"""
Validation utilities for Pick Stream system.

Author: Jeriel Francis

Copyright (c) 2025, Jollys Pharmacy Limited and contributors
For license information, please see license.txt
"""


import frappe
from pick_stream import exceptions, utils


def validate_exists(
    doctype:str,
    id:str,
    child:bool = False,
    field:str = None
) -> None:
    """Raises an exception if document does not exist in the database"""
    if not child and not field:
        if not frappe.db.exists(doctype, id):
            raise exceptions.DoesNotExistError(
                f"{doctype} '{id}' does not exist."
            )
        return
    if not frappe.db.exists(doctype, {field:id}):
        raise exceptions.DoesNotExistError(
            f"{doctype} '{id}' does not exist."
        )


def validate_permission(user:str, workflow:str) -> None:
    """
    Raises an exception if user does not have permission for specified workflow.
    
    Available Workflows:
    
    - picking
    - transit
    - verification
    - receiving
    """
    allowed_permissions = {'picking', 'transit', 'verification', 'receiving'}
    if workflow not in allowed_permissions:
        raise exceptions.PermissionError(
            f"Invalid workflow permission: '{workflow}'. "
            f"Expected one of {', '.join(allowed_permissions)}."
        )
    access = utils.get_user_workflow_access(user)
    if not access.get(workflow, False):
        raise exceptions.PermissionError(
            f"User '{user}' does not have permission for '{workflow}' workflow."
        )
        
     
def validate_user_assigned_to_item_group(user:str, id:str) -> None:
    """Raises an exception if user is not assigned to item group"""
    validate_exists('Item Group', id)
    if not frappe.db.exists('User Group Member', {'user': user, 'parent':id}):
        raise exceptions.PermissionError(
            f"User '{user}' is not assigned to item group '{id}'. Contact Supervisor."
        )


def validate_user_assigned_to_mr(
    mr_name:str,
    user:str,
    allow_closed:bool=False
) -> None:
    """
    Raises an exception if user is not assigned to Material Request.

    Args:
        mr_name: Material Request name
        user: User email
        allow_closed: If True, allows users with Closed ToDos (recently completed)
    """
    if allow_closed:
        # Check if user has either Open or Closed ToDo for this MR
        # This allows users who just completed their work to still access the MR view
        has_todo = frappe.db.exists('ToDo', {
            'allocated_to': user,
            'reference_name': mr_name,
            'status': ['in', ['Open', 'Closed']]
        })
        if not has_todo:
            raise exceptions.PermissionError(
                f"User '{user}' is not assigned to Material Request '{mr_name}'. Contact Supervisor."
            )
    else:
        # Only allow Open ToDos
        if not frappe.db.exists('ToDo', {
            'allocated_to': user,
            'reference_name': mr_name,
            'status': 'Open'
        }):
            raise exceptions.PermissionError(
                f"User '{user}' is not assigned to Material Request '{mr_name}'. Contact Supervisor."
            )


def validate_scan_params(
    scanned_qty: int,
    crate_code: str,
    as_box: bool,
    as_other: bool,
    skipped: bool,
    crates: bool
) -> None:
    active_flags = sum(
        1 for flag in [
            as_box, as_other, skipped, crates, crate_code is not None
        ] if flag
    )
    if active_flags < 1:
        raise exceptions.SystemError(
            'Scan action must be selected. Contact IT.'
        )
    if active_flags > 1:
        raise exceptions.SystemError(
            'Only one scan action allowed. Contact IT.'
        )
    if not skipped and not crates and scanned_qty <= 0:
        raise exceptions.SystemError(
            'Scanned quantity must be greater than 0. Contact IT.'
        )
    if skipped:
        if scanned_qty > 0:
            raise exceptions.SystemError(
                'Cannot skip with quantity. Contact IT.'
            )
        if crate_code is not None:
            raise exceptions.SystemError(
                'Cannot skip with crate code. Contact IT.'
            )
    if crate_code is not None:
        if as_box:
            raise exceptions.SystemError(
                'Cannot scan both crate code and box. Contact IT.'
            )
        if as_other:
            raise exceptions.SystemError(
                'Cannot scan both crate code and other. Contact IT.'
            )
    if crates:
        if as_box or as_other:
            raise exceptions.SystemError(
                'Cannot scan crates with box/other. Contact IT.'
            )
        if crate_code:
            raise exceptions.SystemError(
                'Cannot scan crates and crate. Contact IT.'
            )
        if scanned_qty > 0:
            raise exceptions.SystemError(
                'Cannot scan crates with scanned quantity. Contact IT.'
            )
        
        
def validate_workflow_is_active(target_warehouse:str) -> None:
    active = frappe.db.get_value(
        'Pick Stream Workflow', 
        {
            'target_warehouse': target_warehouse
        },
        'is_active'
    )
    if not active:
        raise exceptions.ValidationError(
            f"{target_warehouse} workflow is not active. Contact Supervisor."
        )


def validate_role(user:str, role:str) -> None:
    """Raises an exception if user does not have a specific role"""
    if not frappe.db.exists('Has Role', {'parent': user, 'role': role}):
        raise exceptions.PermissionError(
            f"User '{user}' does not have role {role}. Contact Supervisor."
        )


def validate_printer_exists(printer:str) -> None:
    printers = utils.get_printers()
    if printer not in printers:
        raise exceptions.SystemError(
            f"Printer '{printer}' not found. Contact IT."
        )


def validate_item_type(item_type:str, settings:dict) -> None:
    item_types = [item.item_type for item in settings.item_types]
    if item_type not in item_types:
        raise exceptions.SystemError(
            f"Item type '{item_type}' not in valid item types. Contact IT."
        )