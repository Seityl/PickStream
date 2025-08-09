import json
from typing import List, Dict, Any, Tuple

import frappe
from frappe.utils.nestedset import get_descendants_of

import pick_stream

def get_settings() -> Dict:
    """Returns cached Pick Stream Settings document"""
    return frappe.get_cached_doc('Pick Stream Settings')

def get_user_branch(user:str) -> str:
    """Returns employee branch based on user"""
    if not frappe.db.exists('Employee', {'user_id': user}):
        raise pick_stream.exceptions.DoesNotExistError(f"Employee for user '{user}' does not exist. Contact HR Department.")

    branch = frappe.db.get_value('Employee', {'user_id': user}, ['branch'])
    if not branch:
        raise pick_stream.exceptions.ValidationError(f"Employee branch for user '{user}' is not set. Contact HR Department.")
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
        f"Employee branch '{user_branch}' for user '{user}' not mapped to a warehouse. Contact IT. "
    )

def get_child_warehouses(parent_warehouse:str) -> list:
    """Get all descendant warehouses of specified parent"""
    return get_descendants_of('Warehouse', parent_warehouse)

def get_assigned_item_groups(user:str) -> list:
    """Get item groups assigned to a user through User Group relationships."""
    user_item_groups = frappe.get_all(
        'User Group',
        filters={
            'custom_is_item_group': 1,
            'name': ['in', frappe.get_all(
                'User Group Member',
                filters={
                    'parenttype': 'User Group',
                    'user': user
                },
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
            pick_stream.validations.validate_user_assigned_to_item_group(user, mr_group)
        return mr_groups

    except Exception as e:
        raise pick_stream.exceptions.ValidationError(f'Error getting item groups for user: {e}') 
        
def get_mr_available_item_groups_for_user(
    mr_name:str,
    user:str,
    child_warehouses:list=None
) -> list:
    """Returns item groups which are available or incomplete for material request"""
    pick_stream.validations.validate_user_assigned_to_mr(mr_name, user)
    out = []
    user_item_groups = get_mr_item_groups_for_user(mr_name, user)

    if not child_warehouses:
        user_branch = pick_stream.utils.get_user_branch(user)
        warehouse_group = pick_stream.utils.get_warehouse_group(user, user_branch)
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

def check_source_exists(mr_name:str, item_group:str) -> bool:
    if frappe.db.exists('Source', {
        'material_request': mr_name,
        'item_group': item_group
    }):
        return True
    return False

def get_source_name(mr_name:str, item_group:str) -> str:
    return frappe.db.get_value('Source', {
        'material_request': mr_name,
        'item_group': item_group
    }, 'name') or ''

def get_material_request_item_group_item_quantity(mr_name: str, item_group: str, user: str) -> dict:
    if not check_source_exists(mr_name, item_group):
        out = frappe._dict({'completed': 0})
        user_branch = pick_stream.utils.get_user_branch(user)
        warehouse_group = pick_stream.utils.get_warehouse_group(user, user_branch)
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

def get_material_request_items_details(mr_name:str, user:str, selected_item_group:str) -> dict:
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
    """Will return all workflows if target warehouse is not passed (For Stock Managers)"""
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
            'transit_required': row.transit_required,
            'transit_after_verification': row.transit_after_verification,
            'transit_user_role': row.transit_user_role,
            'transit_warehouse': row.transit_warehouse,
            'receiving_user_role': row.receiving_user_role,
            'receiving_after_verification': row.receiving_after_verification,
            'send_notifications': row.send_notifications
        }))

    return result[0] if target_warehouse else result

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