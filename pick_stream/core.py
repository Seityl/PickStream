import cups
import json
import tempfile

import frappe
from frappe import _
from frappe.utils import strip_html
from frappe.utils.nestedset import get_descendants_of

import pick_stream.exceptions

def validate_role(user:str, role:str) -> None:
    """Raises an exception if user does not have a specific role"""
    if not frappe.db.exists('Has Role', {'parent': user, 'role': role}):
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not allowed to verify. Contact Supervisor.")
    
def validate_exists(doctype:str, id:str, child:bool = False, field:str = None) -> None:
    """Raises an exception if document does not exist in the database."""
    if not child and not field:
        if not frappe.db.exists(doctype, id):
            raise pick_stream.exceptions.DoesNotExistError(f"{doctype} '{id}' does not exist.")
        return

    if not frappe.db.exists(doctype, {field:id}):
        raise pick_stream.exceptions.DoesNotExistError(f"{doctype} '{id}' does not exist.")

def validate_employee_exists(user:str) -> None:
    if not frappe.db.exists('Employee', {'user_id': user}):
        raise pick_stream.exceptions.DoesNotExistError(f"Employee for user '{user}' does not exist. Contact HR Department.")

def validate_user_assigned_to_item_group(user:str, id:str) -> None:
    validate_exists('Item Group', id)
    if not frappe.db.exists("User Group Member", {'user': user, 'parent':id}):
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not assigned to item group '{id}'. Contact Supervisor.")
        
def validate_user_assigned_to_mr(mr_name:str, user:str) -> None:
    if not frappe.db.exists('ToDo', {
        'allocated_to': user,
        'reference_name': mr_name,
        'status': 'Open'
    }):
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not assigned to Material Request '{mr_name}'. Contact Supervisor.")

def validate_scan_params(scanned_qty: int, crate_code: str, as_box: bool, as_other: bool, skipped: bool, crates: bool) -> None:
    active_flags = sum(1 for flag in [as_box, as_other, skipped, crates, crate_code is not None] if flag)
    if active_flags < 1:
        raise pick_stream.exceptions.ValidationError('Scan action must be selected. Contact IT.')
    if active_flags > 1:
        raise pick_stream.exceptions.ValidationError('Only one scan action allowed. Contact IT.')
    
    if skipped:
        if scanned_qty > 0:
            raise pick_stream.exceptions.ValidationError('Cannot skip with quantity. Contact IT.')
        if crate_code is not None:
            raise pick_stream.exceptions.ValidationError('Cannot skip with crate code. Contact IT.')
    
    if crate_code is not None:
        if as_box:
            raise pick_stream.exceptions.ValidationError('Cannot scan both crate code and box. Contact IT.')
        if as_other:
            raise pick_stream.exceptions.ValidationError('Cannot scan both crate code and other. Contact IT.')
    
    if crates:
        if as_box or as_other:
            raise pick_stream.exceptions.ValidationError('Cannot scan crates with box/other. Contact IT.')
        if crate_code:
            raise pick_stream.exceptions.ValidationError('Cannot scan crates and crate. Contact IT.')
        if scanned_qty > 0:
            raise pick_stream.exceptions.ValidationError('Cannot scan crates with scanned quantity. Contact IT.')

def validate_printer_exists(printer:str) -> None:
    printers = get_printers()
    if printer not in printers:
        raise pick_stream.exceptions.ValidationError(f"Printer '{printer}' not found exist. Contact IT.")

def validate_item_type(item_type:str, settings:dict) -> None:
    item_types = [item.item_type for item in settings.item_types]
    if item_type not in item_types:
        raise pick_stream.exceptions.ValidationError(f"Item type '{item_type}' not in valid item types. Contact IT.")

def validate_user_assigned_to_crate(user:str, crate_code:str) -> None:
    user_streams = frappe.db.get_all('Stream',
        filters={'user': user, 'status': 'Picking'},
        fields=['crate_code']
    )

    if not user_streams:
        raise pick_stream.exceptions.ValidationError(f'User {user} did not pick crate {crate_code}. Contact IT.')
        
    if not any(stream.crate_code == crate_code for stream in user_streams):
        raise pick_stream.exceptions.ValidationError(f'User {user} did not pick crate {crate_code}. Contact IT.')

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

def check_crate_availability(crate_code: str, user: str, from_stream: bool = False) -> bool:
    validate_exists('Crate', crate_code)
    if not from_stream: 
        validate_exists('User', user)
        
    crate_status = frappe.db.get_value('Crate', crate_code, 'status')
    
    if crate_status != 'Available':
        crate_picking_user = frappe.get_value('Crate', crate_code, 'picking_user')
        if not crate_picking_user:
            raise pick_stream.exceptions.ValidationError((
                f"Crate '{crate_code}' is not available and has no picking user. "
                "Report error to IT."
            ))
        
        if crate_status == 'Picking' and crate_picking_user != user:
            raise pick_stream.exceptions.ValidationError((
                f"Crate '{crate_code}' is already in use by {crate_picking_user}. "
                "Contact IT if you believe this is an error."
            ))

        if crate_status == 'Picking' and crate_picking_user == user:
            return True

        return False
    
    return True

def check_material_request_item_group_in_progress(mr_name:str, item_group:str) -> dict:
    source_name = get_source_name(mr_name, item_group)
    if source_name:
        if frappe.db.get_value('Source', source_name, 'status') != 'Completed':
            return frappe._dict({'in_progress': True, 'source': source_name})

    return frappe._dict({'in_progress': False, 'source': source_name})

def has_role(user:str, role:str) -> bool:
    if frappe.db.exists('Has Role', {'parent': user, 'role': role}):
        return True

    return False

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
            AND ug.custom_is_item_group = '1'
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
    settings = get_pick_stream_settings()
    try:
        conn = cups.Connection(host=settings.host, port=settings.port)
        return list(conn.getPrinters().keys())

    except RuntimeError as e:
        raise pick_stream.exceptions.ValidationError(f'Error connecting to CUPS: {e}')

    except Exception as e:
        raise pick_stream.exceptions.ValidationError(f'Error connecting to CUPS: {e}')

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
        raise pick_stream.exceptions.ValidationError(f'Error getting item groups for user: {e}')

def get_mr_available_item_groups_for_user(
    mr_name:str,
    user:str,
    child_warehouses:list=None
) -> list:
    """Returns item groups which don't already have completed source for material request"""
    validate_user_assigned_to_mr(mr_name, user)
    out = []
    user_item_groups = get_mr_item_groups_for_user(mr_name, user)

    if not child_warehouses:
        user_branch = get_user_branch(user)
        warehouse_group = get_warehouse_group(user, user_branch)
        child_warehouses = get_child_warehouses(warehouse_group)

    for item_group in user_item_groups:
        if frappe.db.exists('Source', {
            'item_group': item_group, 
            'material_request': mr_name,
            'status': ['=', 'Completed']
        }):
            out.append(frappe._dict({'name': item_group, 'available': False, 'reason': 'Completed'}))
            continue
            
        if not bool(frappe.db.sql(
            """
                SELECT 1
                FROM `tabMaterial Request Item` mri
                INNER JOIN `tabItem` item ON mri.item_code = item.name
                INNER JOIN `tabBin` bin ON mri.item_code = bin.item_code
                WHERE mri.parent = %(mr_name)s
                AND item.item_group IN %(user_item_groups)s
                AND bin.actual_qty >= 1
                AND bin.warehouse IN %(child_warehouses)s
                AND (mri.stock_qty > COALESCE(mri.ordered_qty, 0))
                LIMIT 1
            """,
            {
                "mr_name": mr_name,
                "user_item_groups": tuple(user_item_groups),
                "child_warehouses": tuple(child_warehouses)
            },
            as_dict=False
        )):
            out.append(frappe._dict({'name': item_group, 'available': False, 'reason': 'No Available Stock'}))
            continue

        out.append(frappe._dict({'name': item_group, 'available': True}))

    return out            

def get_user_material_requests(user:str) -> list:
    validate_exists('User', user)

    settings = get_pick_stream_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse

    user_item_groups = get_assigned_item_groups(user)
    user_branch = get_user_branch(user)
    warehouse_group = get_warehouse_group(user, user_branch)
    child_warehouses = get_child_warehouses(warehouse_group)

    try:
        if user_branch == 'King George':
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
                        mr.docstatus = 1
                        AND td.allocated_to = %(user)s
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
            ) or []

        # TODO: Account for JP Mega 
        elif user_branch == 'JP Mega':
            return []
        
        if not mr_list:
            return []
        
        filtered_mr_list = []

        for mr in mr_list:
            mr_name = mr.get('name')
            availability = get_mr_available_item_groups_for_user(
                mr_name,
                user,
                child_warehouses=child_warehouses
            )
            if availability is None:
                continue
            
            available_groups = [group for group in availability if group.available]

            if available_groups:
                mr['item_group_availability'] = available_groups
                filtered_mr_list.append(mr)

        return filtered_mr_list
        
    except Exception as e:
        raise pick_stream.exceptions.ValidationError(f"Error retrieving Material Requests for user '{user}': {str(e)}")

def get_material_request_item_groups_view_details(mr_name: str, user: str) -> dict:
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
        """,
        {
            'mr_name': mr_name,
            'default_set_from_warehouse': default_set_from_warehouse
        },
        as_dict=True
    )[0]

    out['item_group_availability'] = get_mr_available_item_groups_for_user(mr_name, user)

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
        item_group['item_count'] = get_material_request_item_group_item_quantity(mr_name, item_group['name'], user)

    return out

def get_material_request_item_group_item_quantity(mr_name: str, item_group: str, user: str) -> dict:
    if not check_source_exists(mr_name, item_group, user):
        out = frappe._dict({'completed': 0})
        user_branch = get_user_branch(user)
        warehouse_group = get_warehouse_group(user, user_branch)
        child_warehouses = get_child_warehouses(warehouse_group)
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
    
    source_name = get_source_name(mr_name, item_group)
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

def get_material_request_item_group_view_details(mr_name:str, user:str, item_group:str) -> dict:
    validate_exists('User', user)
    validate_exists('Material Request', mr_name)
    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, item_group)

    check = check_material_request_item_group_in_progress(mr_name, item_group)
    
    if check.in_progress:
        crate_code = get_relevant_source_crate_code(check.source)
        return frappe._dict({'in_progress': True, 'crate_code': crate_code})
        
    try:
        settings = get_pick_stream_settings()
        default_set_from_warehouse = settings.default_set_from_warehouse

        return frappe.db.sql(
            """
            SELECT 
                mr.name,
                mr.set_warehouse AS target_warehouse,
                COALESCE(mr.set_from_warehouse, %(default_set_from_warehouse)s) AS source_warehouse
            FROM `tabMaterial Request` mr
            WHERE
                mr.name = %(mr_name)s
            """, 
            {
                'default_set_from_warehouse': default_set_from_warehouse,
                'mr_name': mr_name,
            },
            as_dict=True
        )[0] or {}
    
    except Exception as e:
        raise pick_stream.exceptions.ValidationError(f"Error retrieving Material Request Item Group View details for user '{user}': {str(e)}")

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
        raise pick_stream.exceptions.ValidationError(f'Error getting material request item details: {e}')

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
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not assigned to any item group. Contact Supervisor.")

    return user_item_groups

def get_user_branch(user:str) -> str:
    """Returns employee branch based on user"""
    validate_employee_exists(user)
    branch = frappe.db.get_value('Employee', {'user_id': user}, ['branch'])
    if not branch:
        raise pick_stream.exceptions.ValidationError(f"Employee branch for user '{user}' is not set. Contact HR Department.")
    return branch

def get_warehouse_group(user:str, user_branch:str) -> str:
    match user_branch:
        case 'King George':
            return 'KG Warehouse - JP'
        case 'JP Mega':
            return 'JP Mega - JP'
        case _:
            raise pick_stream.exceptions.ValidationError(f"Employee for user '{user}' branch is not set to 'King George' or 'JP Mega'. Contact HR Department.")

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

def get_child_warehouses(parent_warehouse:str) -> list:
    """Get all descendant warehouses of specified parent"""
    return get_descendants_of('Warehouse', parent_warehouse)

def get_source_name(mr_name:str, item_group:str) -> str:
    return frappe.db.get_value('Source', {
        'material_request': mr_name,
        'item_group': item_group
    }, 'name') or ''

def get_material_request_picking_view_details(mr_name:str, user:str, item_group:str) -> dict:
    if check_source_exists(mr_name, item_group, user):
        source_name = get_source_name(mr_name, item_group)
        return get_relevant_source_item(source_name)
    else:
        source = create_source(mr_name, item_group, user)
        return get_relevant_source_item(source.name)

def get_relevant_source_item(source_name:str) -> dict:
    out = frappe._dict()
    doc = frappe.get_doc('Source', source_name)
    for item in doc.items:
        if not item.scanned and not item.skipped:
            out.item_code = item.item_code
            out.description = strip_html(item.description) if item.description else ''
            out.requested_qty = item.requested_qty
            out.uom = item.uom
            out.from_warehouse = item.from_warehouse
            out.to_warehouse = doc.to_warehouse
            # For current item idx / total number of items
            out.idx = item.idx
            out.item_count = len(doc.items)
            return out

    return out

def get_user_crate(user: str) -> str:
    validate_exists('User', user)

    matching_crates = frappe.get_all('Crate', 
        filters={
            'picking_user': user,
            'status': 'Picking'
        },
        fields=['name']
    )

    if len(matching_crates) > 1:
        raise pick_stream.exceptions.ValidationError((
            f"User '{user}' has multiple crates active. "
            f"Found crates: {', '.join([crate['name'] for crate in matching_crates])}. Please contact IT immediately!"
        ))

    return matching_crates[0]['name'] if matching_crates else ''
    
def source_is_complete(source_name: str) -> bool:
    doc = frappe.get_doc('Source', source_name)
    return not any(not item.scanned and not item.skipped for item in doc.items)

def get_pick_stream_settings() -> dict:
    return frappe.get_cached_doc('Pick Stream Settings') 

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
        frappe.db.rollback(save_point=True)
        raise pick_stream.exceptions.ValidationError(f"Error creating item identifier: {e}")
    
    return str(identifier.name)

def get_item_print_details(item_code: str, user: str, mr_name: str, from_warehouse: str, to_warehouse: str) -> dict:
    source_doc = frappe.get_doc(
        'Source',
        {
            'user': user,
            'material_request': mr_name,
            'from_warehouse': from_warehouse,
            'to_warehouse': to_warehouse
        }
    )

    item = next(item for item in source_doc.items if item.item_code == item_code)

    if not item:
        return None
        
    return frappe._dict({
        'identifier_code': item.identifier_code,
        'qty': item.scanned_qty
    })

# def get_user_crate_details(user:str) -> dict:
#     validate_exists('User', user)
#     user_streams = frappe.db.get_all('Stream',
#         filters={'user': user, 'status': 'Picking'},
#         fields=['crate_code']
#     )
#     out = frappe._dict()
#     for stream in user_streams:
#         out[stream.crate_code] = frappe.db.get_all('Crate',
#             filters={'crate_code': stream.crate_code, 'status': 'Picking'},
#             fields=['status', 'item_group', 'from_warehouse', 'to_warehouse']
#         )
#     return out

def get_user_crate_details(user:str) -> dict:
    validate_exists('User', user)
    crate_code = get_user_crate(user)
    if crate_code:
        validate_user_assigned_to_crate(user, crate_code)
        return frappe._dict({
            'crate_code': crate_code,
            'from_warehouse': frappe.db.get_value('Crate', crate_code, 'from_warehouse'),
            'to_warehouse': frappe.db.get_value('Crate', crate_code, 'to_warehouse'),
            'items': frappe.db.get_all(
                'Source Item',
                    filters={'parent': crate_code},
                    fields=['item_code', 'item_name', 'uom', 'scanned_qty'],
                    order_by='idx asc'
                ) or []
        })
        
    return frappe._dict()

def get_crate_details_(
    user:str,
    crate_code:str,
    to_verify: bool,
    to_transit: bool,
    to_receive: bool,
) -> dict:
    validate_exists('User', user)
    validate_exists('Crate', crate_code)
    
    return frappe._dict({
        'crate_code': crate_code,
        'from_warehouse': frappe.db.get_value('Crate', crate_code, 'from_warehouse'),
        'to_warehouse': frappe.db.get_value('Crate', crate_code, 'to_warehouse'),
        'items': frappe.db.get_all(
            'Source Item',
                filters={'parent': crate_code},
                fields=['item_code', 'item_name', 'uom', 'scanned_qty'],
                order_by='idx asc'
            ) or []
    })

def create_source(mr_name:str, item_group:str, user:str) -> dict:
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
        frappe.db.commit()
        return source

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(str(e))

def crate_is_closed(crate_code:str, user:str) -> bool:
    validate_exists('Crate', crate_code)
    validate_exists('User', user)
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
        'source': source.name,
        'user': user
    })

    crate_available = check_crate_availability(crate_code, user, from_stream=True) 
    if not crate_available:
        raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' is not available. Contact Supervisor.")

    item_crate_qty_map = {}
    for item_crate in source.item_crates:
        if item_crate.crate_code == crate_code:
            item_crate_qty_map[item_crate.item_code] = item_crate.qty

    matching_item_codes_set = set(item_crate_qty_map.keys())

    for item in source.items:
        if item.item_code in matching_item_codes_set:
            crate_qty = item_crate_qty_map[item.item_code]

            stream.append('items', {
                'idx': item.idx,
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

    frappe.db.savepoint('sp3')

    try:
        stream.insert()
        frappe.db.commit()
        return stream.name

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(str(e))

def update_stream(source:dict, stream_name:str, status:str=None) -> dict:
    stream = frappe.get_doc('Stream', stream_name)
    if status:
        stream.update({'status': status})

    stream.items = []

    item_crate_qty_map = {}
    for item_crate in source.item_crates:
        if item_crate.crate_code == stream.crate_code:
            item_crate_qty_map[item_crate.item_code] = item_crate.qty

    matching_item_codes_set = set(item_crate_qty_map.keys())

    for item in source.items:
        if item.item_code in matching_item_codes_set:
            crate_qty = item_crate_qty_map[item.item_code]

            stream.append('items', {
                'idx': item.idx,
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

    frappe.db.savepoint('sp5')

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
    crates:any=[],
    as_box:bool = False,
    scanned_qty:int = 0,
    skipped:bool = False,
    as_other:bool = False,
    crate_code:str = None
) -> dict:
    validate_scan_params(scanned_qty, crate_code, as_box, as_other, skipped, crates)
    if crate_code:
        validate_exists('Crate', crate_code)

    if crates:
        crates = json.loads(crates)
        crates = [frappe._dict(crate) for crate in crates]
        for crate in crates:
            validate_exists('Crate', crate.crate_code)

    validate_exists('User', user)
    validate_exists('Item', item_code)
    validate_exists('Material Request', mr_name)

    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, item_group)

    source_name = get_source_name(mr_name, item_group)
    if not source_name:
        raise pick_stream.exceptions.ValidationError(f"Source for Material Request '{mr_name}' does not exist. Contact IT.")

    relevant_item = get_relevant_source_item(source_name) 
    if relevant_item.item_code != item_code:
        raise pick_stream.exceptions.ValidationError(f"Scanned item '{item_code}' does not match relevant item '{relevant_item.item_code}'. Contact IT.")

    doc = frappe.get_doc('Source', source_name)
    settings = get_pick_stream_settings()
    # Default to default set from warehouse if not set on material request
    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')

    out = frappe._dict()

    if crate_code:
        out.message = process_scan_as_crate(doc, crate_code, item_code, scanned_qty)
    elif as_box:
        identifier_code = create_item_identifier(item_code, 'box', user, mr_name, from_warehouse, to_warehouse, scanned_qty, relevant_item.uom)
        out.message = process_scan_as_box(doc, identifier_code, item_code, scanned_qty)
    elif as_other:
        identifier_code = create_item_identifier(item_code, 'other', user, mr_name, from_warehouse, to_warehouse, scanned_qty, relevant_item.uom)
        out.message = process_scan_as_other(doc, identifier_code, item_code, scanned_qty)
    elif skipped:
        out.message = process_scan_as_skip(doc, item_code)
    elif crates:
        out.message = process_scan_as_crates(doc, crates, item_code)

    doc.scan_pointer += 1

    frappe.db.savepoint('sp1')

    try:
        doc.save()
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        raise pick_stream.exceptions.ValidationError(str(e))
        
    out.complete = frappe.db.get_value('Source', doc.name, 'status') == 'Completed'
        
    return out

def process_scan_as_crate(source:dict, crate_code:str, item_code:str, scanned_qty:int) -> str:
    item = next((item for item in source.items if item.item_code == item_code), None)
    if not item:
        raise pick_stream.exceptions.ValidationError(f'Item {item_code} not found in source document. Contact IT.')
    
    existing_crate = next((
        crate for crate in source.item_crates
        if crate.item_code == item_code and crate.crate_code == crate_code
    ), None)
    
    if existing_crate:
        raise pick_stream.exceptions.ValidationError(f'Crate {crate_code} already exists for item {item_code}. Contact IT.')

    existing_item_crate_records = [
        crate for crate in source.item_crates
        if crate.item_code == item_code and crate.crate_code == crate_code
    ]
    
    if len(existing_item_crate_records) > 0:
        raise pick_stream.exceptions.ValidationError(f'Crate {crate_code} already exists for item {item_code}. Contact IT.')
    
    source.append('item_crates', {
        'source_item': item.name,
        'crate_code': crate_code,
        'item_code': item_code,
        'qty': scanned_qty
    })
    
    item.scanned = 1
    
    return f'Scanned {scanned_qty} {item.uom} for item {item_code} into crate {crate_code}'

def process_scan_as_crates(doc, crates, item_code):
    for crate in crates:
        process_scan_as_crate(doc, crate.crate_code, item_code, crate.scanned_qty)

def process_scan_as_box(source:dict, identifier_code:str, item_code:str, scanned_qty:int) -> str:
    item = next((item for item in source.items if item.item_code == item_code))
    item.scanned = 1
    item.is_box_item = 1
    item.scanned_qty = scanned_qty
    item.identifier_code = identifier_code
    return f'Scanned {scanned_qty} {item.uom} for item {item_code} assigned to box {identifier_code}'

def process_scan_as_other(source:dict, identifier_code:str, item_code:str, scanned_qty:int) -> str:
    item = next((item for item in source.items if item.item_code == item_code))
    item.scanned = 1
    item.is_other_item = 1
    item.scanned_qty = scanned_qty
    item.identifier_code = identifier_code
    return f'Scanned {scanned_qty} {item.uom} for item {item_code} assigned to identifier {identifier_code}'

def process_scan_as_skip(source:dict, item_code:str) -> str:
    item = next((item for item in source.items if item.item_code == item_code))
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

def close_crate(crate_code:str) -> None:
    item_crates = frappe.db.get_all('Item Crates',
        filters={
            'crate_code': crate_code,
            'parenttype': 'Source'
        },
        fields=['parent'])

    if not item_crates:
        raise pick_stream.exceptions.ValidationError(f"No matching item crates found. Contact IT.")
        
    closed_crates = frappe.db.get_all('Item Crates',
        filters={
            'crate_code': crate_code,
            'parenttype': 'Source',
            'crate_closed': 1
        },
        fields=['parent'])
    
    if closed_crates:
        raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' is already closed. Contact IT.")

    source_names = {item.parent for item in item_crates}
    for name in source_names:
        source_doc = frappe.get_doc('Source', name)
        for item_crate in source_doc.item_crates:
            if item_crate.crate_code == crate_code:
                item_crate.crate_closed = 1

        try:
            source_doc.save()
            frappe.db.commit()
            
        except Exception as e:
            frappe.db.rollback()
            raise pick_stream.exceptions.ValidationError(f'Error closing crate: {e}')
            
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
    settings = get_pick_stream_settings()

    if crate_code:
        validate_exists('Crate', crate_code)
        if qty <= 0:
            qty = 1
        return print_crate_label(printer, settings, crate_code, qty)

    if item_identifier:
        validate_exists('Pick Stream Identifier', item_identifier)
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

    validate_exists('Material Request', mr_name)
    validate_exists('Item', item_code)
    validate_item_type(item_type, settings)
    validate_exists('User', user)
        
    # Default to default set from warehouse if not set on material request
    from_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_from_warehouse') or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value('Material Request', mr_name, 'set_warehouse')
    item_name = frappe.db.get_value('Item', item_code, 'item_name')
    print_job = print_item_identifier(user, mr_name, printer, from_warehouse, to_warehouse, item_code, item_type, settings, item_name, qty, item_identifier)
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
        item_print_details = get_item_print_details(item_code, user, mr_name, from_warehouse, to_warehouse)
        if not item_print_details:
            raise pick_stream.exceptions.ValidationError(f"Item '{item_code}' not found in source for user '{user}' and material request '{mr_name}'.")

        item_identifier = item_print_details.identifier_code

        # Default to item qty if user does not provide label qty
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
    
def get_verification_list(user='jeriel@jollysonline.com') -> dict:
    validate_exists('User', user)

    stock_manager = has_role(user, 'Stock Manager') 
    if not stock_manager:
        user_branch = get_user_branch(user)
        target_warehouse = get_workflow_target_warehouse(user, user_branch)
        workflow_details = get_workflow_details(target_warehouse)

        validate_role(user, workflow_details.verification_user_role)

        if user_branch not in workflow_details.verification_branches:
            raise pick_stream.exceptions.ValidationError(f"User '{user}' is not authorized to verify from '{user_branch}'. Contact Supervisor.")

        to_warehouses = [workflow_details.target_warehouse]
        verification_branches = workflow_details.verification_branches

    else:
        workflow_details = get_workflow_details()
        to_warehouses = [workflow.target_warehouse for workflow in workflow_details]
        verification_branches = set()
        for workflow in workflow_details:
            verification_branches.update(workflow.verification_branches)

    crates = frappe.db.sql("""
        SELECT DISTINCT ic.crate_code, ic.parent
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        WHERE ic.parenttype = 'Source'
        AND ic.crate_closed = 1
        AND ic.verified = 0
        AND ic.received = 0
        AND s.to_warehouse IN %(to_warehouses)s
        ORDER BY ic.modified ASC
    """, {
        'to_warehouses': to_warehouses
    }, as_dict=True)

    return [frappe._dict({'crate_code': crate.crate_code, 'source': crate.parent}) for crate in crates] if crates else frappe._dict()

def process_verification_request(
    user:str,
    items:any,
    source:str,
    crate_code:str
) -> str:
    validate_exists('User', user)
    validate_exists('Source', source)
    validate_exists('Crate', crate_code)

    items = json.loads(items)
    items = [frappe._dict(item) for item in items]
    for item in items:
        validate_exists('Item', item.item_code)

    to_warehouse = frappe.db.get_value('Source', source, 'to_warehouse')
    if not to_warehouse:
        raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' has no destination warehouse set. Contact IT.")

    workflow_details = get_workflow_details(to_warehouse)
    
    if not has_role(user, 'Stock Manager'):
        validate_role(user, workflow_details.verification_user_role)

        user_branch = get_user_branch(user)
        if user_branch not in workflow_details.verification_branches:
            raise pick_stream.exceptions.ValidationError(f"User '{user}' is not authorized to verify from '{user_branch}'. Contact Supervisor.")

    source_doc = frappe.get_doc('Source', source)
    
    verified_items = {item.item_code: item.qty for item in items}
    
    discrepancies = []
    updated_items = []
    
    for item_crate in source_doc.item_crates:
        if item_crate.crate_code == crate_code:
            item_code = item_crate.item_code
            current_qty = item_crate.qty
            verified_qty = verified_items.get(item_code, 0)
            
            if current_qty != verified_qty:
                discrepancies.append({
                    'item_code': item_code,
                    'current_qty': current_qty,
                    'verified_qty': verified_qty,
                    'difference': verified_qty - current_qty
                })
                
                item_crate.qty = verified_qty
                updated_items.append(item_code)
            
            item_crate.verified = 1

    frappe.db.savepoint('verification_savepoint')
    
    try:
        source_doc.save()
        frappe.db.commit()
        
        if discrepancies:
            discrepancy_log = []
            for disc in discrepancies:
                if disc.get('note'):
                    discrepancy_log.append(f"Item {disc['item_code']}: {disc['note']} (verified: {disc['verified_qty']})")
                else:
                    discrepancy_log.append(f"Item {disc['item_code']}: {disc['current_qty']} → {disc['verified_qty']} (diff: {disc['difference']:+d})")
            
            frappe.log_error(
                message=f"Verification discrepancies found by {user} for crate {crate_code}:\n" + 
                        "\n".join(discrepancy_log),
                title=f"[Pick Stream] Verification Discrepancies - Crate {crate_code}",
                reference_name=source
            )
        
        success_message = f'Verification completed successfully for crate {crate_code}'
        
        if discrepancies:
            success_message += f'. {len(discrepancies)} discrepancies found and corrected'
        
        if updated_items:
            success_message += f'. Updated quantities for: {", ".join(updated_items)}'
            
        return success_message
        
    except Exception as e:
        frappe.db.rollback(save_point='verification_savepoint')
        raise pick_stream.exceptions.ValidationError(f'Error during verification: {str(e)}')

def get_workflow_details(target_warehouse:str=None):
   """Will return all workflows if target warehouse is not passed (For Stock Managers)"""
   settings = get_pick_stream_settings()
   active_workflows = [row for row in settings.workflow_settings if row.is_active]

   if target_warehouse:
       validate_exists('Warehouse', target_warehouse)
       matching_row = next((row for row in active_workflows if row.target_warehouse == target_warehouse), None)
       
       if matching_row is None:
           raise pick_stream.exceptions.ValidationError(f'No active workflow found for {target_warehouse}. Contact Supervisor.')
       
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

       result.append(frappe._dict({
           'target_warehouse': row.target_warehouse,
           'verification_branches': verification_branches,
           'picking_warehouse_branches': picking_warehouse_branches,
           'verification_user_role': row.verification_user_role,
           'verification_required': row.verification_required,
           'verification_approval_required': row.verification_approval_required,
           'transit_user_role': row.transit_user_role,
           'transit_required': row.transit_required,
           'transit_warehouse': row.transit_warehouse,
           'receiving_user_role': row.receiving_user_role,
           'send_notifications': row.send_notifications,
       }))

   return result[0] if target_warehouse else result

def get_transit_list(user: str):
    validate_exists('User', user)

    stock_manager = has_role(user, 'Stock Manager') 
    if not stock_manager:
        user_branch = get_user_branch(user)
        target_warehouse = get_workflow_target_warehouse(user, user_branch)
        workflow_details = get_workflow_details(target_warehouse)

        validate_role(user, workflow_details.transit_user_role)
        to_warehouses = [workflow_details.target_warehouse]
        workflows = [workflow_details]

    else:
        workflow_details = get_workflow_details()
        to_warehouses = [workflow.target_warehouse for workflow in workflow_details]
        workflows = workflow_details

    verification_conditions = []

    for workflow in workflows:
        if workflow.verification_required:
            # If verification is required, crate must be verified
            verification_conditions.append(f"(s.to_warehouse = '{workflow.target_warehouse}' AND ic.verified = 1)")
        else:
            # If verification is not required, crate can be unverified
            verification_conditions.append(f"(s.to_warehouse = '{workflow.target_warehouse}')")

    if not verification_conditions:
        return []

    verification_clause = ' OR '.join(verification_conditions)

    crates = frappe.db.sql(f"""
        SELECT DISTINCT ic.crate_code, ic.parent
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        WHERE ic.parenttype = 'Source'
        AND ic.crate_closed = 1
        AND ic.received = 0
        AND s.to_warehouse IN %(to_warehouses)s
        AND ({verification_clause})
        ORDER BY ic.modified ASC
    """, {'to_warehouses': to_warehouses}, as_dict=True)

    return [crate.crate_code for crate in crates] if crates else []

def process_transit_request(
    user: str,
    crate_codes:any,
    to_warehouse:str,
    from_warehouse:str
) -> str:
    validate_exists('User', user)
    validate_exists('Warehouse', to_warehouse)
    validate_exists('Warehouse', from_warehouse)

    crate_codes = json.loads(crate_codes)
    crate_codes = [str(crate_code) for crate_code in crate_codes]    
    for crate_code in crate_codes:
        validate_exists('Crate', crate_code)

    workflow_details = get_workflow_details(to_warehouse)
    
    if not workflow_details.transit_required:
        raise pick_stream.exceptions.ValidationError(f"Transit is not required for '{to_warehouse}'. Contact Supervisor.")

    if not has_role(user, 'Stock Manager'):
        validate_role(user, workflow_details.transit_user_role)

    all_sources = set()
    crate_stream_map = {}
    
    for crate_code in crate_codes:
        crate_doc = frappe.get_doc('Crate', crate_code)
        
        if crate_doc.to_warehouse != to_warehouse:
            raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' destination is '{crate_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")
        
        if not crate_doc.streams:
            raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' has no streams. Contact IT.")
        
        crate_sources = []
        for stream_row in crate_doc.streams:
            stream_doc = frappe.get_doc('Stream', stream_row.stream)
            source = stream_doc.source
            all_sources.add(source)
            crate_sources.append(source)
        
        crate_stream_map[crate_code] = crate_sources

    source_docs = {}
    for source in all_sources:
        source_doc = frappe.get_doc('Source', source)
        source_docs[source] = source_doc

    for crate_code in crate_codes:
        for source in crate_stream_map[crate_code]:
            source_doc = source_docs[source]
            
            crate_items = [item for item in source_doc.item_crates if item.crate_code == crate_code]
            
            if not crate_items:
                raise pick_stream.exceptions.ValidationError(f"No items found for crate '{crate_code}' in source '{source}'. Contact IT.")
            
            if workflow_details.verification_required:
                unverified_items = [item for item in crate_items if not item.verified]
                if unverified_items:
                    raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' has unverified items in source '{source}'. Contact IT.")
            
            unclosed_items = [item for item in crate_items if not item.crate_closed]
            if unclosed_items:
                raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' has unclosed items in source '{source}'. Contact IT.")

    warehouse_items = {}
    
    for crate_code in crate_codes:
        for source in crate_stream_map[crate_code]:
            source_doc = source_docs[source]
            
            crate_items = [item for item in source_doc.item_crates if item.crate_code == crate_code]
            
            for item_crate in crate_items:
                source_item = next((item for item in source_doc.items if item.name == item_crate.source_item), None)
                if not source_item:
                    raise pick_stream.exceptions.ValidationError(f"Source item '{item_crate.source_item}' not found in source '{source}'. Contact IT.")
                
                item_from_warehouse = source_item.from_warehouse
                
                warehouse_key = f"{item_from_warehouse}|{source}"
                if warehouse_key not in warehouse_items:
                    warehouse_items[warehouse_key] = {
                        'from_warehouse': item_from_warehouse,
                        'source': source,
                        'items': []
                    }
                
                warehouse_items[warehouse_key]['items'].append({
                    'item_code': item_crate.item_code,
                    'qty': item_crate.qty,
                    'uom': source_item.uom,
                    'crate_code': crate_code
                })

    created_stock_entries = []
    
    frappe.db.savepoint('transit_savepoint')
    
    try:
        transit_warehouse = workflow_details.transit_warehouse
        
        for warehouse_key, warehouse_data in warehouse_items.items():
            from_warehouse = warehouse_data['from_warehouse']
            source = warehouse_data['source']
            items = warehouse_data['items']
            
            stock_entry = frappe.new_doc('Stock Entry')
            stock_entry.update({
                'stock_entry_type': 'Material Transfer',
                'purpose': 'Material Transfer',
                'from_warehouse': from_warehouse,
                'to_warehouse': transit_warehouse,
                'posting_date': frappe.utils.today(),
                'posting_time': frappe.utils.nowtime(),
                'company': frappe.defaults.get_user_default('Company'),
                'remarks': f'Transit from {from_warehouse} to {transit_warehouse} for crates: {", ".join(set([item["crate_code"] for item in items]))} (Source: {source})'
            })
            
            for item in items:
                stock_entry.append('items', {
                    'item_code': item['item_code'],
                    's_warehouse': from_warehouse,
                    't_warehouse': transit_warehouse,
                    'qty': item['qty'],
                    'uom': item['uom'],
                    'basic_rate': frappe.db.get_value('Item', item['item_code'], 'valuation_rate') or 0
                })
            
            stock_entry.insert()
            stock_entry.submit()
            created_stock_entries.append(stock_entry.name)
        
        for crate_code in crate_codes:
            frappe.db.set_value('Crate', crate_code, {
                'status': 'In Transit',
                'transit_user': user
            })
        
        for crate_code in crate_codes:
            for source in crate_stream_map[crate_code]:
                streams = frappe.get_all('Stream', 
                    filters={'crate_code': crate_code, 'source': source},
                    fields=['name']
                )
                for stream in streams:
                    frappe.db.set_value('Stream', stream.name, 'status', 'In Transit')
        
        frappe.db.commit()
        
        return f'Transit to {transit_warehouse} completed successfully for {len(crate_codes)} crates. Created {len(created_stock_entries)} stock entries: {", ".join(created_stock_entries)}'
        
    except Exception as e:
        frappe.db.rollback(save_point='transit_savepoint')
        raise pick_stream.exceptions.ValidationError(f'Error during transit: {str(e)}')

def get_receiving_list(user: str) -> list:
    validate_exists('User', user)

    stock_manager = has_role(user, 'Stock Manager') 
    if not stock_manager:
        user_branch = get_user_branch(user)
        target_warehouse = get_workflow_target_warehouse(user, user_branch)
        workflow_details = get_workflow_details(target_warehouse)

        validate_role(user, workflow_details.receiving_user_role)
        to_warehouses = [workflow_details.target_warehouse]

    else:
        workflow_details = get_workflow_details()
        to_warehouses = [workflow.target_warehouse for workflow in workflow_details]

    verification_conditions = []
    transit_conditions = []
    
    for workflow in workflow_details:
        target_wh = workflow.target_warehouse
        
        if workflow.verification_required:
            verification_conditions.append(f"(s.to_warehouse = '{target_wh}' AND ic.verified = 1)")
        else:
            verification_conditions.append(f"(s.to_warehouse = '{target_wh}')")
        
        if workflow.transit_required:
            transit_conditions.append(f"(s.to_warehouse = '{target_wh}' AND c.status = 'In Transit')")
        else:
            transit_conditions.append(f"(s.to_warehouse = '{target_wh}' AND c.status IN ('Waiting', 'Verifying', 'In Transit'))")

    if not verification_conditions:
        return []

    verification_clause = ' OR '.join(verification_conditions)
    transit_clause = ' OR '.join(transit_conditions)

    crates = frappe.db.sql(f"""
        SELECT DISTINCT ic.crate_code, ic.parent
        FROM `tabItem Crates` ic
        JOIN `tabSource` s ON ic.parent = s.name
        JOIN `tabCrate` c ON ic.crate_code = c.name
        WHERE ic.parenttype = 'Source'
        AND ic.crate_closed = 1
        AND ic.received = 0
        AND s.to_warehouse IN %(to_warehouses)s
        AND ({verification_clause})
        AND ({transit_clause})
        ORDER BY ic.modified ASC
    """, {'to_warehouses': to_warehouses}, as_dict=True)

    return [crate.crate_code for crate in crates] if crates else []

def process_receiving_request(
    user: str,
    crate_codes: any,
    to_warehouse: str
) -> str:
    validate_exists('User', user)
    validate_exists('Warehouse', to_warehouse)

    crate_codes = json.loads(crate_codes)
    crate_codes = [str(crate_code) for crate_code in crate_codes]
    for crate_code in crate_codes:
        validate_exists('Crate', crate_code)

    workflow_details = get_workflow_details(to_warehouse)
    
    if not has_role(user, 'Stock Manager'):
        validate_role(user, workflow_details.receiving_user_role)

    transit_warehouse = None
    crate_stream_map = {}
    all_sources = set()
    
    for crate_code in crate_codes:
        crate_doc = frappe.get_doc('Crate', crate_code)
        
        if crate_doc.status != 'In Transit':
            raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' is not in transit. Current status: {crate_doc.status}")
        
        if crate_doc.to_warehouse != to_warehouse:
            raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' destination is '{crate_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")
        
        if not transit_warehouse:
            transit_warehouse = workflow_details.transit_warehouse
        
        if not crate_doc.streams:
            raise pick_stream.exceptions.ValidationError(f"Crate '{crate_code}' has no streams. Contact IT.")
        
        crate_sources = []
        for stream_row in crate_doc.streams:
            stream_doc = frappe.get_doc('Stream', stream_row.stream)
            source = stream_doc.source
            all_sources.add(source)
            crate_sources.append(source)
        
        crate_stream_map[crate_code] = crate_sources

    source_docs = {}
    for source in all_sources:
        source_doc = frappe.get_doc('Source', source)
        source_docs[source] = source_doc

    warehouse_items = {}
    
    for crate_code in crate_codes:
        for source in crate_stream_map[crate_code]:
            source_doc = source_docs[source]
            
            crate_items = [item for item in source_doc.item_crates if item.crate_code == crate_code]
            
            if not crate_items:
                raise pick_stream.exceptions.ValidationError(f"No items found for crate '{crate_code}' in source '{source}'. Contact IT.")
            
            for item_crate in crate_items:
                source_item = next((item for item in source_doc.items if item.name == item_crate.source_item), None)
                if not source_item:
                    raise pick_stream.exceptions.ValidationError(f"Source item '{item_crate.source_item}' not found in source '{source}'. Contact IT.")
                
                if source not in warehouse_items:
                    warehouse_items[source] = {
                        'source': source,
                        'items': []
                    }
                
                warehouse_items[source]['items'].append({
                    'item_code': item_crate.item_code,
                    'qty': item_crate.qty,
                    'uom': source_item.uom,
                    'crate_code': crate_code
                })

    created_stock_entries = []
    
    frappe.db.savepoint('receiving_savepoint')
    
    try:
        for source, warehouse_data in warehouse_items.items():
            items = warehouse_data['items']
            
            stock_entry = frappe.new_doc('Stock Entry')
            stock_entry.update({
                'stock_entry_type': 'Material Transfer',
                'purpose': 'Material Transfer',
                'from_warehouse': transit_warehouse,
                'to_warehouse': to_warehouse,
                'posting_date': frappe.utils.today(),
                'posting_time': frappe.utils.nowtime(),
                'company': frappe.defaults.get_user_default('Company'),
                'remarks': f'Receiving from {transit_warehouse} to {to_warehouse} for crates: {", ".join(set([item["crate_code"] for item in items]))} (Source: {source})'
            })
            
            for item in items:
                stock_entry.append('items', {
                    'item_code': item['item_code'],
                    's_warehouse': transit_warehouse,
                    't_warehouse': to_warehouse,
                    'qty': item['qty'],
                    'uom': item['uom'],
                    'basic_rate': frappe.db.get_value('Item', item['item_code'], 'valuation_rate') or 0
                })
            
            stock_entry.insert()
            stock_entry.submit()
            created_stock_entries.append(stock_entry.name)
        
        # Update crates status to "Completed" and set receiving_user
        for crate_code in crate_codes:
            frappe.db.set_value('Crate', crate_code, {
                'status': 'Available',  # Reset to available for next use
                'receiving_user': user,
                'current_warehouse': to_warehouse,
                'picking_user': None,  # Clear previous users
                'verifying_user': None,
                'transit_user': None
            })
        
        # Update streams status to "Completed"
        for crate_code in crate_codes:
            for source in crate_stream_map[crate_code]:
                streams = frappe.get_all('Stream', 
                    filters={'crate_code': crate_code, 'source': source},
                    fields=['name']
                )
                for stream in streams:
                    frappe.db.set_value('Stream', stream.name, 'status', 'Completed')
        
        for crate_code in crate_codes:
            for source in crate_stream_map[crate_code]:
                source_doc = source_docs[source]
                for item_crate in source_doc.item_crates:
                    if item_crate.crate_code == crate_code:
                        item_crate.received = 1
                
                # Save the source document
                source_doc.save()
        
        frappe.db.commit()
        
        success_message = f'Receiving completed successfully for {len(crate_codes)} crates. Created {len(created_stock_entries)} stock entries: {", ".join(created_stock_entries)}'
        return success_message
        
    except Exception as e:
        frappe.db.rollback(save_point='receiving_savepoint')
        raise pick_stream.exceptions.ValidationError(f'Error during receiving: {str(e)}')