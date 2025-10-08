import json
import html
from typing import List, Dict, Any, Optional

import frappe
from frappe.utils import strip_html
from frappe.utils.nestedset import get_descendants_of

import pick_stream


def get_settings() -> Dict:
    """Returns cached Pick Stream Settings document"""
    return frappe.get_cached_doc('Pick Stream Settings')


def get_user_branch(user:str) -> str:
    """Returns employee branch based on user"""
    if not frappe.db.exists('Employee', {'user_id': user}):
        raise pick_stream.exceptions.DoesNotExistError(f"Employee for user '{user}' does not exist. Contact HR.")
    branch = frappe.db.get_value('Employee', {'user_id': user}, ['branch'])
    if not branch:
        raise pick_stream.exceptions.ValidationError(f"Branch for user '{user}' is not set. Contact HR.")
    return branch


def get_warehouse_group(user:str, user_branch:str, settings:Dict=None) -> str:
    """Returns warehouse group defined in settings based on user's branch"""
    if not settings:
        settings = get_settings()
    if not settings.warehouse_group_map:
        raise pick_stream.exceptions.ValidationError(
            f'No warehouse group mappings configured. Contact IT.'
        )
    for mapping in settings.warehouse_group_map:
        if mapping.branch == user_branch:
            return mapping.warehouse
    raise pick_stream.exceptions.ValidationError(
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
        raise pick_stream.exceptions.ValidationError(f"User '{user}' is not assigned to any item group. Contact Supervisor.")
    return user_item_groups


def get_mr_item_groups_for_user(mr_name:str, user:str, user_item_groups:List=[]) -> List:
    try:
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
        raise pick_stream.exceptions.ValidationError(f'Error getting item groups for user: {e}') 
        
        
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
        raise pick_stream.exceptions.SystemError(str(e))


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
            raise pick_stream.exceptions.ValidationError(f"Employee for user '{user}' branch is not valid. Contact HR Department.")


def get_material_request_items_details(mr_name:str, user:str, selected_item_group:str) -> Dict:
    pick_stream.validations.validate_exists('User', user)
    pick_stream.validations.validate_exists('Material Request', mr_name)
    pick_stream.validations.validate_user_assigned_to_mr(mr_name, user)
    pick_stream.validations.validate_user_assigned_to_item_group(user, selected_item_group)
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


def get_workflow_details(target_warehouse:str=None):
    """Will return all workflows if target warehouse is not passed (For privileged users)"""
    settings = pick_stream.utils.get_settings()
    active_workflows = [row for row in settings.workflow_settings if row.is_active]

    if not active_workflows:
        raise pick_stream.exceptions.ValidationError('No active workflows found. Contact IT.')

    if target_warehouse:
        pick_stream.validations.validate_exists('Warehouse', target_warehouse)
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
    pick_stream.validations.validate_exists('User', user)
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
    pick_stream.validations.validate_exists('User', user)
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
    pick_stream.validations.validate_exists('User', user)
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

# TODO: Get Picking User by checking item crates child table
def check_crate_availability(crate_code: str, user: str, from_stream: bool = False) -> bool:
    pick_stream.validations.validate_exists('Crate', crate_code)
    if not from_stream: 
        pick_stream.validations.validate_exists('User', user)
        
    crate_status = frappe.db.get_value('Crate', crate_code, 'status')
    
    if crate_status != 'Available':
        crate_picking_user = get_crate_picking_user(crate_code)
        if not crate_picking_user:
            raise pick_stream.exceptions.SystemError((
                f"Crate '{crate_code}' is not available and has no picking user. Contact IT."
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

def get_crate_picking_user(crate_code):
    """Returns current picking user for crate"""
    all_picking_users = frappe.get_all(
        'Item Crates',
        fields=['picking_user', 'crate_code', 'modified'],
        filters=[
            ['crate_code', '=', crate_code],
            ['parenttype', '=', 'Source'], 
            ['picking_user', 'is', 'set'],
            ['crate_closed', '=', 0],
            ['transited', '=', 0],
            ['verified', '=', 0],
            ['received', '=', 0]
        ]
    )
    if not all_picking_users:
        return None
        
    user_dict = {}
    for record in all_picking_users:
        key = (record['crate_code'], record['picking_user'])
        if key not in user_dict or record['modified'] > user_dict[key]['modified']:
            user_dict[key] = record
    
    # There should only be one picking user at a given time for a crate
    # If multiple are found then close the crate to ensure forward correctedness
    unique_records = list(user_dict.values())
    if len(unique_records) > 1:
        pick_stream.core.close_crate(crate_code, commit=True)
    
    most_recent_record = max(unique_records, key=lambda x: x['modified'])
    return most_recent_record['picking_user']