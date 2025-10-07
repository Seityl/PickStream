import cups
import json
import html
import tempfile
from typing import List, Dict, Any, Tuple, Optional

import frappe
from frappe import _
from frappe.utils import strip_html, now_datetime

import pick_stream

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
    
def check_item_against_barcode(item_code:str, barcode:str) -> bool:
    pick_stream.validations.validate_exists('Item', item_code)
    pick_stream.validations.validate_exists('Item Barcode', barcode, child=True, field='barcode')
    parent = frappe.db.get_value('Item Barcode', {'barcode': barcode}, 'parent')
    if parent != item_code:
        return False
    return True

def check_material_request_item_group_in_progress(mr_name:str, item_group:str) -> dict:
    source_name = pick_stream.utils.get_source_name(mr_name, item_group)
    if source_name:
        if frappe.db.get_value('Source', source_name, 'status') != 'Completed':
            return frappe._dict({'in_progress': True, 'source': source_name})

    return frappe._dict({'in_progress': False, 'source': source_name})

def assign_users_to_mr(doc:str, method:str) -> dict:
    """Assigns users to a Material Request (MR) based on item groups in the MR."""
    if not doc.custom_assign_warehouse_staff:
        return frappe.msgprint('Assignment to warehouse staff was skipped', alert=True)

    settings = pick_stream.utils.get_settings()
    
    try:
        mr_name = doc.name
        mr_doc = frappe.get_doc('Material Request', mr_name)
        # Default to first branch (King George) to avoid situations where source warehouse is not set
        # Source should be explicitly set if is goods are being picked from Mega 
        warehouse_group_map = settings.warehouse_group_map
        warehouse_to_branch = {mapping.warehouse: mapping.branch for mapping in warehouse_group_map}
        branch = warehouse_to_branch.get(mr_doc.set_from_warehouse, warehouse_group_map[0].branch)

        mr_item_groups = {item.item_group for item in mr_doc.items}
        fulfillment_users = frappe.db.sql_list(
            """
            SELECT DISTINCT ugm.user
            FROM `tabUser Group Member` ugm
            JOIN `tabUser Group` ug ON ug.name = ugm.parent
            JOIN `tabEmployee` emp ON emp.user_id = ugm.user
            WHERE ug.name IN %(mr_item_groups)s
            AND emp.branch = %(branch)s
            AND ug.custom_is_item_group = '1'
            """, {
                'mr_item_groups': list(mr_item_groups),
                'branch': branch
            }
        )

        if not fulfillment_users:
            return frappe.msgprint(f'No fulfillment users found for Material Request {mr_name} in branch {branch}', alert=True)

        for user in fulfillment_users:
            try:
                existing_todo = frappe.db.get_value(
                    'ToDo', {
                        'reference_type': 'Material Request',
                        'reference_name': mr_doc.name,
                        'allocated_to': user,
                    },
                    ['name', 'status'],
                    as_dict=True
                )

                if existing_todo: 
                    if existing_todo.status == 'Open':
                        frappe.msgprint(f'Open ToDo already exists for user {user} on Material Request {mr_name}.', alert=True)

                    else:
                        todo_doc = frappe.get_doc('ToDo', existing_todo.name)
                        todo_doc.update({
                            'assigned_by': frappe.session.user,
                            'description': f'Material Request {mr_doc.name} requires your action.',
                            'priority': 'High',
                            'status': 'Open'
                        })
                        todo_doc.save()
                        todo_doc.add_comment('Info', 'Reopened this ToDo as the user is now required to take action on the Material Request')
                        frappe.msgprint(f'Reopened ToDo {todo_doc.name} as the user {user} is now required to take action on Material Request {mr_name}.', alert=True)
                    
                else:
                    todo = frappe.get_doc({
                        'doctype': 'ToDo',
                        'allocated_to': user,
                        'reference_type': 'Material Request',
                        'reference_name': mr_doc.name,
                        'assigned_by': frappe.session.user,
                        'description': f'Material Request {mr_doc.name} requires your action.',
                        'priority': 'High',
                        'status': 'Open'
                    })
                    todo.insert()
                    frappe.msgprint(f'Created ToDo for user {user} on Material Request {mr_name}.', alert=True)

            except Exception as e:
                frappe.msgprint(f'Error processing ToDo for User {user}', alert=True)
                frappe.log_error(
                    message=f'Error processing ToDo for User {user}: {str(e)}',
                    title='[Pick Stream] Error in assign_users_to_mr()',
                    reference_name=mr_name
                )
                continue
        
    except Exception as e:
        frappe.msgprint(f'Error assigning users to MR: {mr_name}', alert=True)
        frappe.log_error(
            message=f'Error assigning users to MR: {mr_name}: {str(e)}',
            title='[Pick Stream] Error in assign_users_to_mr()',
            reference_name=mr_name
        )

def get_printers() -> dict:
    settings = pick_stream.utils.get_settings()
    try:
        conn = cups.Connection(host=settings.host, port=settings.port)
        return list(conn.getPrinters().keys())

    except RuntimeError as e:
        raise pick_stream.exceptions.ValidationError(f'Error connecting to CUPS: {e}')

    except Exception as e:
        raise pick_stream.exceptions.ValidationError(f'Error connecting to CUPS: {e}')  


def get_user_material_requests(user: str) -> List:
    """Returns submitted Material Requests assigned to a user with item group availability."""
    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_permission(user, 'picking')
    # Get user context
    user_item_groups = pick_stream.utils.get_assigned_item_groups(user)
    user_branch = pick_stream.utils.get_user_branch(user)
    warehouse_group = pick_stream.utils.get_warehouse_group(user, user_branch)  
    child_warehouses = pick_stream.utils.get_child_warehouses(warehouse_group)
    # Get default warehouse from settings
    settings = pick_stream.utils.get_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse
    mr_list = frappe.db.sql("""
        WITH UserMRs AS (
            -- Get all submitted MRs assigned to user with availability check
            SELECT DISTINCT
                mr.name,
                mr.set_warehouse AS target_warehouse,
                -- Use default warehouse if set_from_warehouse is NULL or empty
                COALESCE(NULLIF(mr.set_from_warehouse, ''), %(default_warehouse)s) AS source_warehouse,
                mr.creation
            FROM `tabToDo` td
            INNER JOIN `tabMaterial Request` mr
                ON td.reference_name = mr.name
            WHERE td.allocated_to = %(user)s
                AND td.status = 'Open'
                AND td.reference_type = 'Material Request'
                AND mr.docstatus = 1
                AND EXISTS (
                    SELECT 1
                    FROM `tabMaterial Request Item` mri
                    INNER JOIN `tabItem` item ON mri.item_code = item.name
                    INNER JOIN `tabBin` bin ON mri.item_code = bin.item_code
                    WHERE mri.parent = mr.name
                        AND item.item_group IN %(user_item_groups)s
                        AND bin.actual_qty >= 1
                        AND bin.warehouse IN %(child_warehouses)s
                        AND (mri.stock_qty > COALESCE(mri.ordered_qty, 0))
                )
        ),
        ItemGroupAvailability AS (
            -- Get availability with specific reasons for each item group per MR
            SELECT 
                mri.parent AS mr_name,
                mri.item_group,
                CASE 
                    -- Check if completed Source exists
                    WHEN EXISTS (
                        SELECT 1
                        FROM `tabSource` src
                        WHERE src.item_group = mri.item_group
                            AND src.material_request = mri.parent
                            AND (src.status = 'Completed' OR src.docstatus = 1)
                    ) THEN 'already_picked'
                    -- Check if stock is available for ANY item in this group
                    WHEN NOT EXISTS (
                        SELECT 1
                        FROM `tabMaterial Request Item` mri_check
                        INNER JOIN `tabItem` item ON mri_check.item_code = item.name
                        INNER JOIN `tabBin` bin ON mri_check.item_code = bin.item_code
                        WHERE mri_check.parent = mri.parent
                            AND item.item_group = mri.item_group
                            AND bin.actual_qty >= 1
                            AND bin.warehouse IN %(child_warehouses)s
                            AND (mri_check.stock_qty > COALESCE(mri_check.ordered_qty, 0))
                    ) THEN 'no_stock'
                    -- Otherwise available
                    ELSE 'available'
                END AS availability_status
            FROM `tabMaterial Request Item` mri
            INNER JOIN UserMRs umr ON mri.parent = umr.name
            WHERE mri.item_group IN %(user_item_groups)s
            GROUP BY mri.parent, mri.item_group
        )
        SELECT 
            umr.name,
            umr.target_warehouse,
            umr.source_warehouse,
            -- Aggregate item group availability as JSON object with status
            COALESCE(
                JSON_OBJECTAGG(
                    iga.item_group, 
                    iga.availability_status
                ),
                JSON_OBJECT()
            ) AS item_group_availability
        FROM UserMRs umr
        LEFT JOIN ItemGroupAvailability iga ON umr.name = iga.mr_name
        GROUP BY umr.name, umr.target_warehouse, umr.source_warehouse, umr.creation
        ORDER BY umr.creation ASC
    """, {
        'user': user,
        'user_item_groups': tuple(user_item_groups),
        'child_warehouses': tuple(child_warehouses),
        'default_warehouse': default_set_from_warehouse
    }, as_dict=True)
    # Parse JSON
    for mr in mr_list:
        if mr.get('item_group_availability'):
            try:
                # Convert JSON string to dict if needed
                if isinstance(mr['item_group_availability'], str):
                    mr['item_group_availability'] = json.loads(mr['item_group_availability'])
            except (json.JSONDecodeError, AttributeError):
                mr['item_group_availability'] = {}
        else:
            mr['item_group_availability'] = {}
    return mr_list
        

def get_material_request_item_groups_view_details(mr_name: str, user: str) -> dict:
    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Material Request', mr_name)
    pick_stream.validations.validate_user_assigned_to_mr(mr_name, user)
    settings = pick_stream.utils.get_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse
    user_branch = pick_stream.utils.get_user_branch(user)
    warehouse_group = pick_stream.utils.get_warehouse_group(user, user_branch)
    child_warehouses = pick_stream.utils.get_child_warehouses(warehouse_group)
    out = frappe.db.sql(
        """
            SELECT 
                mr.name AS mr_name,
                mr.set_warehouse AS target_warehouse,
                COALESCE(mr.set_from_warehouse, %(default_set_from_warehouse)s) AS source_warehouse
            FROM `tabMaterial Request` mr
            WHERE
                mr.name = %(mr_name)s
        """,
        {
            'mr_name': mr_name,
            'default_set_from_warehouse': default_set_from_warehouse
        },
        as_dict=True
    )[0]
    out['item_group_availability'] = pick_stream.utils.get_mr_available_item_groups_for_user(
        mr_name,
        user,
        child_warehouses
    )
    for item_group in out['item_group_availability']:
        crates = frappe.db.sql(
            """
                SELECT COALESCE(
                    (
                        SELECT JSON_ARRAYAGG(
                            JSON_OBJECT(
                                'crate_code', ps.crate_code,
                                'status', ps.status
                            )
                        )
                        FROM `tabStream` ps
                        WHERE 
                            ps.material_request = %(mr_name)s
                            AND ps.item_group = %(item_group)s
                            AND (ps.crate_code IS NOT NULL 
                                OR ps.item_group IS NOT NULL 
                                OR ps.status IS NOT NULL)
                    ),
                    JSON_ARRAY()
                ) AS crates
            """,
            {
                'mr_name': mr_name,
                'item_group': item_group['name']
            },
            as_dict=True
        )
        item_group['crates'] = json.loads(crates[0].get('crates', '[]')) if crates else []
        item_group['item_count'] = pick_stream.utils.get_material_request_item_group_item_quantity(
            mr_name,
            item_group['name'],
            child_warehouses
        )
    return out


# TODO: Dont hardcode this
def get_workflow_target_warehouse(user:str, user_branch:str) -> str:
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
            raise pick_stream.exceptions.ValidationError(f"Employee for user '{user}' branch is not valid. Contact HR Department.")

def get_material_request_picking_view_details(mr_name:str, user:str, item_group:str) -> dict:
    if pick_stream.utils.check_source_exists(mr_name, item_group):
        source_name = pick_stream.utils.get_source_name(mr_name, item_group)
        return get_relevant_source_item(source_name)
    else:
        source = create_source(mr_name, item_group, user)
        return get_relevant_source_item(source.name)

def get_relevant_source_item(source_name: str) -> dict:
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
            # No duplicates - use requested_qty (assuming available_qty >= requested_qty)
            out.requested_qty = item.requested_qty

    except StopIteration:
        # No items found matching the criteria
        pass
    
    return out


def get_user_crate(user: str) -> Optional[str]:
    pick_stream.validations.validate_exists('User', user)
    all_crates  = frappe.get_all(
        'Item Crates',
        fields=['crate_code'],
        filters=[
            ['parenttype', '=', 'Source'], 
            ['crate_code', 'is', 'set'],
            ['picking_user', '=', user],
            ['crate_closed', '=', 0],
            ['transited', '=', 0],
            ['verified', '=', 0],
            ['received', '=', 0]
        ],
        distinct=True
    )
    crate_dict = {}
    for crate in all_crates:
        crate_code = crate['crate_code']
        if crate_code not in crate_dict or crate['modified'] > crate_dict[crate_code]['modified']:
            crate_dict[crate_code] = crate
    matching_crates = list(crate_dict.values())
    if len(matching_crates) > 1:
        matching_crates.sort(key=lambda x: x['modified'])
        crates_to_close = matching_crates[:-1]
        most_recent_crate = matching_crates[-1]['crate_code']
        for crate_data in crates_to_close:
            crate_code = crate_data['crate_code']
            close_crate(crate_code, commit=True)
            frappe.log_error('close_crate(crate_code, commit=True)')
        return most_recent_crate
    return matching_crates[0]['crate_code'] if matching_crates else ''

    
def source_is_complete(source_name: str) -> bool:
    doc = frappe.get_doc('Source', source_name)
    return not any(not item.scanned and not item.skipped for item in doc.items) 

def get_relevant_source_crate_code(source:str) -> str:
    # Should not return crate code if crate is closed since it is unavailable
    doc = frappe.get_doc('Source', source)
    for item in reversed(doc.items):
        # if item.scanned and item.crate_code and not item.crate_closed:
        if item.scanned and item.crate_code:
            return item.crate_code
    return None
        
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
        raise pick_stream.exceptions.ValidationError(f"Error creating item identifier: {e}")
    
    return str(identifier.name)

def get_item_print_details(item_code: str, mr_name: str, from_warehouse: str, to_warehouse: str) -> dict:
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

    item = next(item for item in source_doc.item_crates if item.item_code == item_code)

    if not item:
        return None
        
    return frappe._dict({
        'identifier_code': item.identifier_code,
        'qty': item.qty if not item.verified_qty else item.verified_qty
    })

def get_user_crate_details(user:str) -> Dict:
    pick_stream.validations.validate_exists('User', user)
    
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

def get_crate_details_(
    user:str,
    crate_code:str,
    to_verify:bool=False,
    to_transit:bool=False,
    to_receive:bool=False
) -> dict:
    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Crate', crate_code)

    to_warehouse = frappe.db.get_value('Crate', crate_code, 'to_warehouse')
    workflow_details = pick_stream.utils.get_workflow_details(to_warehouse)
    
    if not pick_stream.utils.has_role(user, 'Stock Manager'):
        if to_verify:
            validate_role(user, workflow_details.verification_user_role)

            user_branch = pick_stream.utils.get_user_branch(user)
            if user_branch not in workflow_details.verification_branches:
                raise pick_stream.exceptions.ValidationError(f"User '{user}' is not authorized to verify from '{user_branch}'. Contact Supervisor.")
        
        if to_transit:
            validate_role(user, workflow_details.transit_user_role)
            
        if to_receive:
            validate_role(user, workflow_details.receiving_user_role)

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

def create_source(mr_name:str, item_group:str, user:str) -> dict:
    source = frappe.new_doc('Source')
    items = pick_stream.utils.get_material_request_items_details(mr_name, user, item_group)

    settings = pick_stream.utils.get_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse

    source.update({
        'material_request': mr_name,
        'from_warehouse': frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or default_set_from_warehouse,
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
        raise pick_stream.exceptions.SystemError(str(e))

def crate_is_closed(crate_code:str, user:str) -> bool:
    pick_stream.validations.validate_exists('Crate', crate_code)
    pick_stream.validations.validate_exists('User', user)
    source_list = frappe.db.get_all(
        'Stream',
        filters={
            'status': ['!=', 'Completed'],
            'crate_code': crate_code, 
            'user': user 
        },
        fields=['source']
    )

    if not source_list:
        return False

    item_crates = frappe.db.get_all(
        'Item Crates',
        filters={
            'parent': ['in', [i.source for i in source_list]],
            'crate_code': crate_code
        },
        fields=['crate_closed']
    )

    if not item_crates:
        return False

    return all(item.crate_closed for item in item_crates)

def create_stream(source:dict, crate_code:str) -> str:
    user = source.user
    material_request = source.material_request
    item_group = source.item_group
    from_warehouse = source.from_warehouse
    to_warehouse = source.to_warehouse

    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Material Request', material_request)
    pick_stream.validations.validate_user_assigned_to_mr(material_request, user)
    pick_stream.validations.validate_user_assigned_to_item_group(user, item_group)
    
    stream = frappe.new_doc('Stream')
    stream.update({
        'material_request': material_request,
        'from_warehouse': from_warehouse,
        'to_warehouse': to_warehouse,
        'crate_code': crate_code,
        'item_group': item_group,
        'source': source.name,
        'user': user
    })

    crate_available = pick_stream.utils.check_crate_availability(crate_code, user, from_stream=True) 
    if not crate_available:
        raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' is not available. Contact Supervisor.")

    item_crate_qty_map = {}
    for item_crate in source.item_crates:
        if item_crate.crate_code == crate_code:
            item_crate_qty_map[item_crate.source_item] = item_crate.qty

    matching_source_item_set = set(item_crate_qty_map.keys())

    for item in source.items:
        if item.name in matching_source_item_set:
            crate_qty = item_crate_qty_map[item.name]

            stream.append('items', {
                'item_code': item.item_code,
                'item_name': item.item_name,
                'item_group': item.item_group,
                'description': item.description,
                'from_warehouse': item.from_warehouse,
                'to_warehouse': item.to_warehouse,
                'uom': item.uom,
                'conversion_factor': item.conversion_factor,
                'requested_qty': item.requested_qty,
                'scanned_qty': crate_qty,
                'scanned': item.scanned,
                'source': source.name,
                'material_request': item.material_request,
                'material_request_item': item.material_request_item
            })

    frappe.db.savepoint('create_stream')

    try:
        stream.insert()
        frappe.db.commit()
        return stream.name

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(str(e))

def update_stream(source:dict, stream_name:str, status:str) -> dict:
    stream = frappe.get_doc('Stream', stream_name)
    stream.update({'status': status})

    stream.items = []

    item_crate_qty_map = {}
    for item_crate in source.item_crates:
        if item_crate.crate_code == stream.crate_code:
            item_crate_qty_map[item_crate.source_item] = item_crate.qty

    matching_source_item_set = set(item_crate_qty_map.keys())

    for item in source.items:
        if item.name in matching_source_item_set:
            crate_qty = item_crate_qty_map[item.name]

            stream.append('items', {
                'item_code': item.item_code,
                'item_name': item.item_name,
                'item_group': item.item_group,
                'description': item.description,
                'from_warehouse': item.from_warehouse,
                'to_warehouse': item.to_warehouse,
                'uom': item.uom,
                'conversion_factor': item.conversion_factor,
                'requested_qty': item.requested_qty,
                'scanned_qty': crate_qty,
                'scanned': item.scanned,
                'source': source.name,
                'material_request': item.material_request,
                'material_request_item': item.material_request_item
            })

    frappe.db.savepoint('update_stream')

    try:
        stream.save()
        frappe.db.commit()
        return stream

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(str(e))

def process_scan_details(
    user:str,
    mr_name:str,
    item_code:str,
    item_group:str,
    crates:Any=[],
    as_box:bool = False,
    scanned_qty:int = 0,
    skipped:bool = False,
    as_other:bool = False,
    crate_code:str = None
) -> dict:
    pick_stream.validations.validate_scan_params(scanned_qty, crate_code, as_box, as_other, skipped, crates)
    if crate_code:
        pick_stream.validations.validate_exists('Crate', crate_code)

    if crates:
        crates = json.loads(crates)
        crates = [frappe._dict(crate) for crate in crates]
        [pick_stream.validations.validate_exists('Crate', crate.crate_code) for crate in crates]

    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Item', item_code)
    pick_stream.validations.validate_exists('Material Request', mr_name)

    pick_stream.validations.validate_user_assigned_to_mr(mr_name, user)
    pick_stream.validations.validate_user_assigned_to_item_group(user, item_group)

    source_name = pick_stream.utils.get_source_name(mr_name, item_group)
    if not source_name:
        raise pick_stream.exceptions.SystemError(f"Source for Material Request '{mr_name}' does not exist. Contact IT.")

    relevant_item = get_relevant_source_item(source_name) 
    if relevant_item.item_code != item_code:
        raise pick_stream.exceptions.SystemError(f"Scanned item '{item_code}' does not match relevant item '{relevant_item.item_code}'. Contact IT.")

    doc = frappe.get_doc('Source', source_name)
    settings = pick_stream.utils.get_settings()
    # Default to default set from warehouse if not set on material request
    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')

    out = frappe._dict()

    if crate_code:
        out.message = process_scan_as_crate(doc, crate_code, item_code, user, scanned_qty)
    elif as_box:
        identifier_code = create_item_identifier(item_code, 'box', user, mr_name, from_warehouse, to_warehouse, scanned_qty, relevant_item.uom)
        out.message = process_scan_as_box(doc, identifier_code, item_code, scanned_qty, user)
    elif as_other:
        identifier_code = create_item_identifier(item_code, 'other', user, mr_name, from_warehouse, to_warehouse, scanned_qty, relevant_item.uom)
        out.message = process_scan_as_other(doc, identifier_code, item_code, scanned_qty, user)
    elif skipped:
        out.message = process_scan_as_skip(doc, item_code)
    elif crates:
        out.message = process_scan_as_crates(doc, crates, user, item_code)

    doc.scan_pointer += 1

    frappe.db.savepoint('process_scan_details')

    try:
        doc.save()
        frappe.db.commit()

        if crates:
            for crate in crates[:-1]:
                close_crate(crate.crate_code, commit=True)

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.SystemError(str(e))
        
    out.complete = frappe.db.get_value('Source', doc.name, 'status') == 'Completed'
        
    return out

def process_scan_as_crate(source:dict, crate_code:str, item_code:str, user:str, scanned_qty:int, from_crates:bool = False) -> str:
    if from_crates:
        item = next((item for item in source.items if item.item_code == item_code and not item.skipped), None)
    else:
        item = next((item for item in source.items if item.item_code == item_code and not item.skipped and not item.scanned), None)
    
    if not item:
        raise pick_stream.exceptions.SystemError(f'Item {item_code} not found in source document. Contact IT.')
    
    existing_crate = next((
        crate for crate in source.item_crates
        if crate.item_code == item_code 
        and crate.crate_code == crate_code
        and crate.source_item == item.name
    ), None)
    
    if existing_crate:
        raise pick_stream.exceptions.SystemError(f'Crate {crate_code} already exists for item {item_code}. Contact IT.')
    
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

def process_scan_as_crates(doc, crates, user, item_code):
    out = []
    for crate in crates:
        result = process_scan_as_crate(doc, crate.crate_code, item_code, user, crate.scanned_qty, from_crates=True)
        out.append(result)

    return  ' '.join(out)
    
def process_scan_as_box(source:dict, identifier_code:str, item_code:str, scanned_qty:int, user:str) -> str:
    item = next((item for item in source.items if item.item_code == item_code and not item.skipped and not item.scanned), None)
    if not item:
        raise pick_stream.exceptions.SystemError(f'Item {item_code} not found in source document. Contact IT.')

    existing_identifier = next((
        identifier for identifier in source.item_crates
        if identifier.item_code == item_code and identifier.identifier_code == identifier_code
    ), None)
    
    if existing_identifier:
        raise pick_stream.exceptions.SystemError(f'Identifier {identifier_code} already exists for item {item_code}. Contact IT.')
    
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

def process_scan_as_other(source:dict, identifier_code:str, item_code:str, scanned_qty:int, user:str) -> str:
    item = next((item for item in source.items if item.item_code == item_code and not item.skipped and not item.scanned), None)
    if not item:
        raise pick_stream.exceptions.ValidationError(f'Item {item_code} not found in source document. Contact IT.')

    existing_identifier = next((
        identifier for identifier in source.item_crates
        if identifier.item_code == item_code and identifier.identifier_code == identifier_code
    ), None)
    
    if existing_identifier:
        raise pick_stream.exceptions.ValidationError(f'Identifier {identifier_code} already exists for item {item_code}. Contact IT.')
    
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

def process_scan_as_skip(source:dict, item_code:str) -> str:
    item = next((item for item in source.items if item.item_code == item_code and not item.scanned and not item.skipped))
    item.skipped = 1
    return f'Skipped item {item_code}'

# Need to rethink this 16/05/2025
# Made obsolete 27/05/2025
# def process_scan_as_close_crate(source:dict, crate_code:str, item_code:str, scanned_qty:int, skipped:bool=False) -> str:
#     item = next((item for item in source.items if item.item_code == item_code))
#     if skipped:
#         item.skipped = skipped
#         return f'Skipped item {item_code}'
#     item.scanned = 1
#     item.crate_code = crate_code
#     item.scanned_qty = scanned_qty
#     return f'Scanned {scanned_qty} {item.uom} for item {item_code} into crate {crate_code}'

def close_crate(crate_code:str, items:Any=[], commit:bool=False) -> None:
    frappe.log_error('crate closed', f'crate closed {frappe.utils.now()}')
    open_crate_items = frappe.db.get_all('Item Crates',
        filters={
            'crate_code': crate_code,
            'parenttype': 'Source',
            'crate_closed': '0'
        },
        fields=['parent']
    )

    if not open_crate_items:
        raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' is already closed. Contact IT.")

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
            raise pick_stream.exceptions.SystemError(f'Error closing crate: {e}')
            
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
    validate_printer_exists(printer)
    settings = pick_stream.utils.get_settings()

    if crate_code:
        pick_stream.validations.validate_exists('Crate', crate_code)
        if qty <= 0:
            qty = 1
        return print_crate_label(printer, settings, crate_code, qty)

    if item_identifier:
        pick_stream.validations.validate_exists('Pick Stream Identifier', item_identifier)
        identifier_doc = frappe.get_doc('Pick Stream Identifier', item_identifier)
        mr_name = identifier_doc.material_request
        item_code = identifier_doc.item_code
        item_type = identifier_doc.item_type
        user = frappe.session.user

        # User must explicitly give qty when identifier is provided
        if qty == 0:
            raise pick_stream.exceptions.ValidationError('Cannot print 0 labels. Contact IT.')

    # Validate params when identifier is not provided
    else:
        if not mr_name:
            raise pick_stream.exceptions.ValidationError('Material Request name is required. Contact IT.')
        if not item_code:
            raise pick_stream.exceptions.ValidationError('Item Code is required. Contact IT.')
        if not item_type:
            raise pick_stream.exceptions.ValidationError('Item Type is required. Contact IT.')
        if not item_type:
            raise pick_stream.exceptions.ValidationError('User is required. Contact IT.')

    if qty < 0:
        raise pick_stream.exceptions.ValidationError(f'Cannot print {qty} labels. Contact IT.')

    pick_stream.validations.validate_exists('Material Request', mr_name)
    pick_stream.validations.validate_exists('Item', item_code)
    validate_item_type(item_type, settings)
    pick_stream.validations.validate_exists('User', user)
        
    # Default to default set from warehouse if not set on material request
    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')
    item_name = frappe.db.get_value('Item', item_code, 'item_name')
    print_job = print_item_identifier(user, mr_name, printer, from_warehouse, to_warehouse, item_code, item_type, settings, item_name, qty, item_identifier)
    return print_job

def print_drug_label(printer:str, barcode, item_code, item_name, qty=1):
    settings = pick_stream.utils.get_settings()

    zpl_template = (
        '^XA\n'
        '^FO90,92,2\n'
        '^FWN\n'
        '^BY3.2,2,96\n'
        '^BCN,96,N,N^FD{barcode}^FS\n'
        '^FO90,16,2\n'
        '^FWN\n'
        '^A40,40^FD{item_code}^FS\n'
        '^FO90,64,2\n'
        '^FWN\n'
        '^A16,16^FD{item_name}^FS\n'
        '^XZ\n'
    )

    try:
        host, port = settings.get('host'), settings.get('port')
        cups.setServer(host)
        cups.setPort(port)
        conn = cups.Connection(host=host, port=port)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.zpl') as tmp:
            for i in range(qty):
                label_data = {
                    'barcode': barcode,
                    'item_code': item_code,
                    'item_name': item_name
                }
                tmp.write(zpl_template.format(**label_data).encode('utf-8'))
            tmp.flush()
            tmp_path = tmp.name

        options = {
            'document-format': 'application/vnd.cups-raw',
            'media': 'Custom.3x2in',
            'scaling': '100',
            'fit-to-page': 'True'
        }
        
        job_name = f'Medication Label Print - {label_data["text_line1"]}'
        conn.printFile(printer, tmp_path, job_name, options)

        frappe.db.commit()

        return 'Print Job Submitted Successfully'

    except RuntimeError as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f"CUPS connection error: {e}")

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f"Printing failed: {e}")
    
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
        raise pick_stream.exceptions.ValidationError(f"CUPS connection error: {e}")

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f"Printing failed: {e}")

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
            raise pick_stream.exceptions.ValidationError(f"Item '{item_code}' not found in source for material request '{mr_name}'.")

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

        frappe.db.savepoint('sp33')

        # Update Item Identifier after successfully sending print job
        current_doc = frappe.get_doc('Pick Stream Identifier', item_identifier)
        current_printed = current_doc.printed or 0
        current_qty_printed = current_doc.qty_printed or 0
        current_date_printed = current_doc.dates_printed or ''

        new_entry = f'{user} - {frappe.utils.now()}'
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
        raise pick_stream.exceptions.ValidationError(f'Error connecting to CUPS: {e}')

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f'Error connecting to CUPS: {e}')
    
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

def get_identifier_details(item_identifier:str) -> dict:
    if not frappe.db.exists('Pick Stream Identifier', item_identifier):
        raise pick_stream.ValidationError(f'Item Identifier {item_identifier} not found. Contact IT.')

    doc = frappe.get_doc('Pick Stream Identifier', item_identifier)
    return frappe._dict({
        'material_request': doc.material_request,
        'from_warehouse': doc.from_warehouse,
        'date_created': doc.date_created,
        'to_warehouse': doc.to_warehouse,
        'date_printed': doc.date_printed,
        'item_code': doc.item_code,
        'item_type': doc.item_type,
        'printed': doc.printed,
        'user': doc.user,
        'uom': doc.uom,
        'qty': doc.qty
    })
    
def get_verification_list(user:str) -> Dict:
    pick_stream.validations.validate_exists('User', user)

    stock_manager = pick_stream.utils.has_role(user, 'Stock Manager') 
    if not stock_manager:
        user_branch = pick_stream.utils.get_user_branch(user)
        target_warehouse = get_workflow_target_warehouse(user, user_branch)
        workflow_details = pick_stream.utils.get_workflow_details(target_warehouse)

        validate_role(user, workflow_details.verification_user_role)

        if user_branch not in workflow_details.verification_branches:
            raise pick_stream.exceptions.ValidationError(f"User '{user}' is not authorized to verify from '{user_branch}'. Contact Supervisor.")

        workflows = [workflow_details]

    else:
        workflows = pick_stream.utils.get_workflow_details()

    crate_receiving_conditions = []
    identifier_receiving_conditions = []
    
    for workflow in workflows:
        base_crate_condition = f"(s.to_warehouse = '{workflow.target_warehouse}' AND ic.crate_closed = 1 AND ic.verified = 0"
        base_identifier_condition = f"(s.to_warehouse = '{workflow.target_warehouse}' AND ic.verified = 0"
        
        if workflow.transit_after_verification:
            base_crate_condition += " AND ic.transited = 0"
            base_identifier_condition += " AND ic.transited = 0"
        
        if workflow.verification_after_receiving:
            crate_condition = f"{base_crate_condition} AND ic.received = 1)"
            identifier_condition = f"{base_identifier_condition} AND ic.received = 1)"
            
        elif workflow.receiving_after_verification:
            crate_condition = f"{base_crate_condition} AND ic.received = 0)"
            identifier_condition = f"{base_identifier_condition} AND ic.received = 0)"
        
        crate_receiving_conditions.append(crate_condition)
        identifier_receiving_conditions.append(identifier_condition)

    crate_where_clause = ' OR '.join(crate_receiving_conditions)
    identifier_where_clause = ' OR '.join(identifier_receiving_conditions)
    
    crate_query = f"""
        SELECT DISTINCT 
            ic.crate_code,
            s.from_warehouse,
            s.to_warehouse
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        WHERE ic.parenttype = 'Source'
        AND ic.crate_code IS NOT NULL
        AND ic.crate_code != ''
        AND ({crate_where_clause})
        ORDER BY ic.modified ASC
    """
    
    identifier_query = f"""
        SELECT DISTINCT 
            ic.identifier_code,
            s.from_warehouse,
            s.to_warehouse
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        WHERE ic.parenttype = 'Source'
        AND ic.identifier_code IS NOT NULL
        AND ic.identifier_code != ''
        AND ({identifier_where_clause})
        ORDER BY ic.modified ASC
    """

    crate_data = frappe.db.sql(crate_query, as_dict=True)
    identifier_data = frappe.db.sql(identifier_query, as_dict=True)

    crate_details = []
    if crate_data:
        for row in crate_data:
            crate_details.append({
                'crate_code': row.crate_code,
                'source_warehouse': row.from_warehouse,
                'target_warehouse': row.to_warehouse
            })

    identifier_details = []
    if identifier_data:
        for row in identifier_data:
            identifier_details.append({
                'identifier_code': row.identifier_code,
                'source_warehouse': row.from_warehouse,
                'target_warehouse': row.to_warehouse
            })

    return {
        'crate_details': crate_details,
        'identifier_details': identifier_details
    }

# TODO: Make sure verified qty doesn't exceed requested qty
def process_verification_request(
    user:str,
    items:Any,
    crate_code:str=None,
    identifier_code:str=None
) -> str:
    if crate_code and identifier_code:
        raise pick_stream.exceptions.SystemError('Cannot process both crate_code and identifier_code simultaneously. Contact IT.')
    
    pick_stream.validations.validate_exists('User', user)

    if crate_code:
        pick_stream.validations.validate_exists('Crate', crate_code)
        crate = frappe.get_doc('Crate', crate_code)
        to_warehouse = crate.to_warehouse
        if not to_warehouse:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' has no destination warehouse set. Contact IT.")

        if not crate.streams:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' has no streams. Contact IT.")

    elif identifier_code:
        pick_stream.validations.validate_exists('Pick Stream Identifier', identifier_code)
        identifier = frappe.get_doc('Pick Stream Identifier', identifier_code)
        to_warehouse = identifier.to_warehouse
        if not to_warehouse:
            raise pick_stream.exceptions.SystemError(f"Identifier '{identifier_code}' has no destination warehouse set. Contact IT.")

    if isinstance(items, str):
        items = json.loads(items)

    items = [frappe._dict(item) for item in items]
    [pick_stream.validations.validate_exists('Item', item.item_code) for item in items]
 
    workflow_details = pick_stream.utils.get_workflow_details(to_warehouse)
    
    if not pick_stream.utils.has_role(user, 'Stock Manager'):
        validate_role(user, workflow_details.verification_user_role)

        user_branch = pick_stream.utils.get_user_branch(user)
        if user_branch not in workflow_details.verification_branches:
            raise pick_stream.exceptions.PermissionError(f"User '{user}' is not authorized to verify from '{user_branch}'. Contact Supervisor.")

    all_updated_items = []     # List of all updated items
    all_discrepancies = []     # List of all discrepancies
    overdelivery_items = []    # Track items with overdelivery

    source_item_mapping = {}   # Mapping of source to crate/identifier, item code and original qty
    original_qty_mapping = {}  # Mapping of item code to aggregate original qty
    requested_qty_mapping = {} # Track original requested quantities

    verified_items = {item.item_code: int(item.qty) for item in items}

    if crate_code:
        source_names = set(frappe.db.get_value('Stream', row.stream, 'source') for row in crate.streams)

    elif identifier_code:
        source_names = [frappe.db.get_value('Item Crates', {'identifier_code': identifier_code}, 'parent')]
    
    source_docs = {}
    for source in source_names:
        source_doc = frappe.get_doc('Source', source)
        source_docs[source] = source_doc

    material_requests = set()
    for source in source_names:
        material_requests.add(source_docs[source].material_request)

    for mr_name in material_requests:
        mr_doc = frappe.get_doc('Material Request', mr_name)
        for item in mr_doc.items:
            if item.item_code not in requested_qty_mapping:
                requested_qty_mapping[item.item_code] = 0

            requested_qty_mapping[item.item_code] += item.qty

    for source in source_names:
        source_doc = source_docs[source]
        source_item_mapping[source] = []
        
        for item_crate in source_doc.item_crates:
            if crate_code and item_crate.crate_code == crate_code:
                item_code = item_crate.item_code
                original_qty = item_crate.qty
                
                source_item_mapping[source].append(frappe._dict({
                    'item_crate': item_crate,
                    'item_code': item_code,
                    'original_qty': original_qty
                }))

                if item_code in original_qty_mapping:
                    original_qty_mapping[item_code] += original_qty

                else:
                    original_qty_mapping[item_code] = original_qty

            elif identifier_code and item_crate.identifier_code == identifier_code:
                item_code = item_crate.item_code
                original_qty = item_crate.qty
                
                source_item_mapping[source].append(frappe._dict({
                    'item_crate': item_crate,
                    'item_code': item_code,
                    'original_qty': original_qty
                }))

                if item_code in original_qty_mapping:
                    original_qty_mapping[item_code] += original_qty

                else:
                    original_qty_mapping[item_code] = original_qty
                    
    for item_code, verified_qty in verified_items.items():
        original_qty = original_qty_mapping.get(item_code, 0)
        requested_qty = requested_qty_mapping.get(item_code, 0)
        if original_qty != verified_qty:
            all_discrepancies.append(frappe._dict({
                'item_code': item_code,
                'original_qty': original_qty,
                'verified_qty': verified_qty,
                'requested_qty': requested_qty,
                'difference': verified_qty - original_qty
            }))

            if verified_qty > requested_qty:
                overdelivery_items.append(frappe._dict({
                    'item_code': item_code,
                    'overdelivery_qty': verified_qty - requested_qty,
                    'verified_qty': verified_qty,
                    'requested_qty': requested_qty
                }))

    frappe.db.savepoint('process_verification_request')

    try:
        verified_qty_updates = {}

        # If there are discrepancies quantities need to be adjusted
        for discrepancy in all_discrepancies:
            item_code = discrepancy.item_code
            verified_qty = discrepancy.verified_qty
            original_qty = discrepancy.original_qty
            requested_qty = discrepancy.requested_qty

            # For overdelivery cases, cap the material request fulfillment at requested qty
            # and handle excess separately
            if verified_qty > requested_qty:
                fulfillment_qty = requested_qty

            else:
                fulfillment_qty = verified_qty

            # List of all sources containing this item
            sources_with_item = []

            for source_name, items in source_item_mapping.items():
                for item_data in items:
                    if item_data.item_code == item_code:
                        sources_with_item.append(frappe._dict({
                            'source_name': source_name,
                            'item_crate': item_data['item_crate'],
                            'original_qty': item_data['original_qty']
                        }))
            
            # Inventory discrepancy has been detected.
            # Distributing verified quantity proportionally
            # across sources due to inability to isolate root cause.
            remaining_fulfillment_qty = fulfillment_qty
            for i, source_item in enumerate(sources_with_item):
                if i == len(sources_with_item) - 1:
                    new_qty = remaining_fulfillment_qty

                else:
                    proportion = source_item.original_qty / original_qty
                    new_qty = int(fulfillment_qty * proportion)
                    remaining_fulfillment_qty -= new_qty
                
                source_name = source_item.source_name
                if source_name not in verified_qty_updates:
                    verified_qty_updates[source_name] = {}

                verified_qty_updates[source_name][item_code] = new_qty
                
                if new_qty != source_item.original_qty:
                    all_updated_items.append(f'{item_code} in {source_name}')

        for source_name in source_names:
            source_doc = source_docs[source_name]
            source_discrepancies = []

            for item_crate in source_doc.item_crates:
                should_update = (
                    (crate_code and item_crate.crate_code == crate_code) or
                    (identifier_code and item_crate.identifier_code == identifier_code)
                )
                if should_update:
                    item_crate.verified = True
                    item_crate.verifying_user = user
                    item_crate.verified_timestamp = frappe.utils.now()

                    if (source_name in verified_qty_updates and 
                        item_crate.item_code in verified_qty_updates[source_name]):
                        new_qty = verified_qty_updates[source_name][item_crate.item_code]
                        item_crate.verified_qty = new_qty
                        
                        if new_qty != item_crate.qty:
                            source_discrepancies.append(
                                f'Item {item_crate.item_code}: {item_crate.qty} → {new_qty} '
                                f'(diff: {new_qty - item_crate.qty:+d})'
                            )
                    else:
                        item_crate.verified_qty = item_crate.qty

            if source_discrepancies:
                discrepancy_note = (
                    f'Verification discrepancies found by {user} for '
                    f'{crate_code if crate_code else identifier_code}:\n' + 
                    '\n'.join(source_discrepancies)
                )
                
                if source_doc.notes:
                    source_doc.notes += f'\n\n{discrepancy_note}'
                else:
                    source_doc.notes = discrepancy_note

            source_doc.save()

        frappe.db.commit()

        if overdelivery_items:
            overdelivery_summary = []
            for item in overdelivery_items:
                overdelivery_summary.append(
                    f"{item.item_code}: +{item.overdelivery_qty} units"
                )

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f'Error during verification: {str(e)}')

def get_transit_list(user: str):
    pick_stream.validations.validate_exists('User', user)

    stock_manager = pick_stream.utils.has_role(user, 'Stock Manager') 
    if not stock_manager:
        user_branch = pick_stream.utils.get_user_branch(user)
        target_warehouse = get_workflow_target_warehouse(user, user_branch)
        workflow_details = pick_stream.utils.get_workflow_details(target_warehouse)

        # TODO: Create global transit role rather than by workflow
        validate_role(user, workflow_details.transit_user_role)

    workflow_details = pick_stream.utils.get_workflow_details()
    workflows = workflow_details

    crate_verification_conditions = []
    identifier_verification_conditions = []

    for workflow in workflows:
        target_warehouse = workflow.target_warehouse
        
        picking_warehouse_stores = workflow.picking_warehouse_stores
        
        transit_warehouses = [
            warehouse for warehouse, store in picking_warehouse_stores.items() 
            if store != target_warehouse
        ]

        if workflow.transit_after_verification:
            crate_condition_parts = []
            identifier_condition_parts = []
            
            # Always require transit if sourced from warehouse that does not match store
            for warehouse in transit_warehouses:
                crate_condition_parts.append(f"(s.from_warehouse = '{warehouse}' AND s.to_warehouse = '{target_warehouse}' AND ic.crate_closed = 1 AND ic.verified = 1 AND ic.received = 0)")
                identifier_condition_parts.append(f"(s.from_warehouse = '{warehouse}' AND s.to_warehouse = '{target_warehouse}' AND ic.verified = 1 AND ic.received = 0)")
            
            if crate_condition_parts:
                crate_verification_conditions.append(f"({' OR '.join(crate_condition_parts)})")

            if identifier_condition_parts:
                identifier_verification_conditions.append(f"({' OR '.join(identifier_condition_parts)})")

        else:
            crate_condition_parts = []
            identifier_condition_parts = []
            
            # Always require transit if sourced from warehouse that does not match store
            for warehouse in transit_warehouses:
                crate_condition_parts.append(f"(s.from_warehouse = '{warehouse}' AND s.to_warehouse = '{target_warehouse}' AND ic.crate_closed = 1 AND ic.received = 0)")
                identifier_condition_parts.append(f"(s.from_warehouse = '{warehouse}' AND s.to_warehouse = '{target_warehouse}' AND ic.received = 0)")
            
            if crate_condition_parts:
                crate_verification_conditions.append(f"({' OR '.join(crate_condition_parts)})")

            if identifier_condition_parts:
                identifier_verification_conditions.append(f"({' OR '.join(identifier_condition_parts)})")
   
    if not crate_verification_conditions and not identifier_verification_conditions:
        raise pick_stream.exceptions.SystemError('No transit conditions found')

    crate_data = []
    identifier_data = []

    if crate_verification_conditions:
        crate_verification_clause = ' OR '.join(crate_verification_conditions)
        crate_query = f"""
            SELECT DISTINCT 
                ic.crate_code,
                s.from_warehouse,
                s.to_warehouse
            FROM `tabItem Crates` ic
            JOIN `tabSource` s ON ic.parent = s.name
            WHERE ic.parenttype = 'Source'
            AND ic.crate_code IS NOT NULL
            AND ic.crate_code != ''
            AND ic.transited = 0
            AND ({crate_verification_clause})
            ORDER BY ic.modified ASC
        """
        crate_data = frappe.db.sql(crate_query, as_dict=True)

    if identifier_verification_conditions:
        identifier_verification_clause = ' OR '.join(identifier_verification_conditions)
        identifier_query = f"""
            SELECT DISTINCT 
                ic.identifier_code,
                s.from_warehouse,
                s.to_warehouse
            FROM `tabItem Crates` ic
            JOIN `tabSource` s ON ic.parent = s.name
            WHERE ic.parenttype = 'Source'
            AND ic.identifier_code IS NOT NULL
            AND ic.identifier_code != ''
            AND ic.transited = 0
            AND ({identifier_verification_clause})
            ORDER BY ic.modified ASC
        """
        identifier_data = frappe.db.sql(identifier_query, as_dict=True)

    crate_details = []
    if crate_data:
        for row in crate_data:
            crate_details.append({
                'crate_code': row.crate_code,
                'source_warehouse': row.from_warehouse,
                'target_warehouse': row.to_warehouse
            })

    identifier_details = []
    if identifier_data:
        for row in identifier_data:
            identifier_details.append({
                'identifier_code': row.identifier_code,
                'source_warehouse': row.from_warehouse,
                'target_warehouse': row.to_warehouse
            })

    return {
        'crate_details': crate_details,
        'identifier_details': identifier_details
    }

def process_transit_request(
    user: str,
    to_warehouse:str,
    from_warehouse:str,
    crate_codes:Any=[],
    identifier_codes:Any=[]
) -> str:
    if not crate_codes and not identifier_codes:
        raise pick_stream.exceptions.SystemError('At least one of crate_codes or identifier_codes must be provided for transit processing')

    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Warehouse', to_warehouse)
    pick_stream.validations.validate_exists('Warehouse', from_warehouse)

    if crate_codes:
        crate_codes = pick_stream.utils.parse_codes(crate_codes)
        [pick_stream.validations.validate_exists('Crate', crate_code) for crate_code in crate_codes]
    
    if identifier_codes:
        identifier_codes = pick_stream.utils.parse_codes(identifier_codes)
        [pick_stream.validations.validate_exists('Pick Stream Identifier', identifier_code) for identifier_code in identifier_codes]

    workflow_details = pick_stream.utils.get_workflow_details(to_warehouse)
    
    transit_required = pick_stream.utils.check_transit_required(workflow_details.picking_warehouse_stores, from_warehouse, to_warehouse)
    if not transit_required:
        raise pick_stream.exceptions.SystemError(
            f"Transit is not required from '{from_warehouse}' to '{to_warehouse}'. Contact IT."
        )

    if not pick_stream.utils.has_role(user, 'Stock Manager'):
        validate_role(user, workflow_details.transit_user_role)

    source_list = []
    
    for crate_code in crate_codes:
        crate_doc = frappe.get_doc('Crate', crate_code)
        
        if crate_doc.to_warehouse != to_warehouse:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' destination is '{crate_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")
        
        if crate_doc.from_warehouse != from_warehouse:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' origin is '{crate_doc.from_warehouse}', not '{from_warehouse}'. Contact IT.")
        
        if not crate_doc.streams:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' has no streams. Contact IT.")

        if not crate_doc.item_groups:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' has no item groups. Contact IT.")

        filters = [
            ['crate_code', '=', crate_code],
            ['parenttype', '=', 'Source'],
            ['crate_closed', '=', 1],
            ['transited', '=', 0],
            ['received', '=', 0]
        ]

        # If workflow requires verification for transit, items must be verified
        if (workflow_details.transit_after_verification):
            filters.append(['verified', '=', 1])

        crate_sources = frappe.get_all(
            'Item Crates',
            fields=['parent'],
            filters=filters,
            pluck='parent',
            distinct=True
        )
        
        source_list.extend(crate_sources)
        
    for identifier_code in identifier_codes:
        identifier_doc = frappe.get_doc('Pick Stream Identifier', identifier_code)
        
        if identifier_doc.to_warehouse != to_warehouse:
            raise pick_stream.exceptions.SystemError(f"Identifier '{identifier_code}' destination is '{identifier_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")

        if identifier_doc.from_warehouse != from_warehouse:
            raise pick_stream.exceptions.SystemError(f"Identifier '{identifier_code}' origin is '{identifier_doc.from_warehouse}', not '{from_warehouse}'. Contact IT.")

        filters = [
            ['identifier_code', '=', identifier_code],
            ['parenttype', '=', 'Source'],
            ['transited', '=', 0],
            ['received', '=', 0]
        ]

        # If workflow requires verification for transit, items must be verified
        if (workflow_details.transit_after_verification):
            filters.append(['verified', '=', 1])

        identifier_sources = frappe.get_all(
            'Item Crates',
            fields=['parent'],
            filters=filters,
            pluck='parent',
            distinct=True
        )
        
        source_list.extend(identifier_sources)
    
    # Remove duplicates
    source_list = list(set(source_list))
    source_docs = {}
    for source in source_list:
        source_doc = frappe.get_doc('Source', source)
        source_docs[source] = source_doc

    source_stock_entries = {}

    for crate_code in crate_codes:
        for source, source_doc in source_docs.items():
            crate_items = [item for item in source_doc.item_crates if item.crate_code == crate_code]
            if not crate_items:
                continue

            if any(not item.crate_closed for item in crate_items):
                raise pick_stream.exceptions.SystemError(
                    f"Crate '{crate_code}' has unclosed items in source '{source}'. Contact IT."
                )

            # If workflow requires verification for transit, items must be verified
            if workflow_details.transit_after_verification:
                if any(not item.verified for item in crate_items):
                    raise pick_stream.exceptions.SystemError(
                        f"Crate '{crate_code}' has unverified items in source '{source}'. Contact IT."
                    )
            
            if source not in source_stock_entries:
                source_stock_entries[source] = {
                    'items': []
                }
                    
            for item_crate in crate_items:
                source_item = next(
                    (item for item in source_doc.items if item.name == item_crate.source_item), 
                    None
                )
                if not source_item:
                    raise pick_stream.exceptions.SystemError(
                        f"Source item '{item_crate.source_item}' not found in source '{source}'. Contact IT."
                    )
                
                source_stock_entries[source]['items'].append({
                    'item_code': item_crate.item_code,
                    's_warehouse': source_item.from_warehouse,
                    'qty': item_crate.qty,
                    'uom': source_item.uom,
                    'material_request': source_item.material_request,
                    'material_request_item': source_item.material_request_item,
                    'crate_code': crate_code,
                    'item_crate': item_crate.name,
                    'source': source
                })

    for identifier_code in identifier_codes:
        for source, source_doc in source_docs.items():
            identifier_items = [item for item in source_doc.item_crates if item.identifier_code == identifier_code]
            if not identifier_items:
                continue 

            # If workflow requires verification for transit, items must be verified
            if workflow_details.verification_required:
                if any(not item.verified for item in identifier_items):
                    raise pick_stream.exceptions.SystemError(
                        f"Identifier '{identifier_code}' has unverified items in source '{source}'. Contact IT."
                    )

            if source not in source_stock_entries:
                source_stock_entries[source] = {
                    'items': []
                }

            for item_crate in identifier_items:
                source_item = next(
                    (item for item in source_doc.items if item.name == item_crate.source_item), 
                    None
                )
                if not source_item:
                    raise pick_stream.exceptions.SystemError(
                        f"Source item '{item_crate.source_item}' not found in source '{source}'. Contact IT."
                    )
                
                source_stock_entries[source]['items'].append({
                    'item_code': item_crate.item_code,
                    's_warehouse': source_item.from_warehouse,
                    'qty': item_crate.qty,
                    'uom': source_item.uom,
                    'material_request': source_item.material_request,
                    'material_request_item': source_item.material_request_item,
                    'identifier_code': identifier_code,
                    'item_crate': item_crate.name,
                    'source': source
                })
            
    created_stock_entries = []
    
    frappe.db.savepoint('process_transit_request')
    
    try:
        transit_warehouse = workflow_details.transit_warehouse
        source_items_to_update = {}

        for source, stock_entry_data in source_stock_entries.items():
            items = stock_entry_data['items']
            source_doc = source_docs[source]
            
            unique_crates = list(set([item.get('crate_code') for item in items if item.get('crate_code')]))
            unique_identifiers = list(set([item.get('identifier_code') for item in items if item.get('identifier_code')]))
            total_items = len(items)
            
            codes_info = []
            if unique_crates:
                codes_info.append(f"Crates ({len(unique_crates)}): {', '.join(unique_crates)}")
            if unique_identifiers:
                codes_info.append(f"Identifiers ({len(unique_identifiers)}): {', '.join(unique_identifiers)}")
            
            stock_entry_remarks = f'Transit Transfer from {from_warehouse} to {transit_warehouse} for {", ".join(codes_info)} (Source: <a href="/app/source/{source}">{source}</a>)'
                    
            stock_entry = frappe.new_doc('Stock Entry')
            stock_entry.update({
                'stock_entry_type': 'Material Transfer',
                'purpose': 'Material Transfer',
                'from_warehouse': from_warehouse,
                'to_warehouse': transit_warehouse,
                'remarks': stock_entry_remarks,
                'add_to_transit': True
            })
            
            for item in items:
                stock_entry.append('items', {
                    'item_code': item['item_code'],
                    's_warehouse': item['s_warehouse'],
                    'qty': item['qty'],
                    'uom': item['uom'],
                    'material_request': item['material_request'],
                    'material_request_item': item['material_request_item']
                })
                
                # Track source items to be updated
                if source not in source_items_to_update:
                    source_items_to_update[source] = []
                
                source_items_to_update[source].append({
                    'item_crate': item['item_crate'],
                    'stock_entry': None,  # Will be set after stock entry creation
                    'stock_entry_detail': None  # Will be set after stock entry creation
                })
                
            stock_entry.insert()
            stock_entry.submit()

            comment_text = f'''
                <div style="line-height: 1.4;">
                    <p style="margin: 5px 0;"><strong>Route:</strong> {from_warehouse} → {transit_warehouse} → {to_warehouse}</p>
                    <p style="margin: 5px 0;"><strong>Processed by:</strong> {user}</p>
                    <p style="margin: 5px 0;"><strong>Source:</strong> <a href="/app/source/{source}">{source}</a></p>
                    <h5 style="margin: 15px 0 8px 0;">Summary:</h5>
                    <ul style="margin: 0; padding-left: 20px;">
                        {f"<li><strong>Crates:</strong> {', '.join(unique_crates)} <em>({len(unique_crates)} total)</em></li>" if unique_crates else ""}
                        {f"<li><strong>Identifiers:</strong> {', '.join(unique_identifiers)} <em>({len(unique_identifiers)} total)</em></li>" if unique_identifiers else ""}
                        <li><strong>Total Items:</strong> {total_items}</li>
                    </ul>
                </div>
            '''

            stock_entry.add_comment('Comment', comment_text)
            created_stock_entries.append(stock_entry.name)

            for i, update_item in enumerate(source_items_to_update[source]):
                if update_item['stock_entry'] is None and update_item['stock_entry_detail'] is None:
                    update_item['stock_entry'] = stock_entry.name
                    update_item['stock_entry_detail'] = stock_entry.items[i].name

        # Now process source item records that need to be updated
        for source, updates in source_items_to_update.items():
            source_doc = source_docs[source]
            
            for update_info in updates:
                for item_crate in source_doc.item_crates:
                    if item_crate.name == update_info['item_crate']:
                        item_crate.transit_stock_entry_detail = update_info['stock_entry_detail']
                        item_crate.transit_stock_entry = update_info['stock_entry']
                        item_crate.transited_timestamp = frappe.utils.now()
                        item_crate.transit_user = user
                        item_crate.transited = True
                        break
                
            source_doc.save()
            
        frappe.db.commit()
        
        return f'Transit successful. Created {len(created_stock_entries)} stock entries: {", ".join(created_stock_entries)}'
        
    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f'Error during transit: {str(e)}')

def get_receiving_list(user: str) -> Dict:
    pick_stream.validations.validate_exists('User', user)

    stock_manager = pick_stream.utils.has_role(user, 'Stock Manager') 
    if not stock_manager:
        user_branch = pick_stream.utils.get_user_branch(user)
        target_warehouse = get_workflow_target_warehouse(user, user_branch)
        workflow_details = pick_stream.utils.get_workflow_details(target_warehouse)

        validate_role(user, workflow_details.receiving_user_role)
        workflows = [workflow_details]

    else:
        workflows = pick_stream.utils.get_workflow_details()

    crate_receiving_conditions = []
    identifier_receiving_conditions = []
    
    for workflow in workflows:
        base_crate_condition = f"(s.to_warehouse = '{workflow.target_warehouse}' AND ic.crate_closed = 1 AND ic.received = 0"
        base_identifier_condition = f"(s.to_warehouse = '{workflow.target_warehouse}' AND ic.received = 0"
        
        if workflow.verification_after_receiving:
            crate_condition = f'{base_crate_condition} AND ic.verified = 0)'
            identifier_condition = f'{base_identifier_condition} AND ic.verified = 0)'

        else:
            if workflow.receiving_after_verification:
                crate_condition = f'{base_crate_condition} AND ic.verified = 1)'
                identifier_condition = f'{base_identifier_condition} AND ic.verified = 1)'

            else:
                crate_condition = f'{base_crate_condition})'
                identifier_condition = f'{base_identifier_condition})'
        
        picking_warehouse_stores = workflow.picking_warehouse_stores
        transit_conditions = []
        
        for picking_warehouse, store in picking_warehouse_stores.items():
            # Check if transit is required based on from and to warehouse
            transit_required_by_source = (store != workflow.target_warehouse)
            
            if transit_required_by_source:
                # Items from different stores must be transited first
                transit_conditions.append(f"(s.from_warehouse = '{picking_warehouse}' AND ic.transited = 1)")
            else:
                # Items from same store can be received directly
                transit_conditions.append(f"s.from_warehouse = '{picking_warehouse}'")
        
        if transit_conditions:
            transit_condition = "({})".format(' OR '.join(transit_conditions))
            crate_condition = crate_condition.rstrip(')') + f" AND {transit_condition})"
            identifier_condition = identifier_condition.rstrip(')') + f" AND {transit_condition})"
        
        crate_receiving_conditions.append(crate_condition)
        identifier_receiving_conditions.append(identifier_condition)

    if not crate_receiving_conditions:
        return {
            'crate_details': [],
            'identifier_details': []
        }

    crate_where_clause = ' OR '.join(crate_receiving_conditions)
    identifier_where_clause = ' OR '.join(identifier_receiving_conditions)
    
    crate_query = f"""
        SELECT DISTINCT 
            ic.crate_code,
            s.from_warehouse,
            s.to_warehouse
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        WHERE ic.parenttype = 'Source'
        AND ic.crate_code IS NOT NULL
        AND ic.crate_code != ''
        AND ({crate_where_clause})
        ORDER BY ic.modified ASC
    """

    identifier_query = f"""
        SELECT DISTINCT 
            ic.identifier_code,
            s.from_warehouse,
            s.to_warehouse
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        WHERE ic.parenttype = 'Source'
        AND ic.identifier_code IS NOT NULL
        AND ic.identifier_code != ''
        AND ({identifier_where_clause})
        ORDER BY ic.modified ASC
    """

    crate_data = frappe.db.sql(crate_query, as_dict=True)
    identifier_data = frappe.db.sql(identifier_query, as_dict=True)

    crate_details = []
    if crate_data:
        for row in crate_data:
            crate_details.append({
                'crate_code': row.crate_code,
                'source_warehouse': row.from_warehouse,
                'target_warehouse': row.to_warehouse
            })

    identifier_details = []
    if identifier_data:
        for row in identifier_data:
            identifier_details.append({
                'identifier_code': row.identifier_code,
                'source_warehouse': row.from_warehouse,
                'target_warehouse': row.to_warehouse
            })

    return {
        'crate_details': crate_details,
        'identifier_details': identifier_details
    }

def process_receiving_request(
    user: str,
    code: str,
    to_warehouse: str,
    from_warehouse: str,
) -> str:
    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Warehouse', to_warehouse)
    pick_stream.validations.validate_exists('Warehouse', from_warehouse)

    code = code.strip().strip('"').strip("'")
    
    crate_code = False
    identifier_code = False
    
    try:
        pick_stream.validations.validate_exists('Crate', code)
        crate_code = True
        filter_field = 'crate_code'
        code_doc = frappe.get_doc('Crate', code)

    except pick_stream.exceptions.DoesNotExistError:
        try:
            pick_stream.validations.validate_exists('Pick Stream Identifier', code)
            identifier_code = True
            filter_field = 'identifier_code'
            code_doc = frappe.get_doc('Pick Stream Identifier', code)

        except pick_stream.exceptions.DoesNotExistError:
            raise pick_stream.exceptions.DoesNotExistError(f'Code {code} not found.')
    
    workflow_details = pick_stream.utils.get_workflow_details(to_warehouse)
    if not pick_stream.utils.has_role(user, 'Stock Manager'):
        # TODO: Create global receiving role rather than basing it off workflow
        validate_role(user, workflow_details.receiving_user_role)

    # Check if transit was required based on from and to warehouse
    transit_required = pick_stream.utils.check_transit_required(workflow_details.picking_warehouse_stores, from_warehouse, to_warehouse)

    filters = [
        [filter_field, '=', code],
        ['received', '=', 0]
    ]

    if transit_required:
        # If transit is required, items must be transited
        filters.append(['transited', '=', 1])
        
    # If workflow requires verification for receiving (either before transit or after receiving), items must be verified
    if (transit_required and workflow_details.transit_after_verification) or workflow_details.receiving_after_verification:
        filters.append(['verified', '=', 1])

    # Only add crate_closed filter if it's a crate code
    if crate_code:
        filters.append(['crate_closed', '=', 1])

    source_list = frappe.get_all(
        'Item Crates',
        fields=['parent'],
        filters=filters,
        pluck='parent',
        distinct=True
    )

    if not source_list:
        if transit_required:
            if crate_code:
                if workflow_details.transit_after_verification:
                    raise pick_stream.exceptions.ValidationError(
                        f"Crate '{code}' cannot be received. Crate must be verified and transited."
                    )

                else:
                    raise pick_stream.exceptions.ValidationError(
                        f"Crate '{code}' cannot be received. Crate must be transited."
                    )
                    
            else:  # identifier_code
                if workflow_details.transit_after_verification:
                    raise pick_stream.exceptions.ValidationError(
                        f"Identifier '{code}' cannot be received. Items must be verified and transited."
                    )
                    
                else:
                    raise pick_stream.exceptions.ValidationError(
                        f"Identifier '{code}' cannot be received. Items must be transited."
                    )
                    
        else:
            if crate_code:
                raise pick_stream.exceptions.ValidationError(
                    f"Crate '{code}' cannot be received. Crate is not verified or closed."
                )
                
            else:  # identifier_code
                raise pick_stream.exceptions.ValidationError(
                    f"Identifier '{code}' cannot be received. Items are not verified."
                )
            
    if code_doc.to_warehouse != to_warehouse:
        raise pick_stream.exceptions.SystemError(f"Code '{crate_code}' destination is '{code_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")

    if code_doc.doctype == 'Crate':
        if not code_doc.streams:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' has no streams. Contact IT.")

        if not code_doc.item_groups:
            raise pick_stream.exceptions.SystemError(f"Crate '{crate_code}' has no item groups. Contact IT.")

    source_docs = {}
    for source in source_list:
        source_doc = frappe.get_doc('Source', source)
        source_docs[source] = source_doc

    transit_warehouse = workflow_details.transit_warehouse

    source_stock_entries = {}
    for source, source_doc in source_docs.items():
        if crate_code:
            code_items = [item for item in source_doc.item_crates if item.crate_code == code]
        else:  # identifier_code
            code_items = [item for item in source_doc.item_crates if item.identifier_code == code]
            
        if not code_items:
            raise pick_stream.exceptions.SystemError(f"No items found for code '{crate_code}' in source '{source}'. Contact IT.")
        
        for row in code_items:
            source_item = next((item for item in source_doc.items if item.name == row.source_item), None)
            if not source_item:
                raise pick_stream.exceptions.SystemError(f"Source item '{row.source_item}' not found in source '{source}'. Contact IT.")
            
            if source not in source_stock_entries:
                source_stock_entries[source] = {
                    'items': []
                }

            if hasattr(row, 'verified_qty') and row.verified_qty and row.verified_qty != row.qty:
                qty = row.verified_qty
            else:
                qty = row.qty

            source_stock_entries[source]['items'].append({
                'qty': qty,
                'uom': source_item.uom,
                'crate_code': code if crate_code else None,
                'identifier_code': code if identifier_code else None,
                'item_code': row.item_code,
                'source_item_name': source_item.name,
                'material_request': source_item.material_request if not transit_required else None,
                'material_request_item': source_item.material_request_item if not transit_required else None,
                'stock_entry': row.transit_stock_entry if transit_required else None,
                'stock_entry_detail': row.transit_stock_entry_detail if transit_required else None,
                'from_warehouse': row.from_warehouse if not transit_required else transit_warehouse
            })

        if transit_required and not all(
            item['stock_entry'] == source_stock_entries[source]['items'][0]['stock_entry']
            for item in source_stock_entries[source]['items']
        ):
            raise pick_stream.exceptions.SystemError(f"Stock entry discrepancy in source '{source}'. Contact IT.")

        source_stock_entries[source]['stock_entry'] = source_stock_entries[source]['items'][0]['stock_entry']

    frappe.db.savepoint('process_receiving_request')

    try:
        source_items_to_update = {}

        for source, stock_entry_data in source_stock_entries.items():
            items = stock_entry_data['items']
            source_doc = source_docs[source]
            
            stock_entry = frappe.new_doc('Stock Entry')

            if transit_required:
                actual_from_warehouse = transit_warehouse
                stock_entry_remarks = f'Receiving from {actual_from_warehouse} to {to_warehouse} for code: {code} (Source: <a href="/app/source/{source}">{source}</a>)'
                stock_entry.outgoing_stock_entry = stock_entry_data['stock_entry']

            else:
                actual_from_warehouse = from_warehouse
                stock_entry_remarks = f'Receiving from {actual_from_warehouse} to {to_warehouse} for code: {code} (Source: <a href="/app/source/{source}">{source}</a>)'

            stock_entry.update({
                'stock_entry_type': 'Material Transfer',
                'purpose': 'Material Transfer',
                'from_warehouse': actual_from_warehouse,
                'to_warehouse': to_warehouse,
                'remarks': stock_entry_remarks,
            })
            
            for item in items:
                stock_entry.append('items', {
                    'qty': item['qty'],
                    'uom': item['uom'],
                    't_warehouse': to_warehouse,
                    'item_code': item['item_code'],
                    's_warehouse': item['from_warehouse'],
                    'material_request': item['material_request'],
                    'material_request_item': item['material_request_item'],
                    'against_stock_entry': item['stock_entry'],
                    'ste_detail': item['stock_entry_detail']
                })

                # Track source items to be updated
                if source not in source_items_to_update:
                    source_items_to_update[source] = []
                
                source_items_to_update[source].append({
                    'source_item_name': item['source_item_name'],
                    'crate_code': code if crate_code else None,
                    'identifier_code': code if identifier_code else None,
                    'stock_entry': None, # Will be set after stock entry creation
                    'stock_entry_detail': None # Will be set after stock entry creation
                })

            stock_entry.insert()
            stock_entry.submit()
            stock_entry.add_comment('Info', stock_entry_remarks)

            for i, update_item in enumerate(source_items_to_update[source]):
                if update_item['stock_entry'] is None and update_item['stock_entry_detail'] is None:  # Only update if not already set
                    update_item['stock_entry'] = stock_entry.name
                    update_item['stock_entry_detail'] = stock_entry.items[i].name
        
        # Now process source item records that are to be updated
        for source, updates in source_items_to_update.items():
            source_doc = source_docs[source]
            
            for update_info in updates:
                if crate_code:
                    row = next((item for item in source_doc.item_crates
                        if item.source_item == update_info['source_item_name'] 
                        and hasattr(item, 'crate_code') 
                        and item.crate_code == update_info['crate_code']),
                        None
                    )
                else:  # identifier_code
                    row = next((item for item in source_doc.item_crates
                        if item.source_item == update_info['source_item_name'] 
                        and hasattr(item, 'identifier_code')
                        and item.identifier_code == update_info['identifier_code']),
                        None
                    )
                
                if row:
                    row.received_stock_entry_detail = update_info['stock_entry_detail']
                    row.received_stock_entry = update_info['stock_entry']
                    row.received_timestamp = frappe.utils.now()
                    row.receiving_user = user
                    row.received = True

            source_doc.save()

        if crate_code:
            # TODO: Reset Crate child tables here
            pass
            
        frappe.db.commit()

        unverified_filters = [
            [filter_field, '=', code],
            ['verified', '=', 0],
            ['received', '=', 1]
        ]

        if transit_required:
            unverified_filters.append(['transited', '=', 1])
            
        if crate_code:
            unverified_filters.append(['crate_closed', '=', 1])
            
        unverified_items = frappe.get_all(
            'Item Crates',
            filters=unverified_filters,
            limit=1
        )
        
        verification_required = len(unverified_items) > 0
        
        return f'Receiving successful for {code}', verification_required
        
    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(f'Error during receiving: {str(e)}')