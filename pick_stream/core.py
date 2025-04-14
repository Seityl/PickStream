import cups
import json
import tempfile

import frappe
from frappe import _
from frappe.utils.nestedset import get_descendants_of

from pick_stream.api_utils import exception_handler

def validate_exists(doctype:str, id:str, child:bool = False, field:str = None) -> None:
    """Raises an exception if document does not exist in the database."""
    if not child and not field:
        if not frappe.db.exists(doctype, id):
            e = frappe.exceptions.DoesNotExistError(f"{doctype} '{id}' does not exist.")
            frappe.response = exception_handler(e)   
            raise e
        return

    if not frappe.db.exists(doctype, {field:id}):
        e = frappe.exceptions.DoesNotExistError(f"{doctype} '{id}' does not exist.")
        frappe.response = exception_handler(e)   
        raise e

def validate_employee_exists(user:str) -> None:
    if not frappe.db.exists("Employee", {'user_id': user}):
        e = frappe.exceptions.DoesNotExistError(f"Employee for user '{user}' does not exist.")
        frappe.response = exception_handler(e)   
        raise e

def validate_user_assigned_to_item_group(user:str, id:str) -> None:
    validate_exists('Item Group', id)
    if not frappe.db.exists("User Group Member", {'user': user, 'parent':id}):
        e = frappe.exceptions.DoesNotExistError(f"Assignment for user '{user}' not found for item group '{id}'")
        frappe.response = exception_handler(e)   
        raise e
        
def validate_user_assigned_to_mr(mr_name:str, user:str) -> None:
    if not frappe.db.exists('ToDo', {
        'allocated_to': user,
        'reference_name': mr_name,
        'status': 'Open'
    }):
        e = frappe.exceptions.DoesNotExistError(f'ToDo for user {user} to MR {mr_name} not found')
        frappe.response = exception_handler(e)   
        raise e

def validate_scan_params(scanned_qty:int, crate_code:str, as_box:bool, as_other:bool, skipped:bool, close_crate:bool) -> None:
    if scanned_qty > 0 and skipped:
        e = frappe.exceptions.ValidationError(f"Scan can not be skipped and have a scanned qty. Contact IT.")   
        frappe.response = exception_handler(e)   
    if crate_code is not None and skipped:
        e = frappe.exceptions.ValidationError(f"Scan can not and have a crate code and be skipped. Contact IT.")   
        frappe.response = exception_handler(e)   
    if crate_code is not None and as_box:
        e = frappe.exceptions.ValidationError(f"Scan can not and have a crate code and box. Contact IT.")   
        frappe.response = exception_handler(e)   
    if crate_code is not None and as_other:
        e = frappe.exceptions.ValidationError(f"Scan can not and have a crate code and other. Contact IT.")   
        frappe.response = exception_handler(e)   
    if as_box & as_other:
        e = frappe.exceptions.ValidationError(f"Scan can not and have a box and other. Contact IT.")   
        frappe.response = exception_handler(e)   
    if as_box & close_crate or as_other & close_crate:
        e = frappe.exceptions.ValidationError(f"Scan can not close crate and have a box or other. Contact IT.")   
        frappe.response = exception_handler(e)   

def validate_scan_modes(scan_modes:dict) -> None:
    if sum(scan_modes.values()) != 1:
        e = frappe.exceptions.ValidationError(f"Exactly one scan mode must be selected. Contact IT.")   
        frappe.response = exception_handler(e)   

def validate_printer_exists(printer:str) -> None:
    printers = get_printers().printers
    if printer not in printers:
        e = frappe.exceptions.DoesNotExistError(f'Printer {printer} not found')
        frappe.response = exception_handler(e)   
        raise e

def validate_item_type(item_type:str, settings:dict) -> None:
    item_types = [item.item_type for item in settings.item_types]
    if item_type not in item_types:
        e = frappe.exceptions.DoesNotExistError(f"Item type '{item_type}' not in valid item types. Contact IT.")
        frappe.response = exception_handler(e)   
        raise e

def check_source_exists(mr_name:str, item_group:str, user:str) -> bool:
    if frappe.db.exists('Source', {
        'material_request': mr_name,
        'item_group': item_group,
        'user': user
    }):
        return True
    return False
    
def check_item_against_barcode(item_code:str, barcode:str) -> bool:
    validate_exists('Item', item_code)
    validate_exists('Item Barcode', barcode, child=True, field='barcode')
    parent = frappe.db.get_value('Item Barcode', {'barcode': barcode}, 'parent')
    if parent != item_code:
        return False
    return True

def check_crate_availability(crate_code:str) -> bool:
    """Validates crate existence then returns True if crate is available and False if crate is not"""
    validate_exists('Crate', crate_code)
    crate_status = frappe.get_value('Crate', crate_code, 'status')
    if crate_status != 'Available':
        return False
    return True

def check_material_request_item_group_in_progress(mr_name:str, user:str, item_group:str) -> dict:
    source_name = get_source_name(mr_name, item_group, user)
    if source_name:
        if frappe.db.get_value('Source', source_name, 'status') != 'Completed':
            return frappe._dict({'in_progress': True, 'source': source_name})

    return frappe._dict({'in_progress': False, 'source': source_name})
        
def assign_users_to_mr(doc:str, method:str) -> dict:
    """Assigns users to a Material Request (MR) based on item groups in the MR."""
    if not doc.custom_assign_warehouse_staff:
        return frappe.msgprint("Assignment to warehouse staff was skipped", alert=True)

    try:
        mr_name = doc.name
        mr_doc = frappe.get_doc('Material Request', mr_name)
        # Default to King George to avoid situations where source warehouse is not set
        # Source should be explicitly set if is goods are being picked from Mega 
        match mr_doc.set_from_warehouse:
            case 'KG Warehouse - JP':
                branch = 'King George'
            case 'JP Mega - JP':
                branch = 'JP Mega'
            case _:
                branch = 'King George'

        mr_item_groups = {item.item_group for item in mr_doc.items}
        fulfillment_users = frappe.db.sql_list(
            """
            SELECT DISTINCT ugm.user
            FROM `tabUser Group Member` ugm
            JOIN `tabUser Group` ug ON ug.name = ugm.parent
            JOIN `tabEmployee` emp ON emp.user_id = ugm.user
            WHERE ug.name IN %(mr_item_groups)s
            AND emp.branch = %(branch)s
            AND ug.custom_is_item_group == 1
            """, {
                'mr_item_groups': list(mr_item_groups),
                'branch': branch
            }
        )

        if not fulfillment_users:
            return frappe.msgprint(f"No fulfillment users found for Material Request {mr_name} in branch {branch}", alert=True)

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
                        frappe.msgprint(f"Open ToDo already exists for user {user} on Material Request {mr_name}.", alert=True)

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
                        frappe.msgprint(f"Reopened ToDo {todo_doc.name} as the user {user} is now required to take action on Material Request {mr_name}.", alert=True)
                    
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
                    frappe.msgprint(f"Created ToDo for user {user} on Material Request {mr_name}.", alert=True)

            except Exception as e:
                frappe.msgprint(f"Error processing ToDo for User {user}", alert=True)
                frappe.log_error(
                    message=f'Error processing ToDo for User {user}: {str(e)}',
                    title='[Pick Stream] Error in assign_users_to_mr()',
                    reference_name=mr_name
                )
                continue
        
    except Exception as e:
        frappe.msgprint(f"Error assigning users to MR: {mr_name}", alert=True)
        frappe.log_error(
            message=f'Error assigning users to MR: {mr_name}: {str(e)}',
            title='[Pick Stream] Error in assign_users_to_mr()',
            reference_name=mr_name
        )

def get_printers() -> dict:
    out = frappe._dict({'exc': None})
    settings = get_pick_stream_settings()
    try:
        conn = cups.Connection(host=settings.host, port=settings.port)
        out.printers = list(conn.getPrinters().keys())
        return out
    except RuntimeError as e:
        out.exc =  f"Error connecting to CUPS: {e}"
        return out
    except Exception as e:
        out.exc =  f"Error connecting to CUPS: {e}"
        return out

def get_mr_item_groups_for_user(mr_name:str, user:str) -> list:
    try:
        user_item_groups = get_assigned_item_groups(user)
        mr_groups = frappe.get_all(
            'Material Request Item',
            filters = {'parent': mr_name, 'item_group': ['in', user_item_groups]},
            pluck = 'item_group',
            distinct = True
        )
        for mr_group in mr_groups:
            validate_user_assigned_to_item_group(user, mr_group)
        return mr_groups

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

def get_mr_available_item_groups_for_user(mr_name:str, user:str) -> list:
    """Returns item groups which don't already have completed source for material request"""
    validate_user_assigned_to_mr(mr_name, user)
    out = []
    user_item_groups = get_mr_item_groups_for_user(mr_name, user)
    for item_group in user_item_groups:
        if frappe.db.exists('Source', {
            'item_group': item_group, 
            'material_request': mr_name,
            'status': ['=', 'Completed']
        }):
            out.append({'name': item_group, 'available': False})
        else:
            out.append({'name': item_group, 'available': True})
    return out            

def get_user_material_requests(user:str) -> dict:
    validate_exists('User', user)

    settings = get_pick_stream_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse

    user_item_groups = get_assigned_item_groups(user)
    user_branch = get_user_branch(user)
    warehouse_group = get_warehouse_group(user, user_branch)
    child_warehouses = get_child_warehouses(warehouse_group)

    try:
        mr_list = frappe.db.sql(
            """
                SELECT 
                    mr.name,
                    mr.set_warehouse AS target_warehouse,
                    COALESCE(mr.set_from_warehouse, %(default_set_from_warehouse)s) AS source_warehouse,
                    td.status
                FROM `tabToDo` td
                INNER JOIN `tabMaterial Request` mr
                    ON td.reference_name = mr.name
                WHERE
                    td.allocated_to = %(user)s
                    AND td.status = 'Open'
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
                ORDER BY mr.creation ASC
            """, {
                'user': user,
                'user_item_groups': tuple(user_item_groups),
                'child_warehouses': tuple(child_warehouses),
                'default_set_from_warehouse': default_set_from_warehouse
            },
            as_dict = True
        ) or {}

        if not mr_list:
            return []
        for mr in mr_list:
            mr_name = mr.get('name')
            availability = get_mr_available_item_groups_for_user(mr_name, user)
            mr['item_group_availability'] = availability
        return mr_list
        

    except Exception as e:
        return exception_handler(e)

def get_material_request_item_groups_view_details(mr_name:str, user:str) -> dict:
    validate_exists('User', user)
    validate_exists('Material Request', mr_name)
    validate_user_assigned_to_mr(mr_name, user)

    settings = get_pick_stream_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse

    out = frappe.db.sql(
        """
            SELECT 
                mr.name AS mr_name,
                mr.set_warehouse AS target_warehouse,
                COALESCE(mr.set_from_warehouse, %(default_set_from_warehouse)s) AS source_warehouse
            FROM `tabMaterial Request` mr
            WHERE
                mr.name = %(mr_name)s
        """, { 
            'mr_name': mr_name,
            'default_set_from_warehouse': default_set_from_warehouse
        },
        as_dict=True
    )[0]
    out['item_group_availability'] = get_mr_available_item_groups_for_user(mr_name, user)
    return out

def get_material_request_item_group_view_details(mr_name:str, user:str, item_group:str) -> dict:
    validate_exists('User', user)
    validate_exists('Material Request', mr_name)
    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, item_group)

    check = check_material_request_item_group_in_progress(mr_name, user, item_group)
    
    if check.in_progress:
        crate_code = get_relevant_source_crate_code(check.source)
        return frappe._dict({'in_progress': True, 'crate_code': crate_code})
        
    try:
        out = frappe.db.sql(
            """
             SELECT 
        mr.name,
        mr.set_warehouse AS target_warehouse,
        mr.set_from_warehouse AS source_warehouse,
        COALESCE(
            (
                SELECT JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'crate_code', crates.crate_code,
                        'item_group', crates.item_group,
                        'status', crates.status
                    )
                )
                FROM (
                    SELECT DISTINCT
                        ps.crate_code,
                        ps.item_group,
                        ps.status
                    FROM `tabStream` ps
                    WHERE 
                        ps.material_request =  %(mr_name)s
                        AND (ps.crate_code IS NOT NULL OR ps.item_group IS NOT NULL OR ps.status IS NOT NULL)
                ) AS crates
            ),
            JSON_ARRAY()
        ) AS crates
    FROM `tabMaterial Request` mr
    WHERE
        mr.name = %(mr_name)s
            """, 
            {
                'mr_name': mr_name
            },
            as_dict=True
        )[0] or {}

        if out:
            out['item_group'] = item_group
            out['crates'] = json.loads(out.get('crates', '[]'))
            
        return out
    
    except Exception as e:
        return exception_handler(e)

def get_material_request_items_details(mr_name:str, user:str, selected_item_group:str) -> dict:
    validate_exists('User', user)
    validate_exists('Material Request', mr_name)
    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, selected_item_group)
    try:
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

    except Exception as e:
        return exception_handler(e)

def get_assigned_item_groups(user:str) -> list:
    """Get unique item groups assigned to a user through User Group relationships."""
    user_item_groups = frappe.get_all(
        'User Group',
        filters={
            'custom_is_item_group': 1,
            'name': ['in', frappe.get_all(
                'User Group Member',
                filters={'parenttype': 'User Group', 'user': user},
                pluck='parent'
            )]
        },
        fields=['name'],
        pluck='name',
        distinct=True
    )
    if not user_item_groups:
        e = frappe.exceptions.DoesNotExistError(f"Item Group assignment not found for user '{user}'. Contact Supervisor.")
        frappe.response = exception_handler(e)
        raise e

    return user_item_groups

def get_user_branch(user:str) -> str:
    """Returns employee branch based on user"""
    validate_employee_exists(user)
    branch = frappe.db.get_value('Employee', {'user_id': user}, ['branch'])
    if not branch:
        e = frappe.exceptions.DoesNotExistError(f"Employee branch for user '{user}' is not set. Contact Supervisor.")
        frappe.response = exception_handler(e)   
        raise e
    return branch

def get_warehouse_group(user:str, user_branch:str):
    match user_branch:
        case 'King George':
            return 'KG Warehouse - JP'
        case 'JP Mega':
            return 'JP Mega - JP'
        case _:
            e = frappe.exceptions.DoesNotExistError(f"Employee for user '{user}' branch is not set to 'King George' or 'JP Mega'.")
            frappe.response = exception_handler(e)   
            raise e

def get_child_warehouses(parent_warehouse:str) -> list:
    """Get all descendant warehouses of specified parent"""
    return get_descendants_of("Warehouse", parent_warehouse)

def get_source_name(mr_name:str, item_group:str, user:str) -> str:
    return frappe.db.get_value('Source', {
        'material_request': mr_name,
        'item_group': item_group,
        'user': user
    }, 'name') or ''

def get_material_request_picking_view_details(mr_name:str, user:str, item_group:str, crate_code:str) -> dict:
    if check_source_exists(mr_name, item_group, user):
        source_name = get_source_name(mr_name, item_group, user)
        return get_relevant_source_item(source_name, crate_code)

    else:
        source = create_source(mr_name, item_group, user, crate_code)
        return get_relevant_source_item(source.name, crate_code)

def get_relevant_source_item(source_name:str, crate_code:str) -> dict:
    out = frappe._dict()
    doc = frappe.get_doc('Source', source_name)
    for item in doc.items:
        if not item.scanned and not item.skipped:
            out.crate_code = crate_code
            out.item_code = item.item_code
            out.description = item.description
            out.requested_qty = item.requested_qty
            out.uom = item.uom
            out.from_warehouse = item.from_warehouse
            return out

    out.complete = True
    return out

def get_pick_stream_settings() -> dict:
    return frappe.get_doc('Pick Stream Settings') 

def get_relevant_source_crate_code(source:str) -> str:
    doc = frappe.get_doc('Source', source)
    for item in reversed(doc.items):
        if item.scanned and item.crate_code:
            return item.crate_code
        
def get_item_identifier(item_code:str, type:str, user:str, mr_name:str, from_warehouse:str, to_warehouse:str) -> str:
    identifier = frappe.new_doc('Pick Stream Identifier')
    identifier.update({
        'item_code': item_code,
        'item_type': type.lower(),
        'user': user,
        'material_request': mr_name,
        'from_warehouse': from_warehouse,
        'to_warehouse': to_warehouse
    })
    try:
        identifier.db_insert()
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e
    
    return str(identifier.name)

def get_crate_status_from_stream(status:str) -> str:
    match status:
        case 'Picking':
            return'Picking'
        case 'Waiting':
            return'Waiting'
        case 'In Transit':
            return'In Transit'
        case 'Verifying':
            return'Verifying'
        case 'Completed':
            return'Waiting'
    
def create_source(mr_name:str, item_group:str, user:str, crate_code:str) -> dict:
    source = frappe.new_doc('Source')
    items = get_material_request_items_details(mr_name, user, item_group)

    settings = get_pick_stream_settings()
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

    frappe.db.savepoint('sp2')

    try:
        source.insert()
        # Set first item's crate code here to prevent error where source was created but scan was not submitted
        # Which would return a null crate code for picking view
        for item in source.items:
            item.crate_code = crate_code
            break
        source.save()
        frappe.db.commit()
        return source

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def create_stream(source:dict, crate_code:str) -> dict:
    user = source.user
    material_request = source.material_request
    item_group = source.item_group
    from_warehouse = source.from_warehouse
    to_warehouse = source.to_warehouse

    validate_exists('User', user)
    validate_exists('Material Request', material_request)
    validate_user_assigned_to_mr(material_request, user)
    validate_user_assigned_to_item_group(user, item_group)
    
    stream = frappe.new_doc('Stream')
    stream.update({
        'material_request': material_request,
        'from_warehouse': from_warehouse,
        'to_warehouse': to_warehouse,
        'crate_code': crate_code,
        'item_group': item_group,
        'status': 'Picking',
        'source': source.name,
        'user': user
    })

    crate_available = check_crate_availability(crate_code) 
    if not crate_available:
        e = frappe.exceptions.ValidationError(f"Crate '{crate_code}' is not available. Contact Supervisor.")
        frappe.response = exception_handler(e)   

    items = source.items
    for item in items:
        if not item.crate_code or item.skipped:
            continue
        item.name = None
        item.source = source.name
        stream.append('items', item)

    frappe.db.savepoint('sp3')

    try:
        stream.insert()
        frappe.db.commit()
        return stream

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def create_crate_log(crate:dict) -> dict:
    crate_code = crate.name
    from_warehouse = crate.from_warehouse
    to_warehouse = crate.to_warehouse
    stream = crate.stream

    crate_log = frappe.new_doc('Crate Log')
    crate_log.update({
        'crate_code': crate_code,
        'stream': stream,
        'to_warehouse': to_warehouse,
        'from_warehouse': from_warehouse,
        'picked_by': frappe.db.get_value('Stream', stream, 'user')
    })

    items = crate.items
    for item in items:
        item.name = None
        crate_log.append('items', item)
        
    frappe.db.savepoint('sp4')

    try:
        crate_log.insert()
        frappe.db.commit()
        return crate_log

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def update_stream(source:dict, stream_name:str, status:str=None) -> dict:
    stream = frappe.get_doc('Stream', stream_name)
    if status:
        stream.update({'status': status})
    relevant_items = {item for item in source.items if item.crate_code == stream.crate_code}
    stream.delete_key('items')

    for item in relevant_items:
        item.name = None
        item.source = source.name
        stream.append('items', item)

    frappe.db.savepoint('sp5')

    try:
        stream.save()
        frappe.db.commit()
        return stream

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def update_crate(stream:dict) -> dict:
    crate = frappe.get_doc('Crate', stream.crate_code)
    status = get_crate_status_from_stream(stream.status)
    crate.update({
        'status': status,
        'stream': stream.name,
        'item_group': stream.item_group,
        'from_warehouse': stream.from_warehouse,
        'to_warehouse': stream.to_warehouse
    })

    crate.delete_key('items')
    for item in stream.items:
        item.name = None
        crate.append('items', item)

    frappe.db.savepoint('sp6')

    try:
        crate.save()
        frappe.db.commit()
        return crate

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def update_crate_log(crate: dict) -> dict:
    crate_log = frappe.get_doc('Crate Log', {'stream': crate.stream})
    crate_log.delete_key('items')
    for item in crate.items:
        item.name = None
        crate_log.append('items', item)

    frappe.db.savepoint('sp7')

    try:
        crate_log.save()
        frappe.db.commit()
        return crate_log

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def process_scan_details(
        user:str,
        mr_name:str,
        item_code:str,
        item_group:str,
        scanned_qty:int,
        crate_code:str = None,
        as_box:bool = False,
        as_other:bool = False,
        skipped:bool = False,
        close_crate:bool = False
    ) -> dict:
    validate_scan_params(scanned_qty, crate_code, as_box, as_other, skipped, close_crate)
        
    out = frappe._dict({'success': True})

    if crate_code:
        validate_exists('Crate', crate_code)

    validate_exists('User', user)
    validate_exists('Item', item_code)
    validate_exists('Material Request', mr_name)

    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, item_group)

    source_name = get_source_name(mr_name, item_group, user)
    if not source_name:
        out.success = False
        out.message = f'Source based on material request {mr_name} for user {user} and item_group {item_group} does not exist.'
        return out

    relevant_item = get_relevant_source_item(source_name, crate_code) 
    if relevant_item.item_code != item_code:
        out.success = False
        out.message = f'Scanned item {item_code} does not match relevant item {relevant_item.item_code}.'
        return out

    doc = frappe.get_doc('Source', source_name)

    scan_modes = frappe._dict({
        'crate': bool(crate_code),
        'as_box': as_box,
        'as_other': as_other,
        'skipped': skipped,
        'close_crate': close_crate,
    })

    # validate_scan_modes(scan_modes)

    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse')
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')
    
    if scan_modes.crate:
        out.message = process_scan_as_crate(doc, crate_code, item_code, scanned_qty)
    elif scan_modes.as_box:
        identifier_code = get_item_identifier(item_code, 'box', user, mr_name, from_warehouse, to_warehouse)
        out.message = process_scan_as_box(doc, identifier_code, item_code, scanned_qty)
    elif scan_modes.as_other:
        identifier_code = get_item_identifier(item_code, 'other', user, mr_name, from_warehouse, to_warehouse)
        out.message = process_scan_as_other(doc, identifier_code, item_code, scanned_qty)
    elif scan_modes.skipped:
        out.message = process_scan_as_skip(doc, item_code)
    elif scan_modes.close_crate:
        out.message = process_scan_as_close_crate(doc, crate_code, item_code, scanned_qty, skipped)

    frappe.db.savepoint('sp1')

    try:
        doc.save()
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e
        
    return out

def process_scan_as_crate(source:dict, crate_code:str, item_code:str, scanned_qty:int) -> str:
    for item in source.items:
        if item.item_code == item_code:
            item.scanned = 1
            item.crate_code = crate_code
            item.scanned_qty = scanned_qty
            return f'Scanned {scanned_qty} {item.uom} for item {item_code} into crate {crate_code}'

def process_scan_as_box(source:dict, identifier_code:str, item_code:str, scanned_qty:int) -> str:
    for item in source.items:
        if item.item_code == item_code:
            item.identifier_code = identifier_code
            item.scanned_qty = scanned_qty
            item.is_box_item = 1
            item.scanned = 1
            return f'Scanned {scanned_qty} {item.uom} for item {item_code} assigned to box {identifier_code}'

def process_scan_as_other(source:dict, identifier_code:str, item_code:str, scanned_qty:int) -> str:
    for item in source.items:
        if item.item_code == item_code:
            item.scanned = 1
            item.is_other_item = 1
            item.scanned_qty = scanned_qty
            item.identifier_code = identifier_code
            return f'Scanned {scanned_qty} {item.uom} for item {item_code} assigned to identifier {identifier_code}'

def process_scan_as_skip(source:dict, item_code:str) -> str:
    for item in source.items:
        if item.item_code == item_code:
            item.skipped = 1
            return f'Skipped item {item_code}'

def process_scan_as_close_crate(source:dict, crate_code:str, item_code:str, scanned_qty:int, skipped:bool=False) -> str:
    for item in source.items:
        if item.item_code == item_code:
            if skipped:
                item.skipped = skipped
            item.scanned = 1
            item.crate_code = crate_code
            item.scanned_qty = scanned_qty
            
            close_crate(source, crate_code)
            
            return f'Scanned {scanned_qty} {item.uom} for item {item_code} into crate {crate_code}'
            
def close_crate(source:dict, crate_code:str) -> None:
    for item in source.items:
        if item.crate_code == crate_code:
            item.closed = 1

def process_print_request(item_code:str, item_type:str, user:str, mr_name:str, printer:str) -> dict:
    settings = get_pick_stream_settings()

    validate_exists('User', user)
    validate_exists('Item', item_code)
    validate_exists('Material Request', mr_name)
    
    validate_printer_exists(printer)
    validate_item_type(item_type, settings)
    
    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')
    print_job = print_barcode(item_code, item_type, from_warehouse, to_warehouse, mr_name, user, printer, settings)
    return print_job
        
def print_barcode(item_code:str, item_type:str, from_warehouse:str, to_warehouse:str, mr_name:str, user:str, printer:str, settings:dict) -> dict:
    out = frappe._dict({'exc': None})
    item_id = get_item_identifier(item_code, item_type, user, mr_name, from_warehouse, to_warehouse)
    ################################################## ZPL ##################################################
    # Docs: https://supportcommunity.zebra.com/s/article/ZPL-Command-Information-and-DetailsV2?language=en_US
    # Generator: https://zplgenerator.com/
    zpl_code = (
        # Start label format
        '^XA\n'

        # Field for 'JP Element'
        "^FXfield for the element 'JP Element'"
        '^FO216,24,2'
        '^FWN'
        f'^A40,40^FD{item_code}^FS'
        
        # Field for 'MR Element'
        "^FXfield for the element 'MR Element'\n"
        '^FO24,64,2\n'
        '^FWN\n'
        f'^A24,40^FDMR:{mr_name}^FS\n'

        # Field for 'F Element'
        "^FXfield for the element 'F Element'\n"
        '^FO24,112,2\n'
        '^FWN\n'
        f'^A16,40^FDF:{from_warehouse}^FS\n'

        # Field for 'T Element'
        "^FXfield for the element 'T Element'\n"
        '^FO24,160,2\n'
        '^FWN\n'
        f'^A24,40^FDT:{to_warehouse}^FS\n'

        # Field for 'Barcode Element'
        "^FXfield for the element 'Barcode Element'\n"
        '^FO88,248,2\n'
        '^FWN\n'
        '^BY3.2,2,120\n'
        f'^BCN,120,Y,N^FD{item_id}^FS\n'
        
        # Field for 'U Element'
        "^FXfield for the element 'U Element'\n"
        '^FO24,208,2\n'
        '^FWN\n'
        f'^A24,40^FDU:{user}^FS\n'

        # End label format
        '^XZ\n'
    )

    try:
        host, port = settings.host, settings.port
        
        cups.setServer(host)
        cups.setPort(port)
        conn = cups.Connection(host=host, port=port)

        # Write the ZPL code to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zpl') as tmp_file:
            tmp_file.write(zpl_code.encode('utf-8'))
            tmp_file.flush()
            temp_file_path = tmp_file.name

        job_options = {
            'document-format': 'application/vnd.cups-raw',
            'media': 'Custom.3x2in',
            'scaling': '75',
            'fit-to-page': 'True'
        }

        job_name = f'{item_type} Identifier Print Job'
        conn.printFile(printer, temp_file_path, job_name, job_options)

        out.message = 'Print Job Submitted Successfully'
        return out
        
    except RuntimeError as e:
        out.exc =  f"Error connecting to CUPS: {e}"
        return out

    except Exception as e:
        out.exc =  f"Error connecting to CUPS: {e}"
        return out
