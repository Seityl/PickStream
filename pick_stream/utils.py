"""
Utilities for Pick Stream system.

Author: Jeriel Francis

Copyright (c) 2025, Jollys Pharmacy Limited and contributors
For license information, please see license.txt
"""


import cups
import json
import html
import tempfile
from typing import List, Dict, Any, Optional, Union

import frappe
from frappe.utils import strip_html
from frappe.utils.nestedset import get_descendants_of

from pick_stream import validations, exceptions


def get_printers() -> List:
    """Returns list of printer names from CUPS server."""
    settings = get_settings()
    try:
        conn = cups.Connection(host=settings.host, port=settings.port)
        return list(conn.getPrinters().keys())
    except RuntimeError as e:
        raise exceptions.ValidationError(f'Error connecting to CUPS: {e}')
    except Exception as e:
        raise exceptions.ValidationError(f'Error connecting to CUPS: {e}')  


def process_print_request(
    printer:str,
    mr_name:str=None,
    item_code:str=None,
    item_type:str=None,
    user:str=None,
    qty:int=0, 
    item_identifier:str=None,
    crate_code:str=None
) -> dict:
    validations.validate_printer_exists(printer)
    settings = get_settings()
    if crate_code:
        validations.validate_exists('Crate', crate_code)
        if qty <= 0:
            qty = 1
        return print_crate_label(printer, settings, crate_code, qty)
    if item_identifier:
        validations.validate_exists('Pick Stream Identifier', item_identifier)
        identifier_doc = frappe.get_doc('Pick Stream Identifier', item_identifier)
        mr_name = identifier_doc.material_request
        item_code = identifier_doc.item_code
        item_type = identifier_doc.item_type
        user = frappe.session.user
        # User must explicitly give qty when identifier is provided
        if qty == 0:
            raise exceptions.SystemError('Cannot print 0 labels. Contact IT.')
    # Validate params when identifier is not provided
    else:
        if not mr_name:
            raise exceptions.SystemError('Material Request name is required. Contact IT.')
        if not item_code:
            raise exceptions.SystemError('Item Code is required. Contact IT.')
        if not item_type:
            raise exceptions.SystemError('Item Type is required. Contact IT.')
        if not item_type:
            raise exceptions.SystemError('User is required. Contact IT.')
    if qty < 0:
        raise exceptions.SystemError(f'Cannot print {qty} labels. Contact IT.')
    validations.validate_exists('Material Request', mr_name)
    validations.validate_exists('Item', item_code)
    validations.validate_item_type(item_type, settings)
    validations.validate_exists('User', user)
    # Default to default set from warehouse if not set on material request
    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')
    item_name = frappe.db.get_value('Item', item_code, 'item_name')
    print_job = print_item_identifier(
        user,
        mr_name,
        printer,
        from_warehouse,
        to_warehouse,
        item_code,
        item_type,
        settings,
        item_name,
        qty,
        item_identifier
    )
    return print_job


def print_crate_label(
    printer: str,
    settings: dict,
    crate_code: str,
    qty: int,
) -> str:
    zpl_template = (
        '^XA\n'
        # Define label width and length
        '^PW609^LH0,0^FS\n'
        # Crate Code text near top
        '^FO90,40^A0N,150,140^FD{crate_code}^FS\n'
        # Barcode of crate code centered horizontally
        '^FO110,180^BY4,3,100\n'
        '^BCN,210,N,N,N^FD{crate_code}^FS\n'
        '^XZ\n'
    )
    try:
        # Configure CUPS connection
        host, port = settings.get('host'), settings.get('port')
        cups.setServer(host)
        cups.setPort(port)
        conn = cups.Connection(host=host, port=port)
        # Write ZPL for all labels to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zpl') as tmp:
            for i in range(qty):
                tmp.write(zpl_template.format(crate_code=crate_code).encode('utf-8'))
            tmp.flush()
            tmp_path = tmp.name
        # Print options
        options = {
            'document-format': 'application/vnd.cups-raw',
            'media': 'Custom.3x2in',
            'scaling': '100',
            'fit-to-page': 'True'
        }
        job_name = f'Crate Label Print - {crate_code}'
        conn.printFile(printer, tmp_path, job_name, options)
        frappe.db.commit()
        return 'Print Job Submitted Successfully'
    except RuntimeError as e:
        frappe.db.rollback()
        raise exceptions.SystemError(f'CUPS connection error: {e}')
    except Exception as e:
        frappe.db.rollback()
        raise exceptions.SystemError(f'Printing failed: {e}')


def print_item_identifier(
    user:str,
    mr_name:str,
    printer:str,
    from_warehouse:str, 
    to_warehouse:str, 
    item_code: str=None, 
    item_type: str=None, 
    settings:dict=None,
    item_name:str=None,
    qty:int=0, 
    item_identifier:str=None
) -> dict:
    if not item_identifier:
        item_print_details = get_item_print_details(item_code, mr_name, from_warehouse, to_warehouse)
        if not item_print_details:
            raise exceptions.SystemError(f"Item '{item_code}' not found in source for material request '{mr_name}'.")
        item_identifier = item_print_details.identifier_code
        # Default to item qty if label qty not provided
        if qty == 0:
            qty = item_print_details.qty
    max_lines = 3
    max_width = 600
    # ZPL code template for each label
    zpl_code_template = (
        '^XA\n'
        # Item Code
        '^FO24,24^A0N,46,46^FDItem Code: {item_code} - {counter}/{qty}^FS\n'
        # Item Name block
        '^FO24,76\n'
        '^A0N,34,34\n'
        f'^FB{max_width},{max_lines},0,L,0\n'  # Adapts to item length
        f'^FD{item_name}^FS\n'
        # From Warehouse
        '^FO24,190^A0N,30,30^FDFrom: {from_warehouse}^FS\n'
        # To Warehouse
        '^FO24,224^A0N,30,30^FDTo:   {to_warehouse}^FS\n'
        # Barcode
        '^FO24,264\n'
        '^BY3.8,3.8,112\n'
        '^BCN,112,Y,N,N\n'
        f'^FD{item_identifier}^FS\n'
        '^XZ\n'
    )
    try:
        host, port = settings.host, settings.port
        cups.setServer(host)
        cups.setPort(port)
        conn = cups.Connection(host=host, port=port)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zpl') as tmp_file:
            # Write all labels, looping through the quantity
            for i in range(1, qty + 1):
                zpl_code = zpl_code_template.format(
                    item_code=item_code,
                    item_name=item_name,
                    from_warehouse=from_warehouse,
                    to_warehouse=to_warehouse,
                    item_identifier=item_identifier,
                    counter=i,
                    qty=qty
                )
                tmp_file.write(zpl_code.encode('utf-8'))
            tmp_file.flush()
            temp_file_path = tmp_file.name
        job_options = {
            'document-format': 'application/vnd.cups-raw',
            'media': 'Custom.3x2in',
            'scaling': '100',
            'fit-to-page': 'True'
        }
        job_name = f'{item_type} Identifier Print Job'
        conn.printFile(printer, temp_file_path, job_name, job_options)
        frappe.db.savepoint('print_item_identifier')
        # Update Item Identifier after successfully sending print job
        current_doc = frappe.get_doc('Pick Stream Identifier', item_identifier)
        current_printed = current_doc.printed or 0
        current_qty_printed = current_doc.qty_printed or 0
        current_date_printed = current_doc.dates_printed or ''
        new_entry = f'User: {user} - Date: {frappe.utils.now()} - Printer: {printer} - Qty: {qty}'
        updated_date_printed = f'{current_date_printed}<br>{new_entry}' if current_date_printed else new_entry
        frappe.db.set_value('Pick Stream Identifier', item_identifier, {
            'printed': current_printed + 1,
            'qty_printed': current_qty_printed + qty,
            'dates_printed': updated_date_printed
        })
        frappe.db.commit()
        return 'Print Job Submitted Successfully'
    except RuntimeError as e:
        frappe.db.rollback()
        raise exceptions.SystemError(f'Error connecting to CUPS: {e}')
    except Exception as e:
        frappe.db.rollback()
        raise exceptions.SystemError(f'Error connecting to CUPS: {e}')


def get_item_print_details(item_code: str, mr_name: str, from_warehouse: str, to_warehouse: str) -> Dict:
    item_group = frappe.db.get_value('Item', item_code, 'item_group')
    source_doc = frappe.get_doc(
        'Source',
        { 
            'item_group': item_group,
            'material_request': mr_name,
            'from_warehouse': from_warehouse,
            'to_warehouse': to_warehouse
        }
    )
    item = next(
        item for item in source_doc.item_crates if 
        item.item_code == item_code and 
        item.identifier_code != None
    )
    if not item:
        return None
    return frappe._dict({
        'identifier_code': item.identifier_code,
        'qty': item.qty if not item.verified_qty else item.verified_qty
    })


def get_settings() -> Dict:
    """Returns cached Pick Stream Settings document"""
    return frappe.get_cached_doc('Pick Stream Settings')


def get_user_branch(user:str) -> str:
    """Returns employee branch based on user"""
    if not frappe.db.exists('Employee', {'user_id': user}):
        raise exceptions.DoesNotExistError(f"Employee for user '{user}' does not exist. Contact HR.")
    branch = frappe.db.get_value('Employee', {'user_id': user}, ['branch'])
    if not branch:
        raise exceptions.ValidationError(f"Branch for user '{user}' is not set. Contact HR.")
    return branch


def get_warehouse_group(user:str, user_branch:str, settings:Dict=None) -> str:
    """Returns warehouse group defined in settings based on user's branch"""
    if not settings:
        settings = get_settings()
    if not settings.warehouse_group_map:
        raise exceptions.ValidationError(
            f'No warehouse group mappings configured. Contact IT.'
        )
    for mapping in settings.warehouse_group_map:
        if mapping.branch == user_branch:
            return mapping.warehouse
    raise exceptions.ValidationError(
        f"Employee branch '{user_branch}' for user '{user}' not mapped to a warehouse. Contact IT."
    )


def get_child_warehouses(parent_warehouse:str) -> List:
    """Get all descendant warehouses of specified parent"""
    return get_descendants_of('Warehouse', parent_warehouse)


def get_assigned_item_groups(user:str) -> List:
    """Get item groups assigned to a user through User Group relationships."""
    user_item_groups = frappe.db.sql_list("""
        SELECT DISTINCT ug.name
        FROM `tabUser Group` ug
        INNER JOIN `tabUser Group Member` ugm 
            ON ug.name = ugm.parent
        WHERE ugm.user = %(user)s
            AND ug.custom_is_item_group = 1
            AND ugm.parenttype = 'User Group'
    """, {'user': user})
    if not user_item_groups:
        raise exceptions.ValidationError(f"User '{user}' is not assigned to any item group. Contact Supervisor.")
    return user_item_groups


def get_mr_item_groups_for_user(mr_name:str, user:str, user_item_groups:List=[]) -> List:
    try:
        if not user_item_groups:
            user_item_groups = get_assigned_item_groups(user)
        mr_groups = frappe.db.sql_list("""
            SELECT DISTINCT mri.item_group
            FROM `tabMaterial Request Item` mri
            INNER JOIN `tabUser Group Member` ugm 
                ON ugm.parent = mri.item_group
            WHERE mri.parent = %(mr_name)s
                AND mri.item_group IN %(user_item_groups)s
                AND ugm.user = %(user)s
                AND ugm.parenttype = 'User Group'
        """, {
            'mr_name': mr_name,
            'user_item_groups': tuple(user_item_groups),
            'user': user
        })
        return mr_groups
    except Exception as e:
        raise exceptions.ValidationError(f'Error getting item groups for user: {e}') 
        
        
def get_mr_available_item_groups_for_user(
    mr_name:str,
    user:str,
    child_warehouses:List,
    user_item_groups:List = []
) -> List:
    """Returns item groups which are available or incomplete for material request"""
    out = []
    user_item_groups = get_mr_item_groups_for_user(mr_name, user, user_item_groups)
    for item_group in user_item_groups:
        # If completed Source (Pick List) exists, mark group unavailable
        if frappe.db.exists('Source', {
            'item_group': item_group, 
            'material_request': mr_name,
            'status': ['=', 'Completed']
        }):
            out.append(frappe._dict({'name': item_group, 'available': False, 'reason': 'Completed'}))
            continue
        # If no stock exists under warehouse group, mark group unavailable
        if not bool(frappe.db.sql(
            """
                SELECT 1
                FROM `tabMaterial Request Item` mri
                INNER JOIN `tabItem` item ON mri.item_code = item.name
                INNER JOIN `tabBin` bin ON mri.item_code = bin.item_code
                WHERE mri.parent = %(mr_name)s
                AND item.item_group = %(item_group)s
                AND bin.actual_qty >= 1
                AND bin.warehouse IN %(child_warehouses)s
                AND (mri.stock_qty > COALESCE(mri.ordered_qty, 0))
                LIMIT 1
            """,
            {
                'mr_name': mr_name,
                'item_group': item_group,
                'child_warehouses': tuple(child_warehouses)
            },
            as_dict=False
        )):
            out.append(frappe._dict({'name': item_group, 'available': False, 'reason': 'No Available Stock'}))
            continue
        # Mark group available if stock exists, and previous (if applicable) Source hasn't been completed
        out.append(frappe._dict({'name': item_group, 'available': True}))
    return out         


def get_source_name(mr_name:str, item_group:str) ->  Optional[str]:
    """
    Returns name of Source document tied to a specific Material Request and Item Group.

    Each Material Request can only have one Source per Item Group.  
    If no matching Source is found, the function returns None.
    """
    return frappe.db.get_value('Source', {
        'material_request': mr_name,
        'item_group': item_group
    }, 'name')


def get_relevant_source_item(source_name: str) -> Dict:
    """Returns the next unscanned and unskipped item with warehouse and quantity details."""
    out = frappe._dict()
    doc = frappe.get_doc('Source', source_name)
    try:
        item = next(item for item in doc.items if not item.scanned and not item.skipped)
        out.item_code = item.item_code
        out.description = html.unescape(strip_html(item.description)) if item.description else ''
        out.uom = item.uom
        out.from_warehouse = item.from_warehouse
        out.to_warehouse = doc.to_warehouse
        # For current item idx / total number of items
        out.idx = item.idx
        out.item_count = len(doc.items)
        duplicate_items = [i for i in doc.items if i.item_code == item.item_code]
        if len(duplicate_items) > 1:
            requested_qty = duplicate_items[0].requested_qty
            # Calculate already picked qty for this item_code
            already_scanned_qty = sum(i.scanned_qty or 0 for i in duplicate_items if i.scanned)
            # Calculate remaining qty needed
            remaining_qty_needed = requested_qty - already_scanned_qty
            # Use the minimum of available_qty and remaining_qty_needed to prevent over-picking
            out.requested_qty = min(item.available_qty, remaining_qty_needed)
        else:
            # No duplicates - use the minimum of requested_qty and available_qty
            out.requested_qty = min(item.requested_qty, item.available_qty)
    except StopIteration:
        # No items found matching the criteria
        pass
    return out


def create_source(mr_name:str, item_group:str, user:str) -> Dict:
    source = frappe.new_doc('Source')
    items = get_material_request_items_details(mr_name, user, item_group)
    settings = get_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse
    source.update({
        'material_request': mr_name,
        'from_warehouse': frappe.db.get_value(
                'Material Request', mr_name, 'set_from_warehouse'
            ) or 
            default_set_from_warehouse,
        'to_warehouse': frappe.db.get_value('Material Request', mr_name, 'set_warehouse'),
        'item_group': item_group,
        'user': user
    })
    for item in items:
        source.append('items', {
            'item_code': item.get('item_code'),
            'item_name': item.get('item_name'),
            'item_group': item.get('item_group'),
            'description': item.get('description'),
            'from_warehouse': item.get('from_warehouse'),
            'to_warehouse': item.get('to_warehouse'),
            'uom': item.get('uom'),
            'requested_qty': item.get('requested_qty'),
            'material_request': item.get('material_request'),
            'material_request_item': item.get('material_request_item')
        })
    frappe.db.savepoint('create_source')
    try:
        source.insert()
        frappe.db.commit()
        return source
    except Exception as e:
        frappe.db.rollback()
        raise exceptions.SystemError(str(e))


def get_material_request_item_group_item_quantity(
        mr_name: str,
        item_group: str,
        child_warehouses:str
    ) -> Dict:
    source_name = get_source_name(mr_name, item_group) 
    if not source_name:
        # Base off material request if source hasn't already been created
        out = frappe._dict({'completed': 0})
        out.total = frappe.db.sql(
            """
            SELECT 
                COUNT(DISTINCT mri.name) as total
            FROM `tabMaterial Request Item` mri
            INNER JOIN `tabBin` bin ON mri.item_code = bin.item_code 
                AND bin.warehouse IN %(child_warehouses)s
                AND bin.actual_qty >= 1
            WHERE mri.parent = %(mr_name)s
            AND mri.item_group = %(item_group)s
            """,
            {
                'mr_name': mr_name,
                'child_warehouses': tuple(child_warehouses),
                'item_group': item_group
            },
            as_dict=True
        )[0].total or 0
        return out
    else:
        # Base off source if available
        result = frappe.db.sql(
            """
            SELECT 
                SUM(CASE WHEN (si.scanned = 1 OR si.skipped = 1) THEN 1 ELSE 0 END) as completed,
                COUNT(*) as total
            FROM `tabSource Item` si
            WHERE 
                si.parent = %(source_name)s
                AND si.item_group = %(item_group)s
            """,
            {
                'source_name': source_name,
                'item_group': item_group
            },
            as_dict=True
        )[0]
        return frappe._dict({
            'completed': result.completed or 0,
            'total': result.total or 0,
        })


# TODO: Dont hardcode this
# 14/10/25
def get_workflow_target_warehouse(user:str, user_branch:str) -> str:
    """Return target warehouse based on user branch."""
    match user_branch:
        case 'King George':
            return 'KG Stock - JP'
        case 'JP Mega':
            return 'Mega Retail - JP'
        case 'JP Mini':
            return 'JPMini Stock - JP'
        case 'Great George':
            return 'GG Stock - JP'
        case 'Portsmouth':
            return 'JPPM Stock - JP'
        case _:
            raise exceptions.ValidationError(f"Employee for user '{user}' branch is not valid. Contact HR Department.")


def get_material_request_items_details(mr_name:str, user:str, selected_item_group:str) -> Dict:
    validations.validate_exists('User', user)
    validations.validate_exists('Material Request', mr_name)
    validations.validate_user_assigned_to_mr(mr_name, user)
    validations.validate_user_assigned_to_item_group(user, selected_item_group)
    return frappe.db.sql("""
        SELECT 
            mri.item_code,
            mri.item_name,
            mri.item_group,
            mri.description,
            mri.stock_uom AS uom,
            mri.stock_qty AS requested_qty,
            mri.name AS material_request_item,
            mr.name AS material_request,
            mr.set_from_warehouse AS from_warehouse,
            mr.set_warehouse AS to_warehouse
        FROM `tabMaterial Request Item` mri
        LEFT JOIN `tabMaterial Request` mr ON mri.parent = mr.name
        WHERE 
            mri.parent = %(mr_name)s
            AND mri.item_group = %(selected_item_group)s
    """, {
        'mr_name': mr_name,
        'selected_item_group': selected_item_group
    }, as_dict=True) or {}


def get_user_crate(user: str) -> Optional[str]:
    validations.validate_exists('User', user)
    all_crates = frappe.get_all(
        'Item Crates',
        fields=['crate_code', 'modified'],
        filters=[
            ['parenttype', '=', 'Source'], 
            ['crate_code', 'is', 'set'],
            ['picking_user', '=', user],
            ['crate_closed', '=', 0],
            ['transited', '=', 0],
            ['verified', '=', 0],
            ['received', '=', 0]
        ],
        order_by='modified desc'
    )
    # Get unique crate codes
    unique_crates = {}
    for crate in all_crates:
        crate_code = crate['crate_code']
        if crate_code not in unique_crates:
            unique_crates[crate_code] = crate
    matching_crates = list(unique_crates.values())
    # No active crates found
    if not matching_crates:
        return ''
    # Exactly one active crate - this is the expected normal state
    if len(matching_crates) == 1:
        return matching_crates[0]['crate_code']
    # Multiple active crates found - this is an error condition
    # List all the crates to help with debugging
    crate_codes = [c['crate_code'] for c in matching_crates]
    crate_list = ', '.join(crate_codes)
    raise exceptions.SystemError(
        f"User '{user}' has {len(matching_crates)} active open crates ({crate_list}). "
        f'Only one active crate is allowed at a time. Please close all but one crate before continuing. '
        f'Contact IT for assistance.'
    )


def check_item_against_barcode(item_code:str, barcode:str) -> bool:
    validations.validate_exists('Item', item_code)
    validations.validate_exists('Item Barcode', barcode, child=True, field='barcode')
    parent = frappe.db.get_value('Item Barcode', {'barcode': barcode}, 'parent')
    if parent != item_code:
        return False
    return True


def process_scan_as_crate(
        source:Dict,
        crate_code:str,
        item_code:str,
        user:str,
        scanned_qty:int,
        from_crates:bool=False
    ) -> str:
    if scanned_qty <= 0:
        raise exceptions.ValidationError(
            f'Scanned quantity must be greater than 0 in crate {crate_code}'
        )
    if from_crates:
        # Calculate pending quantities already in item_crates for this transaction
        # These quantities are not yet reflected in source_item.scanned_qty
        pending_qty_map = {}
        for crate in source.item_crates:
            if crate.item_code == item_code:
                pending_qty_map.setdefault(crate.source_item, 0)
                pending_qty_map[crate.source_item] += crate.qty
        # Find next available Source Item with remaining capacity
        # Account for BOTH scanned_qty and pending quantities
        item = next(
            (item for item in source.items 
             if item.item_code == item_code 
             and not item.skipped 
            # Add pending quantities to scanned_qty for accurate capacity check
            and ((item.scanned_qty or 0) + pending_qty_map.get(item.name, 0)) < item.requested_qty
            # Ensure this source_item isn't already in this specific crate
            and not any(
                    crate.crate_code == crate_code 
                    and crate.source_item == item.name 
                    for crate in source.item_crates
                )
            ),
            None
        )
    else:
        item = next(
            (item for item in source.items 
            if item.item_code == item_code 
            and not item.skipped 
            and not item.scanned),
            None
        )
    if not item:
        # Provide detailed error message for debugging
        available_items = [
            item for item in source.items 
            if item.item_code == item_code and not item.skipped
        ]
        if not available_items:
            raise exceptions.ValidationError(
                f'No source items found for {item_code}. Item may have been skipped or does not exist in this source.'
            )
        # Calculate total scanned/pending vs requested for better error message
        if from_crates:
            pending_qty_map = {}
            for crate in source.item_crates:
                if crate.item_code == item_code:
                    pending_qty_map.setdefault(crate.source_item, 0)
                    pending_qty_map[crate.source_item] += crate.qty
            total_pending = sum(pending_qty_map.values())
            total_scanned = sum((item.scanned_qty or 0) for item in available_items)
            total_requested = sum(item.requested_qty for item in available_items)
            total_in_crates = total_scanned + total_pending
            raise exceptions.ValidationError(
                f'Cannot scan {scanned_qty} more units of {item_code} into crate {crate_code}. '
                f'Total requested: {total_requested}, already in crates: {total_in_crates}. '
                f'Remaining units: {max(0, total_requested - total_in_crates)} units.'
            )
        else:
            raise exceptions.SystemError(
                f'Item {item_code} not found in source document. Contact IT.'
            )
    # Validate we're not exceeding capacity with this scan
    if from_crates:
        # Note: item.scanned_qty is already calculated from item_crates in validate_scanned_qty()
        # during the before_save hook, so it reflects all crates already added to this Source.
        # We just need to check if adding this new scan would exceed limits.
        total_after_scan = (item.scanned_qty or 0) + scanned_qty
        if total_after_scan > item.requested_qty:
            raise exceptions.ValidationError(
                f'Cannot scan {scanned_qty} units into crate {crate_code}. '
                f'This would exceed requested quantity of {item.requested_qty} '
                f'(current: {item.scanned_qty or 0}, attempting to add: {scanned_qty}).'
            )
        # Check against allocated quantity (available_qty) which was set during location allocation
        # This prevents over-scanning beyond what was allocated from this specific warehouse
        allocated_qty = item.available_qty if item.available_qty else item.requested_qty
        if total_after_scan > allocated_qty:
            # Check if this is a reasonable attempt given allocation constraints
            available_to_scan = max(0, allocated_qty - (item.scanned_qty or 0))
            if available_to_scan == 0:
                raise exceptions.ValidationError(
                    f'Cannot scan {scanned_qty} units into crate {crate_code}. '
                    f'No more stock allocated from warehouse {item.from_warehouse}. '
                    f'Allocated: {allocated_qty}, already scanned: {item.scanned_qty or 0}.'
                )
            else:
                raise exceptions.ValidationError(
                    f'Cannot scan {scanned_qty} units into crate {crate_code}. '
                    f'Only {available_to_scan} units allocated from warehouse {item.from_warehouse}. '
                    f'(Allocated: {allocated_qty}, already scanned: {item.scanned_qty or 0})'
                )
    existing_crate = next((
        crate for crate in source.item_crates
        if crate.item_code == item_code 
        and crate.crate_code == crate_code
        and crate.source_item == item.name
    ), None)
    if existing_crate:
        raise exceptions.SystemError(
            f'Crate {crate_code} already exists for item {item_code}. Contact IT.'
        )
    source.append('item_crates', {
        'picked_timestamp': frappe.utils.now(),
        'from_warehouse': item.from_warehouse,
        'source_item': item.name,
        'crate_code': crate_code,
        'item_code': item_code,
        'picking_user': user,
        'qty': scanned_qty
    })
    item.scanned = 1
    return f'Scanned {scanned_qty} {item.uom} for item {item_code} into crate {crate_code}'


def process_scan_as_crates(doc: Dict, crates:str, user:str, item_code:str) -> str:
    out = []
    for crate in crates:
        result = process_scan_as_crate(
            doc,
            crate.crate_code,
            item_code,
            user,
            crate.scanned_qty,
            from_crates=True
        )
        out.append(result)
    return  ' '.join(out)

    
def process_scan_as_box(source:Dict, identifier_code:str, item_code:str, scanned_qty:int, user:str) -> str:
    item = next(
        (item for item in source.items if item.item_code == item_code and not item.skipped and not item.scanned),
        None
    )
    if not item:
        raise exceptions.SystemError(
            f'Item {item_code} not found in source document. Contact IT.'
        )
    existing_identifier = next((
        identifier for identifier in source.item_crates
        if identifier.item_code == item_code and identifier.identifier_code == identifier_code
    ), None)
    if existing_identifier:
        raise exceptions.SystemError(
            f'Identifier {identifier_code} already exists for item {item_code}. Contact IT.'
        )
    source.append('item_crates', {
        'picked_timestamp': frappe.utils.now(),
        'from_warehouse': item.from_warehouse,
        'identifier_code': identifier_code,
        'source_item': item.name,
        'item_code': item_code,
        'picking_user': user,
        'qty': scanned_qty
    })
    item.scanned = 1
    item.is_box_item = 1
    return f'Scanned {scanned_qty} {item.uom} for item {item_code} assigned to identifier {identifier_code}'


def process_scan_as_other(source:Dict, identifier_code:str, item_code:str, scanned_qty:int, user:str) -> str:
    item = next(
        (item for item in source.items if item.item_code == item_code and not item.skipped and not item.scanned),
        None
    )
    if not item:
        raise exceptions.SystemError(
            f'Item {item_code} not found in source document. Contact IT.'
        )
    existing_identifier = next((
        identifier for identifier in source.item_crates
        if identifier.item_code == item_code and identifier.identifier_code == identifier_code
    ), None)
    if existing_identifier:
        raise exceptions.SystemError(
            f'Identifier {identifier_code} already exists for item {item_code}. Contact IT.'
        )
    source.append('item_crates', {
        'picked_timestamp': frappe.utils.now(),
        'from_warehouse': item.from_warehouse,
        'identifier_code': identifier_code,
        'source_item': item.name,
        'item_code': item_code,
        'picking_user': user,
        'qty': scanned_qty
    })
    item.scanned = 1
    item.is_other_item = 1
    return f'Scanned {scanned_qty} {item.uom} for item {item_code} assigned to identifier {identifier_code}'


def process_scan_as_skip(source:Dict, item_code:str) -> str:
    item = next(
        (item for item in source.items if item.item_code == item_code and not item.scanned and not item.skipped)
    )
    item.skipped = 1
    return f'Skipped item {item_code}'


def create_item_identifier(
    item_code:str,
    type:str,
    user:str,
    mr_name:str,
    from_warehouse:str,
    to_warehouse:str,
    qty:int,
    uom:str
) -> str:
    identifier = frappe.new_doc('Pick Stream Identifier')
    identifier.update({
        'date_created': frappe.utils.now(),
        'from_warehouse': from_warehouse,
        'to_warehouse': to_warehouse,
        'material_request': mr_name,
        'item_type': type.lower(),
        'item_code': item_code,
        'user': user,
        'qty': qty,
        'uom': uom
    })
    try:
        identifier.db_insert()
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        raise exceptions.SystemError(f'Error creating item identifier: {e}')
    return str(identifier.name)


def check_and_complete_mr_todo(mr_name: str, user: str) -> None:
    """
    Check if all Sources for a user's Material Request are completed.
    
    If all are completed, mark the user's ToDo as Closed.
    """
    user_item_groups = get_mr_item_groups_for_user(mr_name, user)
    if not user_item_groups:
        # No assigned item groups - nothing to check
        return
    # Check if all item groups have sources created
    existing_sources = frappe.db.get_all('Source', filters={
        'item_group': ['in', user_item_groups],
        'material_request': mr_name
    }, pluck='item_group')
    # If not all item groups have sources created, don't close the ToDo
    if set(existing_sources) != set(user_item_groups):
        return
    # Check if all item groups are completed
    incomplete_sources = frappe.db.count('Source', filters={
        'item_group': ['in', user_item_groups],
        'status': ['!=', 'Completed'],
        'material_request': mr_name
    })
    # If there are any incomplete sources, don't close the ToDo
    if incomplete_sources > 0:
        return
    # All sources are completed - close the ToDo for this user
    todo_name = frappe.db.get_value('ToDo', {
        'allocated_to': user,
        'reference_type': 'Material Request',
        'reference_name': mr_name,
        'status': 'Open'
    }, 'name')
    if todo_name:
        try:
            todo_doc = frappe.get_doc('ToDo', todo_name)
            todo_doc.status = 'Closed'
            todo_doc.add_comment('Comment', f'All pick lists completed for user {user}')
            todo_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(
                title=f'Failed to close ToDo {todo_name}',
                message=f'Error closing ToDo for user {user} on MR {mr_name}: {str(e)}'
            )


def get_crate_check_details(crate_code:str) -> dict:
    """Returns details of a crate for checking"""
    validations.validate_exists('Crate', crate_code)
    # Get crate basic details
    crate = frappe.get_doc('Crate', crate_code)
    items = frappe.db.get_all(
        'Source Item',
        filters={'parent': crate_code},
        fields=[
            'item_code',
            'item_name',
            'uom',
            'requested_qty',
            'scanned_qty',
            'item_group'
        ],
        order_by='idx asc'
    ) or []
    # Get streams associated with crate
    streams = frappe.db.get_all(
        'Streams',
        filters={'parent': crate_code, 'parenttype': 'Crate'},
        fields=['stream'],
        order_by='idx asc'
    ) or []
    # Get material request info from streams
    material_requests = []
    if streams:
        for stream in streams:
            mr = frappe.db.get_value('Stream', stream.stream, 'material_request')
            if mr and mr not in material_requests:
                material_requests.append(mr)
    return frappe._dict({
        'material_requests': material_requests,
        'from_warehouse': crate.from_warehouse,
        'to_warehouse': crate.to_warehouse,
        'total_items': len(items),
        'crate_code': crate_code,
        'status': crate.status,
        'color': crate.color,
        'items': items
    })


def get_user_crate_details(user:str, first_crate_code:str=None) -> Dict:
    if first_crate_code:
        validations.validate_exists('User', user)
        crate_code = first_crate_code
    else:
        crate_code = get_user_crate(user)
    if not crate_code:
        return frappe._dict()
    if first_crate_code:
        # Get Items from crate document explicitly if first crate code is passed
        items = frappe.db.get_all(
            'Source Item',
            filters=[
                ['parenttype', '=', 'Crate'], 
                ['parent', '=', crate_code], 
            ],
            fields=[
                'source as source_name',
                'scanned_qty as qty',
                'from_warehouse',
                'requested_qty',
                'item_code',
                'item_name',
                'name',
                'uom',
            ],
            order_by='idx asc'
        ) or []
    else:
        # Get Items from source documents otherwise
        items = frappe.db.get_all(
            'Item Crates',
            filters=[
                ['crate_code', '=', crate_code],
                ['parenttype', '=', 'Source'], 
                ['picking_user', '=', user],
                ['crate_closed', '=', 0],
                ['transited', '=', 0],
                ['verified', '=', 0],
                ['received', '=', 0]
            ],
            fields=['name', 'item_code', 'qty', 'source_item', 'parent as source_name', 'from_warehouse'],
            order_by='idx asc'
        ) or []
    for item in items:
        if not first_crate_code:
            if item.get('source_item'):
                item['requested_qty'] = frappe.db.get_value('Source Item', item['source_item'], 'requested_qty')
                item['item_name'] = frappe.db.get_value('Source Item', item['source_item'], 'item_name')
                item['uom'] = frappe.db.get_value('Source Item', item['source_item'], 'uom')
            else:
                item['requested_qty'] = None
    return frappe._dict({
        'crate_code': crate_code,
        'from_warehouse': frappe.db.get_value('Crate', crate_code, 'from_warehouse'),
        'to_warehouse': frappe.db.get_value('Crate', crate_code, 'to_warehouse'),
        'items': items
    })


def close_crate(crate_code:str, items:Any=None, commit:bool=False) -> None:
    if items is None:
        items = []
    open_crate_items = frappe.db.get_all(
        'Item Crates',
        filters={
            'crate_code': crate_code,
            'parenttype': 'Source',
            'crate_closed': 0
        },
        fields=['parent', 'item_code', 'from_warehouse']
    )
    if not open_crate_items:
        exceptions.SystemError(f"Crate '{crate_code}' is already closed. Contact IT.")
    # Create lookup for item quantities (by item_code only)
    items_lookup = {
        item.get('item_code'): item
        for item in items
    }
    # If specific items provided, validate they all exist in the crate
    if items:
        # Create lookup of what's actually in the crate (by item_code only)
        crate_items_set = {
            item.item_code
            for item in open_crate_items
        }
        # Check if all provided items exist in the crate
        provided_items_set = set(items_lookup.keys())
        unmatched_items = provided_items_set - crate_items_set
        if unmatched_items:
            raise exceptions.ValidationError(
                f"Cannot close crate '{crate_code}'. "
                f"The following items are not found in this crate: {', '.join(unmatched_items)}. "
                f'Crate contents may have changed since you last viewed it. Please refresh and try again.'
            )
        # Check if all items in the crate are being closed
        missing_items = crate_items_set - provided_items_set
        if missing_items:
            raise exceptions.ValidationError(
                f"Cannot close crate '{crate_code}'. "
                f"You must close all items in the crate. Missing: {', '.join(missing_items)}. "
                f'Crate contents may have changed since you last viewed it. Please refresh and try again.'
            )
    # Group items by source
    source_items = {}
    for item in open_crate_items:
        source_items.setdefault(item.parent, []).append(item)
    # Process each source
    for source_name, crate_items in source_items.items():
        source_doc = frappe.get_doc('Source', source_name)
        modified = False
        for item_crate in source_doc.item_crates:
            if item_crate.crate_code != crate_code:
                continue
            # If specific items provided, only process those items
            if items:
                item_data = items_lookup.get(item_crate.item_code)
                if item_data:
                    final_qty = item_data.get('final_qty')
                    if final_qty is not None and final_qty != item_crate.qty:
                        item_crate.qty = final_qty
                        modified = True
                    item_crate.crate_closed = 1
                    item_crate.crate_closed_timestamp = frappe.utils.now()
                    modified = True
            else:
                # No specific items provided, close all items in this crate
                item_crate.crate_closed = 1
                item_crate.crate_closed_timestamp = frappe.utils.now()
                modified = True
        if modified:
            source_doc.save()
    if commit:
        try:
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            exceptions.SystemError(f'Error closing crate: {e}')


def source_is_complete(source_doc: Dict) -> bool:
    completed =  frappe.db.get_value('Source', source_doc.name, 'status') == 'Completed'
    if not completed:
        return not any(not item.scanned and not item.skipped for item in source_doc.items)
    return completed


def verify_first_crate(crate_code:str, items:Any=None, commit:bool=False) -> dict:
    """Verify quantities for the first crate in multi-crate picking scenario"""
    if items is None:
        items = []
    if isinstance(items, str):
        items = json.loads(items)
    items = [frappe._dict(item) for item in items]
    sources = set(item.source_name for item in items if item.source_name)
    # Get all items in the crate
    crate_items = frappe.db.get_all(
        'Item Crates',
        filters={
            'parent': ['in', sources],
            'crate_code': crate_code,
            'parenttype': 'Source',
            'crate_closed': 1
        },
        fields=['parent', 'item_code', 'qty', 'name', 'from_warehouse']
    )
    if not crate_items:
        raise exceptions.SystemError(
            f"Crate '{crate_code}' has no items. Contact IT."
        )
    # Create composite key for unique item identification
    def make_item_key(item_code, from_warehouse, source):
        """Create a composite key from item_code, from_warehouse, and source"""
        return f"{item_code}||{from_warehouse or ''}||{source or ''}"
    # Create lookup for verified quantities by composite key
    # This handles cases where the same item appears multiple times from different sources/warehouses
    items_lookup = {}
    for item in items:
        if item.item_code and item.source_name:
            key = make_item_key(
                item.item_code,
                item.from_warehouse,
                item.source_name
            )
            items_lookup[key] = item
    # Create lookup for crate items by composite key
    crate_items_lookup = {}
    for crate_item in crate_items:
        key = make_item_key(
            crate_item.item_code,
            crate_item.from_warehouse,
            crate_item.parent
        )
        crate_items_lookup[key] = crate_item
    # Validate all items are accounted for
    closed_items_set = set(crate_items_lookup.keys())
    provided_items_set = set(items_lookup.keys())
    if closed_items_set != provided_items_set:
        # Create readable error messages
        def format_keys(keys):
            return [f"({k.replace('||', ', ')})" for k in sorted(keys)]
        frappe.log_error(
            title=f'Item mismatch verifying crate {crate_code}',
            message=(
                f"Crate '{crate_code}' item mismatch. "
                f'Items in crate: {", ".join(format_keys(closed_items_set))}. '
                f'Items provided: {", ".join(format_keys(provided_items_set))}.'
            )
        )
        raise exceptions.ValidationError(
            f"Item mismatch for crate '{crate_code}'. Please refresh and try again."
        )
    # Group items by source
    source_items = {}
    for item in crate_items:
        source_items.setdefault(item.parent, []).append(item)
    frappe.db.savepoint('verify_first_crate')
    try:
        # Process each source
        for source_name, source_crate_items in source_items.items():
            source_doc = frappe.get_doc('Source', source_name)
            modified = False
            for item_crate in source_doc.item_crates:
                if item_crate.crate_code != crate_code or not item_crate.crate_closed:
                    continue
                # Create composite key for this item_crate
                key = make_item_key(
                    item_crate.item_code,
                    item_crate.from_warehouse,
                    source_name
                )
                # Look up the verified item data using composite key
                item_data = items_lookup.get(key)
                if item_data:
                    frappe.log_error('Verifying item', f'Crate: {crate_code}, Item: {item_crate.item_code}, Key: {key}, Data: {item_data}')
                    final_qty = item_data.get('final_qty')
                    if final_qty is not None and final_qty != item_crate.qty:
                        item_crate.qty = final_qty
                        modified = True
            if modified:
                source_doc.save()
        if commit:
            frappe.db.commit()
        return {'success': True, 'crate_code': crate_code}
    except Exception as e:
        frappe.db.rollback()
        raise exceptions.ValidationError(f'Error verifying crate: {e}')


def get_identifier_list(user, limit):
    return frappe.get_all(
        'Pick Stream Identifier',
        filters={'user': user},
        fields=[
            'from_warehouse',
            'to_warehouse',
            'item_code',
            'item_type',
            'user',
            'name'
        ],
        limit=limit,
        order_by='modified desc'
    )


def get_identifier_details(item_identifier: str) -> Dict:
    if not frappe.db.exists('Pick Stream Identifier', item_identifier):
        raise exceptions.SystemError(f'Item Identifier {item_identifier} not found. Contact IT.')
    doc = frappe.get_doc('Pick Stream Identifier', item_identifier)
    return frappe._dict({
        'material_request': doc.material_request,
        'from_warehouse': doc.from_warehouse,
        'dates_printed': doc.dates_printed,
        'date_created': doc.date_created,
        'to_warehouse': doc.to_warehouse,
        'qty_printed': doc.qty_printed,
        'item_code': doc.item_code,
        'item_type': doc.item_type,
        'printed': doc.printed,
        'user': doc.user,
        'uom': doc.uom,
        'qty': doc.qty
    })
    

def get_crate_details_(
    user:str,
    crate_code:str,
    to_verify:bool=False,
    to_transit:bool=False,
    to_receive:bool=False
) -> dict:
    validations.validate_exists('User', user)
    validations.validate_exists('Crate', crate_code)
    to_warehouse = frappe.db.get_value('Crate', crate_code, 'to_warehouse')
    settings = get_settings()
    workflow_details = get_workflow_details(to_warehouse, settings)
    if not has_role(user, settings.privileged_user_role):
        if to_verify:
            validations.validate_permission(user, 'verification')
            user_branch = get_user_branch(user)
            if user_branch not in workflow_details.verification_branches:
                raise exceptions.PermissionError(
                    f"User '{user}' is not authorized to verify from '{user_branch}'. Contact Supervisor."
                )
        if to_transit:
            validations.validate_permission(user, 'transit')
        if to_receive:
            validations.validate_permission(user, 'receiving')
    return frappe._dict({
        'crate_code': crate_code,
        'from_warehouse': frappe.db.get_value('Crate', crate_code, 'from_warehouse'),
        'to_warehouse': to_warehouse,
        'items': frappe.db.get_all(
            'Source Item',
                filters={'parent': crate_code},
                fields=['item_code', 'item_name', 'uom', 'scanned_qty as qty'],
                order_by='idx asc'
            ) or []
    })


def get_workflow_details(target_warehouse:str=None, picking_warehouse:str=None, settings:Dict=None):
    """
    Returns workflow configuration details as defined in the Pick Stream Settings.
    
    Multiple workflows can exist for the same target_warehouse with different
    picking_warehouse sources. Provide both parameters when you need a specific
    workflow path.

    Args:
        target_warehouse: If provided, filters workflows by this destination warehouse
        picking_warehouse: If provided, filters workflows by this source warehouse
        settings: Pick Stream Settings document (fetched if not provided)
    """    
    if settings is None:
        settings = frappe.get_single('Pick Stream Settings')
    
    active_workflows = [row for row in settings.workflow_settings if row.is_active]
    if not active_workflows:
        raise exceptions.SystemError(
            'No active workflows found. Contact IT.'
        )
    # Filter by target_warehouse if provided
    if target_warehouse:
        validations.validate_exists('Warehouse', target_warehouse)
        matching_workflows = [
            row for row in active_workflows 
            if row.target_warehouse == target_warehouse
        ]
        if not matching_workflows:
            raise exceptions.ValidationError(
                f'No active workflow found for target warehouse {target_warehouse}. Contact IT.'
            )
        workflows = matching_workflows
    else:
        workflows = active_workflows
    # Filter by picking_warehouse if provided
    if picking_warehouse:
        validations.validate_exists('Warehouse', picking_warehouse)
        matching_workflows = [
            row for row in workflows 
            if row.picking_warehouse == picking_warehouse
        ]
        if not matching_workflows:
            if target_warehouse:
                raise exceptions.ValidationError(
                    f'No active workflow found from {picking_warehouse} to {target_warehouse}. Contact IT.'
                )
            else:
                raise exceptions.ValidationError(
                    f'No active workflow found for picking warehouse {picking_warehouse}. Contact IT.'
                )
        workflows = matching_workflows
    # Build result
    result = []
    for row in workflows:
        result.append(frappe._dict({
            'target_warehouse': row.target_warehouse,
            'picking_warehouse': row.picking_warehouse,
            'picking_user_branch': row.picking_user_branch,
            'verification_branch': row.verification_branch,
            'verification_after_receiving': row.verification_after_receiving,
            'transit_after_verification': row.transit_after_verification,
            'transit_warehouse': row.transit_warehouse,
            'receiving_after_verification': row.receiving_after_verification,
            'send_notifications': row.send_notifications
        }))
    # Return single workflow if both warehouses specified, otherwise return list
    if target_warehouse and picking_warehouse:
        return result[0]  # Should only be one exact match
    else:
        return result


def has_role(user:str, role:str) -> bool:
    """Return True if user has the specified role, False otherwise."""
    if frappe.db.exists('Has Role', {'parent': user, 'role': role}):
        return True
    return False
    

def get_user_workflow_access(user):
    """Returns workflow access of the specified user."""
    validations.validate_exists('User', user)
    settings = get_settings()
    if has_role(user, settings.privileged_user_role):
        return {
            'verification': True,
            'receiving': True,
            'picking': True,
            'transit': True
        }
    return {
        'verification': has_role(user, settings.verification_user_role),
        'receiving': has_role(user, settings.receiving_user_role),
        'picking': has_role(user, settings.picking_user_role),
        'transit': has_role(user, settings.transit_user_role)
    }
    

def get_user_profile(user):
    validations.validate_exists('User', user)
    user_doc = frappe.get_doc('User', user)

    employee_doc = None
    if frappe.db.exists('Employee', {'user_id': user}):
        employee_doc = frappe.get_doc('Employee', {'user_id': user})
    
    profile_data = {
        'name': user_doc.name,
        'email': user_doc.email,
        'user_image': user_doc.user_image
    }
    
    if employee_doc:
        profile_data.update({
            'full_name': employee_doc.employee_name or user_doc.full_name or user_doc.first_name,
            'designation': employee_doc.designation,
            'department': employee_doc.department,
            'company': employee_doc.company,
            'employee': employee_doc.name,
            'branch': employee_doc.branch,
            'phone': employee_doc.cell_number or user_doc.phone
        })

    else:
        profile_data.update({
            'full_name': user_doc.full_name or user_doc.first_name,
            'phone': user_doc.phone,
        })
    
    return profile_data

def get_user_notifications(user):
    validations.validate_exists('User', user)
    notifications = []
    
    def clean_text(text, max_length=200):
        if not text:
            return ''
        
        cleaned = frappe.utils.strip_html_tags(text)
        cleaned = " ".join(cleaned.split())
        
        if len(cleaned) > max_length:
            return cleaned[:max_length].rsplit(' ', 1)[0] + "..."
        
        return cleaned
    
    notification_logs = frappe.get_all(
        'Notification Log',
        filters={
            'for_user': user,
            'read': ['in', [0, 1]]  # Get both read and unread
        },
        fields=[
            'name', 'subject', 'email_content', 'document_type', 
            'document_name', 'from_user', 'creation', 'read'
        ],
        order_by='creation desc',
        limit=50
    )
    
    for log in notification_logs:
        notifications.append({
            'id': log.name,
            'title': clean_text(log.subject or 'Notification', 100),
            'message': clean_text(log.email_content),
            'document_type': log.document_type,
            'document_name': log.document_name,
            'from_user': log.from_user,
            'creation': log.creation,
            'read': bool(log.read),
            'type': 'notification_log'
        })
    
    # Get Assignment notifications
    assignments = frappe.get_all(
        'ToDo',
        filters={
            'allocated_to': user,
            'status': ['in', ['Open', 'Closed']]
        },
        fields=[
            'name', 'description', 'reference_type', 'reference_name', 
            'assigned_by', 'creation', 'status'
        ],
        order_by='creation desc',
        limit=20
    )
    
    for assignment in assignments:
        notifications.append({
            'id': f'todo_{assignment.name}',
            'title': clean_text(f"Task Assigned: {assignment.reference_type or 'General Task'}", 100),
            'message': clean_text(assignment.description or 'You have been assigned a new task'),
            'document_type': assignment.reference_type,
            'document_name': assignment.reference_name,
            'from_user': assignment.assigned_by,
            'creation': assignment.creation,
            'read': assignment.status == 'Closed',
            'type': 'assignment'
        })
    
    notifications.sort(key=lambda x: x.get('creation', ''), reverse=True)
    
    return notifications[:100]

def parse_codes(codes: Any) -> List[str]:
    if isinstance(codes, str):
        try:
            parsed_codes = json.loads(codes)
            if isinstance(parsed_codes, list):
                return [str(code) for code in parsed_codes]
            else:
                return [str(parsed_codes)]
        except (json.JSONDecodeError, TypeError):
            return [str(codes)]
    
    elif isinstance(codes, list):
        return [str(code) for code in codes]
    
    else:
        return [str(codes)]

def check_transit_required(picking_warehouse_stores, from_warehouse, to_warehouse) -> bool:
    """Returns true if specified store doesn't match store mapped to picking location"""
    source_warehouse_store = picking_warehouse_stores.get(from_warehouse)
    if source_warehouse_store is None:
        return True
    return source_warehouse_store != to_warehouse


def check_crate_availability(crate_code: str, user: str, from_stream: bool = False) -> bool:
    """Check if a crate is available for use by a specific user"""
    validations.validate_exists('Crate', crate_code)
    if not from_stream: 
        validations.validate_exists('User', user)
    crate_status = frappe.db.get_value('Crate', crate_code, 'status')
    # Crate is available - anyone can use it
    if crate_status == 'Available':
        return True
    # Crate is being picked - check if it's this user or another user
    if crate_status == 'Picking':
        crate_picking_user = get_crate_picking_user(crate_code)
        # If no picking user found but status is Picking, it's a data integrity issue
        # but we should just return False rather than break the flow
        if not crate_picking_user:
            frappe.log_error(
                title=f'Crate Status Inconsistency: {crate_code}',
                message=f"Crate '{crate_code}' has status 'Picking' but no active picking user found in Item Crates."
            )
            return False
        # Crate is being picked by another user - deny access with clear error
        if crate_picking_user != user:
            raise exceptions.ValidationError(
                f"Crate '{crate_code}' is already in use by {crate_picking_user}. "
                'Contact IT if you believe this is an error.'
            )
        # Crate is being picked by the same user - allow access
        return True
    # For all other statuses (Waiting, In Transit, Completed, etc.), crate is not available
    # This includes closed crates, transited crates, etc.
    return False
    

def get_crate_picking_user(crate_code):
    """
    Get the current picking user for a crate by querying the Item Crates child table.
    
    This function finds the active picking user by looking for open (unclosed, 
    unverified, unreceived) items in the Item Crates table associated with the crate.
    
    Business Logic:
    - Only considers items that haven't been closed, transited, verified, or received
    - If multiple users are found (data integrity issue), returns the most recent
    - If multiple users found, automatically closes the crate to prevent further issues
    """
    all_picking_users = frappe.get_all(
        'Item Crates',
        fields=['picking_user', 'crate_code', 'modified'],
        filters=[
            ['crate_code', '=', crate_code],
            ['parenttype', '=', 'Source'],
            ['picking_user', 'is', 'set'],
            ['crate_closed', '=', 0],   # Not closed
            ['transited', '=', 0],      # Not transited
            ['verified', '=', 0],       # Not verified
            ['received', '=', 0]        # Not received
        ]
    )
    # No active items found - crate has no picking user
    if not all_picking_users:
        return None
    # Deduplicate by (crate_code, picking_user) and keep most recent
    user_dict = {}
    for record in all_picking_users:
        key = (record['crate_code'], record['picking_user'])
        if key not in user_dict or record['modified'] > user_dict[key]['modified']:
            user_dict[key] = record
    unique_records = list(user_dict.values())
    # Data integrity issue: Multiple users have open items in the same crate
    # This should NEVER happen - close the crate to prevent further issues
    if len(unique_records) > 1:
        frappe.log_error(
            title=f'Multiple Picking Users Found for Crate {crate_code}',
            message=f'Found {len(unique_records)} picking users for crate {crate_code}: '
                   f"{[r['picking_user'] for r in unique_records]}. Auto-closing crate."
        )
        try:
            core.close_crate(crate_code, commit=True)
        except Exception as e:
            # Log but don't fail if close_crate fails - we still want to return a user
            frappe.log_error(
                title=f"Failed to Auto-Close Crate {crate_code}",
                message=f"Error while auto-closing crate with multiple users: {str(e)}"
            )
    # Return the most recent picking user
    most_recent_record = max(unique_records, key=lambda x: x['modified'])
    return most_recent_record['picking_user']

# def check_material_request_item_group_in_progress(mr_name:str, item_group:str) -> dict:
#     source_name = get_source_name(mr_name, item_group)
#     if source_name:
#         if frappe.db.get_value('Source', source_name, 'status') != 'Completed':
#             return frappe._dict({'in_progress': True, 'source': source_name})
#     return frappe._dict({'in_progress': False, 'source': source_name})
