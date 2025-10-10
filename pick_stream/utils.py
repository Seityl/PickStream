import cups
import json
import html
from typing import List, Dict, Any, Optional

import frappe
from frappe.utils import strip_html
from frappe.utils.nestedset import get_descendants_of

from pick_stream import validations, exceptions

def get_printers() -> dict:
    settings = get_settings()
    try:
        conn = cups.Connection(host=settings.host, port=settings.port)
        return list(conn.getPrinters().keys())
    except RuntimeError as e:
        raise exceptions.ValidationError(f'Error connecting to CUPS: {e}')
    except Exception as e:
        raise exceptions.ValidationError(f'Error connecting to CUPS: {e}')  


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
    # Get all item groups assigned to this user for this MR
    user_item_groups = get_mr_item_groups_for_user(mr_name, user)
    if not user_item_groups:
        # No Sources exist for this user and MR yet
        return
    # Check if all Sources for this user's item groups are completed
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


def get_user_crate_details(user:str) -> Dict:
    validations.validate_exists('User', user)
    crate_code = get_user_crate(user)
    if not crate_code:
        return frappe._dict()
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
        fields=['item_code', 'qty', 'source_item'],
        order_by='idx asc'
    ) or []
    for item in items:
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


def close_crate(crate_code:str, items:Any=[], commit:bool=False) -> None:
    open_crate_items = frappe.db.get_all('Item Crates',
        filters={
            'crate_code': crate_code,
            'parenttype': 'Source',
            'crate_closed': '0'
        },
        fields=['parent']
    )
    if not open_crate_items:
        raise exceptions.SystemError(f"Crate '{crate_code}' is already closed. Contact IT.")
    items_lookup = {}
    for item in items:
        items_lookup[item.get('item_code')] = item
    source_names = set([item.parent for item in open_crate_items])
    for source_name in source_names:
        source_doc = frappe.get_doc('Source', source_name)
        for item_crate in source_doc.item_crates:
            if item_crate.crate_code == crate_code:
                # TODO: Account for same item in same crate from multiple locations
                if item_crate.item_code in items_lookup:
                    item_data = items_lookup[item_crate.item_code]
                    final_qty = item_data.get('final_qty')
                    current_qty = item_crate.qty
                    
                    # Update quantity if there's a discrepancy
                    if final_qty is not None and final_qty != current_qty:
                        item_crate.qty = final_qty
                        
                item_crate.crate_closed = 1
                item_crate.crate_closed_timestamp = frappe.utils.now()

        source_doc.save()

    if commit:
        frappe.db.savepoint('close_crate')

        try:
            frappe.db.commit()
            
        except Exception as e:
            frappe.db.rollback()
            raise exceptions.SystemError(f'Error closing crate: {e}')


def get_workflow_details(target_warehouse:str=None):
    """Will return all workflows if target warehouse is not passed (For privileged users)"""
    settings = get_settings()
    active_workflows = [row for row in settings.workflow_settings if row.is_active]

    if not active_workflows:
        raise exceptions.ValidationError('No active workflows found. Contact IT.')

    if target_warehouse:
        validations.validate_exists('Warehouse', target_warehouse)
        matching_row = next((row for row in active_workflows if row.target_warehouse == target_warehouse), None)
        
        if matching_row is None:
            raise exceptions.ValidationError(f'No active workflow found for {target_warehouse}. Contact Supervisor.')
        
        workflows = [matching_row]

    else:
        workflows = active_workflows

    result = []

    for row in workflows:
        verification_branches = {
            wh for wh in [
                row.verification_branch_1,
                row.verification_branch_2,
                row.verification_branch_3
            ] if wh
        }

        picking_warehouse_branches = {
            wh: branch for wh, branch in [
                (row.picking_warehouse_1, row.picking_user_branch_1),
                (row.picking_warehouse_2, row.picking_user_branch_2),
                (row.picking_warehouse_3, row.picking_user_branch_3)
            ] if wh
        }

        picking_warehouse_stores = {
            wh: store for wh, store in [
                (row.picking_warehouse_1, row.picking_store_1),
                (row.picking_warehouse_2, row.picking_store_2),
                (row.picking_warehouse_3, row.picking_store_3)
            ] if wh
        }

        result.append(frappe._dict({
            'target_warehouse': row.target_warehouse,
            'picking_warehouse_branches': picking_warehouse_branches,
            'picking_warehouse_stores': picking_warehouse_stores,
            'verification_branches': verification_branches,
            'verification_user_role': row.verification_user_role,
            'verification_after_receiving': row.verification_after_receiving,
            # 'transit_required': row.transit_required,
            'transit_after_verification': row.transit_after_verification,
            'transit_user_role': row.transit_user_role,
            'transit_warehouse': row.transit_warehouse,
            'receiving_user_role': row.receiving_user_role,
            'receiving_after_verification': row.receiving_after_verification,
            'send_notifications': row.send_notifications
        }))

    return result[0] if target_warehouse else result


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
