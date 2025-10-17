"""
Core business logic for Pick Stream system.

Implements the main operational functions for all warehouse workflows:
- Material Request assignment and user task management
- Picking workflow: Source creation, item scanning, and crate management
- Verification workflow: Quantity validation and discrepancy handling
- Transit workflow: Inter-warehouse transfer processing via stock entries
- Receiving workflow: Final delivery and stock entry completion

Author: Jeriel Francis

Copyright (c) 2025, Jollys Pharmacy Limited and contributors
For license information, please see license.txt
"""


import json
from typing import List, Dict, Any

import frappe
from frappe import _

from pick_stream import utils, validations, exceptions


def assign_users_to_mr(doc:str, method:str) -> Dict:
    """Assigns users to a Material Request (MR) based on item groups in the MR."""
    if not doc.custom_assign_warehouse_staff:
        return frappe.msgprint('Assignment to warehouse staff was skipped', alert=True)
    settings = utils.get_settings()
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


def get_user_material_requests(user: str) -> List:
    """Returns submitted Material Requests assigned to a user with item group availability."""
    validations.validate_exists('User', user)
    validations.validate_permission(user, 'picking')
    # Get user context
    user_item_groups = utils.get_assigned_item_groups(user)
    user_branch = utils.get_user_branch(user)
    warehouse_group = utils.get_warehouse_group(user, user_branch)  
    child_warehouses = utils.get_child_warehouses(warehouse_group)
    # Get default warehouse from settings
    settings = utils.get_settings()
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
            INNER JOIN `tabWarehouse Group Map` wgm
                ON wgm.warehouse = COALESCE(NULLIF(mr.set_from_warehouse, ''), %(default_warehouse)s)
            WHERE td.allocated_to = %(user)s
                AND td.status = 'Open'
                AND td.reference_type = 'Material Request'
                AND mr.docstatus = 1
                AND wgm.branch = %(user_branch)s  -- Filter by branch from warehouse group map
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
        'default_warehouse': default_set_from_warehouse,
        'user_branch': user_branch
    }, as_dict=True)
    # Parse JSON
    for mr in mr_list:
        if mr.get('item_group_availability'):
            try:
                # Convert JSON string to dict
                if isinstance(mr['item_group_availability'], str):
                    mr['item_group_availability'] = json.loads(mr['item_group_availability'])
            except (json.JSONDecodeError, AttributeError):
                mr['item_group_availability'] = {}
        else:
            mr['item_group_availability'] = {}
    return mr_list
        

def get_material_request_item_groups_view_details(mr_name: str, user: str) -> Dict:
    validations.validate_exists('User', user)
    validations.validate_permission(user, 'picking')
    validations.validate_exists('Material Request', mr_name)
    # Allow users with Closed ToDos to view this page
    # This handles the case where a user just completed their last pick list
    # and is redirected back to the item groups view
    validations.validate_user_assigned_to_mr(mr_name, user, allow_closed=True)
    # Get user context
    user_branch = utils.get_user_branch(user)
    warehouse_group = utils.get_warehouse_group(user, user_branch)
    child_warehouses = utils.get_child_warehouses(warehouse_group)
    # Get default warehouse from settings
    settings = utils.get_settings()
    default_set_from_warehouse = settings.default_set_from_warehouse
    result = frappe.db.sql(
        """
        WITH mr_info AS (
            SELECT
                mr.name AS mr_name,
                mr.set_warehouse AS target_warehouse,
                COALESCE(NULLIF(mr.set_from_warehouse, ''), %(default_set_from_warehouse)s) AS source_warehouse
            FROM `tabMaterial Request` mr
            WHERE mr.name = %(mr_name)s
        ),
        item_groups_base AS (
            SELECT DISTINCT
                mri.item_group AS item_group_name
            FROM `tabMaterial Request Item` mri
            INNER JOIN `tabUser Group Member` ugm
                ON ugm.parent = mri.item_group
                AND ugm.parenttype = 'User Group'
                AND ugm.user = %(user)s
            INNER JOIN `tabUser Group` ug
                ON ug.name = ugm.parent
                AND ug.custom_is_item_group = 1
            WHERE mri.parent = %(mr_name)s
        ),
        source_status AS (
            SELECT
                src.item_group,
                MAX(CASE WHEN (src.status = 'Completed' OR src.docstatus = 1) THEN 1 ELSE 0 END) AS is_completed
            FROM `tabSource` src
            WHERE src.material_request = %(mr_name)s
            GROUP BY src.item_group
        ),
        stock_availability AS (
            SELECT
                item.item_group,
                MAX(CASE WHEN bin.actual_qty >= 1 THEN 1 ELSE 0 END) AS has_stock
            FROM `tabMaterial Request Item` mri_check
            INNER JOIN `tabItem` item ON mri_check.item_code = item.name
            INNER JOIN `tabBin` bin ON mri_check.item_code = bin.item_code
            WHERE mri_check.parent = %(mr_name)s
                AND bin.warehouse IN %(child_warehouses)s
                AND (mri_check.stock_qty > COALESCE(mri_check.ordered_qty, 0))
            GROUP BY item.item_group
        ),
        crates_data AS (
            SELECT
                ps.item_group,
                JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'crate_code', ps.crate_code,
                        'status', ps.status
                    )
                ) AS crates_json
            FROM `tabStream` ps
            WHERE ps.material_request = %(mr_name)s
                AND ps.item_group IS NOT NULL
                AND (ps.crate_code IS NOT NULL
                    OR ps.item_group IS NOT NULL
                    OR ps.status IS NOT NULL)
            GROUP BY ps.item_group
        ),
        item_counts_from_source AS (
            SELECT
                si.item_group,
                src.name AS source_name,
                SUM(CASE WHEN (si.scanned = 1 OR si.skipped = 1) THEN 1 ELSE 0 END) AS completed,
                COUNT(*) AS total
            FROM `tabSource` src
            INNER JOIN `tabSource Item` si ON si.parent = src.name
            WHERE src.material_request = %(mr_name)s
            GROUP BY si.item_group, src.name
        ),
        item_counts_from_mr AS (
            SELECT
                mri.item_group,
                COUNT(DISTINCT mri.name) AS total
            FROM `tabMaterial Request Item` mri
            INNER JOIN `tabBin` bin ON mri.item_code = bin.item_code
                AND bin.warehouse IN %(child_warehouses)s
                AND bin.actual_qty >= 1
            WHERE mri.parent = %(mr_name)s
            GROUP BY mri.item_group
        )
        SELECT
            (SELECT mr_name FROM mr_info) AS mr_name,
            (SELECT target_warehouse FROM mr_info) AS target_warehouse,
            (SELECT source_warehouse FROM mr_info) AS source_warehouse,
            igb.item_group_name AS name,
            CASE
                WHEN COALESCE(ss.is_completed, 0) = 1 THEN 'already_picked'
                WHEN COALESCE(sa.has_stock, 0) = 0 THEN 'no_stock'
                ELSE 'available'
            END AS status,
            COALESCE(cd.crates_json, JSON_ARRAY()) AS crates_json,
            COALESCE(icfs.completed, 0) AS item_count_completed,
            COALESCE(icfs.total, icfm.total, 0) AS item_count_total
        FROM item_groups_base igb
        LEFT JOIN source_status ss ON ss.item_group = igb.item_group_name
        LEFT JOIN stock_availability sa ON sa.item_group = igb.item_group_name
        LEFT JOIN crates_data cd ON cd.item_group = igb.item_group_name
        LEFT JOIN item_counts_from_source icfs ON icfs.item_group = igb.item_group_name
        LEFT JOIN item_counts_from_mr icfm ON icfm.item_group = igb.item_group_name
        """,
        {
            'mr_name': mr_name,
            'user': user,
            'child_warehouses': tuple(child_warehouses),
            'default_set_from_warehouse': default_set_from_warehouse
        },
        as_dict=True
    )
    # Parse results
    if not result:
        raise exceptions.SystemError(f'No data found for Material Request {mr_name}')
    # Build output
    first_row = result[0]
    out = frappe._dict({
        'mr_name': first_row['mr_name'],
        'target_warehouse': first_row['target_warehouse'],
        'source_warehouse': first_row['source_warehouse']
    })
    # Parse crates JSON and build item_count dict for each item group
    item_groups = []
    for row in result:
        item_group = frappe._dict({
            'name': row['name'],
            'status': row['status'],
            'crates': json.loads(row['crates_json']) if row['crates_json'] else [],
            'item_count': frappe._dict({
                'completed': row['item_count_completed'],
                'total': row['item_count_total']
            })
        })
        item_groups.append(item_group)
    out['item_group_availability'] = item_groups
    return out


def get_material_request_picking_view_details(mr_name:str, user:str, item_group:str) -> Dict:
    validations.validate_exists('User', user)
    validations.validate_permission(user, 'picking')
    validations.validate_exists('Material Request', mr_name)
    validations.validate_user_assigned_to_mr(mr_name, user)
    source_name = utils.get_source_name(mr_name, item_group)
    if source_name:
        return utils.get_relevant_source_item(source_name)
    else:
        source = utils.create_source(mr_name, item_group, user)
        return utils.get_relevant_source_item(source.name)


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
) -> Dict:
    validations.validate_scan_params(scanned_qty, crate_code, as_box, as_other, skipped, crates)
    if crate_code:
        validations.validate_exists('Crate', crate_code)
    if crates:
        crates = json.loads(crates)
        crates = [frappe._dict(crate) for crate in crates]
        [validations.validate_exists('Crate', crate.crate_code) for crate in crates]
    validations.validate_exists('User', user)
    validations.validate_permission(user, 'picking')
    validations.validate_exists('Item', item_code)
    validations.validate_exists('Material Request', mr_name)
    validations.validate_user_assigned_to_mr(mr_name, user)
    validations.validate_user_assigned_to_item_group(user, item_group)
    source_name = utils.get_source_name(mr_name, item_group)
    if not source_name:
        raise exceptions.SystemError(
            f"Source for Material Request '{mr_name}' does not exist. Contact IT."
        )
    relevant_item = utils.get_relevant_source_item(source_name) 
    if relevant_item.item_code != item_code:
        raise exceptions.SystemError(
            f"Scanned item '{item_code}' does not match relevant item '{relevant_item.item_code}'. Contact IT."
        )
    doc = frappe.get_doc('Source', source_name)
    settings = utils.get_settings()
    # Default to default set from warehouse if not set on material request
    from_warehouse = frappe.db.get_value(
        'Material Request',
        mr_name,
        'set_from_warehouse'
    ) or settings.default_set_from_warehouse
    to_warehouse = frappe.db.get_value(
        'Material Request',
        mr_name,
        'set_warehouse'
    )
    out = frappe._dict()
    if crate_code:
        out.message = utils.process_scan_as_crate(
            doc,
            crate_code,
            item_code,
            user,
            scanned_qty
        )
    elif crates:
        out.message = utils.process_scan_as_crates(
            doc,
            crates,
            user,
            item_code
        )
    elif as_box:
        identifier_code = utils.create_item_identifier(
            item_code,
            'box',
            user,
            mr_name,
            from_warehouse,
            to_warehouse,
            scanned_qty,
            relevant_item.uom
        )
        out.message = utils.process_scan_as_box(
            doc,
            identifier_code,
            item_code,
            scanned_qty,
            user
        )
    elif as_other:
        identifier_code = utils.create_item_identifier(
            item_code,
            'other',
            user,
            mr_name,
            from_warehouse,
            to_warehouse,
            scanned_qty,
            relevant_item.uom
        )
        out.message = utils.process_scan_as_other(doc,
            identifier_code,
            item_code,
            scanned_qty,
            user
        )
    elif skipped:
        out.message = utils.process_scan_as_skip(
            doc,
            item_code
        )
    # Increment scan pointer
    if not doc.scan_pointer:
        doc.scan_pointer = 0
    doc.scan_pointer += 1
    # When scanning with multiple crates, mark all except the last as closed
    # BEFORE saving. This prevents the "partially fulfilled crate" validation error.
    # We mark them in memory first, then save this Source doc, then close them in other
    # Source docs that may reference these crates.
    crates_to_close = []
    first_crate_data = None
    if crates and len(crates) > 1:
        crates_to_close = [crate.crate_code for crate in crates[:-1]]
        # Mark items as closed in THIS document's memory
        for item_crate in doc.item_crates:
            if item_crate.crate_code in crates_to_close and not item_crate.crate_closed:
                item_crate.crate_closed = 1
                item_crate.crate_closed_timestamp = frappe.utils.now()
    frappe.db.savepoint('process_scan_details')
    try:
        # Save this Source document first with crates marked as closed
        doc.save()
        frappe.db.commit()
        # Now close these crates in OTHER Source documents that reference them
        # We need to do this AFTER our save to avoid double-processing
        if crates_to_close:
            for crate_code in crates_to_close:
                # Query for OTHER Source documents (excluding the one we just saved)
                open_crate_items = frappe.db.get_all('Item Crates',
                    filters={
                        'crate_code': crate_code,
                        'parenttype': 'Source',
                        'crate_closed': '0',
                        'parent': ['!=', doc.name] # Exclude current document
                    },
                    fields=['parent'],
                    distinct=True
                )
                # Only call close_crate if there are OTHER sources with this crate open
                if open_crate_items:
                    try:
                        utils.close_crate(crate_code, commit=True)
                    except exceptions.SystemError as e:
                        # If crate is already closed, that's fine - continue
                        if 'already closed' not in str(e).lower():
                            raise
            # Collect first crate data for verification
            first_crate_code = crates_to_close[0]
            all_crate_items = utils.get_user_crate_details(user, first_crate_code=first_crate_code).get('items') or []
            if all_crate_items:
                first_crate_items = []
                for item in all_crate_items:
                    first_crate_items.append(frappe._dict({
                        'name': item.name,
                        'item_code': item.item_code,
                        'item_name': item.item_name,
                        'uom': item.uom,
                        'requested_qty': item.requested_qty,
                        'from_warehouse': item.from_warehouse,
                        'qty': item.qty,
                        'final_qty': item.qty,
                        'source_name': item.source_name  # Track which source this came from
                    }))
                first_crate_data = frappe._dict({
                    'crate_code': first_crate_code,
                    'from_warehouse': doc.from_warehouse,
                    'to_warehouse': doc.to_warehouse,
                    'items': first_crate_items,
                    'requires_verification': True
                })
    except exceptions.ValidationError as e:
        frappe.db.rollback()
        # Re-raise validation errors with the original message
        # These are user-facing errors that should be displayed as-is
        raise
    except Exception as e:
        frappe.db.rollback()
        # Wrap other exceptions as system errors
        raise exceptions.SystemError(str(e))
    out.complete = utils.source_is_complete(doc)
    out.first_crate_verification = first_crate_data
    return out

 
def get_verification_list(user:str) -> Dict:
    """
    Returns list of crates and identifiers available for verification for a specific user.
    
    Verification items are determined by workflow configuration:
    - Pick → Transit → Receive → Verify: Items must be received first
    - Pick → Verify → Transit → Receive: Items ready after picking (closed crates)
    - Pick → Verify → Receive: Items ready after picking (closed crates)
    
    Only items that require AND are ready for verification are returned.
    """
    validations.validate_exists('User', user)
    # Get settings and check permissions
    settings = utils.get_settings()
    privileged = utils.has_role(user, settings.privileged_user_role)
    if not privileged:
        # Regular users: Restrict to their assigned branch and workflow
        user_branch = utils.get_user_branch(user)
        # Get the target warehouse fot this user's branch
        target_warehouse = utils.get_workflow_target_warehouse(user, user_branch)
        # Get workflow(s) for this target warehouse
        workflows_for_target = utils.get_workflow_details(target_warehouse=target_warehouse)
        # Ensure user has verification permission
        validations.validate_permission(user, 'verification')
        # Check if user's branch is authorized for verification in ANY of the workflows
        # Since workflows is a list, we need to check if user_branch matches ANY workflow
        if isinstance(workflows_for_target, list):
            authorized = any(
                user_branch == wf.verification_branch 
                for wf in workflows_for_target
            )
            if not authorized:
                raise exceptions.PermissionError(
                    f"User '{user}' is not authorized to verify items for {target_warehouse} "
                    f"from '{user_branch}'. Contact Supervisor."
                )
            workflows = workflows_for_target
        else:
            # Single workflow returned
            if user_branch != workflows_for_target.verification_branch:
                raise exceptions.PermissionError(
                    f"User '{user}' is not authorized to verify items for {target_warehouse} "
                    f"from '{user_branch}'. Contact Supervisor."
                )
            workflows = [workflows_for_target]
    else:
        # Privileged users: Get ALL workflows
        workflows = utils.get_workflow_details()
    # Build dynamic SQL conditions for each workflow
    crate_verification_conditions = []
    identifier_verification_conditions = []
    for workflow in workflows:
        target_warehouse = workflow.target_warehouse
        picking_warehouse = workflow.picking_warehouse
        # Base conditions: Items must be headed to the workflow's target warehouse and not yet verified
        base_crate_condition = (
            f"(s.from_warehouse = '{picking_warehouse}' "
            f"AND s.to_warehouse = '{target_warehouse}' "
            f"AND ic.crate_closed = 1 "
            f"AND ic.verified = 0"
        )
        base_identifier_condition = (
            f"(s.from_warehouse = '{picking_warehouse}' "
            f"AND s.to_warehouse = '{target_warehouse}' "
            f"AND ic.verified = 0"
        )
        # Determine verification conditions based on workflow path
        crate_condition = None
        identifier_condition = None
        if workflow.verification_after_receiving:
            # WORKFLOW PATH: Pick → Transit → Receive → Verify
            # Items must be received before verification
            # Items should also be transited (since transit comes before receive)
            crate_condition = (
                f"{base_crate_condition} "
                f"AND ic.transited = 1 "
                f"AND ic.received = 1)"
            )
            identifier_condition = (
                f"{base_identifier_condition} "
                f"AND ic.transited = 1 "
                f"AND ic.received = 1)"
            )
        elif workflow.transit_after_verification:
            # WORKFLOW PATH: Pick → Verify → Transit → Receive
            # Verification happens after picking but before transit
            # Only show items that haven't been transited yet (prevents re-verification)
            crate_condition = (
                f"{base_crate_condition} "
                f"AND ic.transited = 0 "
                f"AND ic.received = 0)"
            )
            identifier_condition = (
                f"{base_identifier_condition} "
                f"AND ic.transited = 0 "
                f"AND ic.received = 0)"
            )
        elif workflow.receiving_after_verification:
            # WORKFLOW PATH: Pick → Verify → Receive (NO TRANSIT)
            # Verification happens after picking but before receiving
            # No transit in this workflow
            crate_condition = (
                f"{base_crate_condition} "
                f"AND ic.received = 0)"
            )
            identifier_condition = (
                f"{base_identifier_condition} "
                f"AND ic.received = 0)"
            )
        else:
            # This should never happen due to validation, but handle it gracefully
            raise exceptions.SystemError(
                f'Invalid workflow configuration for {target_warehouse}. '
                'No verification timing flag is set. Contact IT.'
            )
        # Add conditions if they were properly defined
        if crate_condition:
            crate_verification_conditions.append(crate_condition)
        if identifier_condition:
            identifier_verification_conditions.append(identifier_condition)
    # Combine all workflow conditions with OR
    # This allows privileged users to see items from multiple workflows
    crate_where_clause = ' OR '.join(crate_verification_conditions)
    identifier_where_clause = ' OR '.join(identifier_verification_conditions)
    # Build and execute queries
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
    # Format results
    crate_details = [
        {
            'crate_code': row.crate_code,
            'source_warehouse': row.from_warehouse,
            'target_warehouse': row.to_warehouse
        }
        for row in crate_data
    ]
    identifier_details = [
        {
            'identifier_code': row.identifier_code,
            'source_warehouse': row.from_warehouse,
            'target_warehouse': row.to_warehouse
        }
        for row in identifier_data
    ]
    return {
        'crate_details': crate_details,
        'identifier_details': identifier_details
    }


def process_verification_request(
    user:str,
    items:Any,
    crate_code:str=None,
    identifier_code:str=None
) -> str:
    """
    Process verification request for items in crates or identifiers.
    
    This function:

    - Compares verified quantities against original picked quantities
    - Detects discrepancies (shortages/overdeliveries)
    - Creates Stock Entry adjustments for discrepancies
    - Updates Item Crates records with verification status
    - Logs discrepancies to Source documents
    """
    # ===============================
    # SECTION 1: INITIAL VALIDATION
    # ===============================
    if crate_code and identifier_code:
        raise exceptions.SystemError(
            'Cannot process both crate_code and identifier_code simultaneously. Contact IT.'
        )
    validations.validate_exists('User', user)
    # Determine target warehouse and validate code configuration
    if crate_code:
        validations.validate_exists('Crate', crate_code)
        crate = frappe.get_doc('Crate', crate_code)
        to_warehouse = crate.to_warehouse
        if not to_warehouse:
            raise exceptions.SystemError(
                f"Crate '{crate_code}' has no destination warehouse set. Contact IT."
            )
        if not crate.streams:
            raise exceptions.SystemError(
                f"Crate '{crate_code}' has no streams. Contact IT."
            )
    elif identifier_code:
        validations.validate_exists('Pick Stream Identifier', identifier_code)
        identifier = frappe.get_doc('Pick Stream Identifier', identifier_code)
        to_warehouse = identifier.to_warehouse
        if not to_warehouse:
            raise exceptions.SystemError(
                f"Identifier '{identifier_code}' has no destination warehouse set. Contact IT."
            )
    if isinstance(items, str):
        items = json.loads(items)
    items = [frappe._dict(item) for item in items]
    [validations.validate_exists('Item', item.item_code) for item in items]
    # =================================
    # SECTION 2: PERMISSION VALIDATION
    # =================================
    settings = utils.get_settings()
    workflow_details = utils.get_workflow_details(to_warehouse, settings)
    # Check if user is privileged (can verify from any branch)
    if not utils.has_role(user, settings.privileged_user_role):
        # Regular user: validate they have verification permission
        validations.validate_permission(user, 'verification')
        # Ensure user's branch is authorized to verify for this workflow
        user_branch = utils.get_user_branch(user)
        if user_branch not in workflow_details.verification_branches:
            raise exceptions.PermissionError(
                f"User '{user}' is not authorized to verify items for {to_warehouse} from '{user_branch}'. Contact Supervisor."
            )
    # =====================================
    # SECTION 3: DATA COLLECTION & MAPPING
    # =====================================
    # Initialize tracking structures
    all_updated_items = []      # Track items where qty changed during verification
    all_discrepancies = []      # Track all discrepancies found
    overdelivery_items = []     # Track items exceeding requested quantity
    source_item_mapping = {}    # Map source -> list of items with original quantities
    original_qty_mapping = {}   # Map item_code -> total original qty across all sources
    requested_qty_mapping = {}  # Map item_code -> originally requested qty from Material Request
    # Create lookup dict of verified quantities by item code
    verified_items = {item.item_code: int(item.qty) for item in items}
    # Discover source documents containing the crate/identifier items
    if crate_code:
        # For crates: get sources via Stream doctype
        source_names = set(
            frappe.db.get_value('Stream', row.stream, 'source') 
            for row in crate.streams
        )
    elif identifier_code:
        # For identifiers: get source directly from Item Crates parent
        source_names = [
            frappe.db.get_value(
                'Item Crates', 
                {'identifier_code': identifier_code}, 
                'parent'
            )
        ]
    # Pre-load all source documents
    source_docs = {}
    for source in source_names:
        source_doc = frappe.get_doc('Source', source)
        source_docs[source] = source_doc
    # Collect all related Material Requests
    material_requests = set()
    for source in source_names:
        material_requests.add(source_docs[source].material_request)
    # Build requested quantity mapping from Material Requests
    # This represents what was originally ordered
    for mr_name in material_requests:
        mr_doc = frappe.get_doc('Material Request', mr_name)
        for item in mr_doc.items:
            if item.item_code not in requested_qty_mapping:
                requested_qty_mapping[item.item_code] = 0
            requested_qty_mapping[item.item_code] += item.qty
    # Build source-item mapping with original picked quantities
    for source in source_names:
        source_doc = source_docs[source]
        source_item_mapping[source] = []
        for item_crate in source_doc.item_crates:
            # Filter items belonging to the crate/identifier being verified
            if crate_code and item_crate.crate_code == crate_code:
                item_code = item_crate.item_code
                # Build mapping entry
                source_item_mapping[source].append({
                    'item_code': item_code,
                    'item_crate': item_crate.name,
                    'original_qty': item_crate.qty
                })
                # Aggregate original quantity across all sources
                if item_code not in original_qty_mapping:
                    original_qty_mapping[item_code] = 0
                original_qty_mapping[item_code] += item_crate.qty
            elif identifier_code and item_crate.identifier_code == identifier_code:
                item_code = item_crate.item_code
                # Build mapping entry
                source_item_mapping[source].append({
                    'item_code': item_code,
                    'item_crate': item_crate.name,
                    'original_qty': item_crate.qty
                })
                # Aggregate original quantity
                if item_code not in original_qty_mapping:
                    original_qty_mapping[item_code] = 0
                original_qty_mapping[item_code] += item_crate.qty
    # =================================
    # SECTION 4: DISCREPANCY DETECTION
    # =================================
    # Compare verified quantities against original quantities
    for item_code, verified_qty in verified_items.items():
        original_qty = original_qty_mapping.get(item_code, 0)
        requested_qty = requested_qty_mapping.get(item_code, 0)
        # Discrepancy detected if verified != original
        if verified_qty != original_qty:
            all_discrepancies.append(frappe._dict({
                'item_code': item_code,
                'verified_qty': verified_qty,
                'original_qty': original_qty,
                'requested_qty': requested_qty
            }))
        # Track overdelivery (verified > requested)
        if verified_qty > requested_qty:
            overdelivery_items.append(frappe._dict({
                'item_code': item_code,
                'overdelivery_qty': verified_qty - requested_qty,
                'verified_qty': verified_qty,
                'requested_qty': requested_qty
            }))
    # ==========================================================
    # SECTION 5: QUANTITY DISTRIBUTION & ADJUSTMENT CALCULATION
    # ==========================================================
    frappe.db.savepoint('process_verification_request')
    try:
        verified_qty_updates = {}   # Track new quantities to update per source
        adjustment_entries = []     # Track Stock Entries created for adjustments
        # Process discrepancies: distribute verified qty proportionally across sources
        for discrepancy in all_discrepancies:
            item_code = discrepancy.item_code
            verified_qty = discrepancy.verified_qty
            original_qty = discrepancy.original_qty
            requested_qty = discrepancy.requested_qty
            # During verification, we record ACTUAL physical quantities
            # We do NOT cap at requested quantity - that happens later during receiving
            # The verified_qty field must reflect what was physically counted
            fulfillment_qty = verified_qty
            # Find all sources containing this item
            sources_with_item = []
            for source_name, items in source_item_mapping.items():
                for item_data in items:
                    if item_data['item_code'] == item_code:
                        sources_with_item.append(frappe._dict({
                            'source_name': source_name,
                            'item_crate': item_data['item_crate'],
                            'original_qty': item_data['original_qty']
                        }))
            # Distribute verified quantity proportionally across sources
            # This is necessary because we can't determine which specific source
            # had the discrepancy when one crate spans multiple sources
            remaining_fulfillment_qty = fulfillment_qty
            for i, source_item in enumerate(sources_with_item):
                if i == len(sources_with_item) - 1:
                    # Last source gets remaining quantity (handles rounding)
                    new_qty = remaining_fulfillment_qty
                else:
                    # Calculate proportional quantity
                    proportion = source_item.original_qty / original_qty
                    new_qty = int(fulfillment_qty * proportion)
                    remaining_fulfillment_qty -= new_qty
                # Store calculated quantity for this source
                source_name = source_item.source_name
                if source_name not in verified_qty_updates:
                    verified_qty_updates[source_name] = {}
                verified_qty_updates[source_name][item_code] = new_qty
                # Track that this item was updated
                if new_qty != source_item.original_qty:
                    all_updated_items.append(f'{item_code} in {source_name}')
        # ======================================================
        # SECTION 6: CREATE STOCK ADJUSTMENTS FOR DISCREPANCIES
        # ======================================================
        # Group adjustments by source and warehouse for Stock Entry creation
        adjustment_by_source_warehouse = {}
        for source_name in source_names:
            source_doc = source_docs[source_name]
            for item_crate in source_doc.item_crates:
                should_process = (
                    (crate_code and item_crate.crate_code == crate_code) or
                    (identifier_code and item_crate.identifier_code == identifier_code)
                )
                if not should_process:
                    continue
                # Check if this item had a quantity adjustment
                if (source_name in verified_qty_updates and 
                    item_crate.item_code in verified_qty_updates[source_name]):
                    new_qty = verified_qty_updates[source_name][item_crate.item_code]
                    qty_diff = new_qty - item_crate.qty
                    # Only create adjustment if there's a difference
                    if qty_diff != 0:
                        # Get source item for UOM and warehouse info
                        source_item = next(
                            (item for item in source_doc.items 
                             if item.name == item_crate.source_item),
                            None
                        )
                        if not source_item:
                            raise exceptions.SystemError(
                                f"Source item '{item_crate.source_item}' not found. Contact IT."
                            )
                        warehouse = source_item.from_warehouse
                        adjustment_key = f'{source_name}|{warehouse}'
                        # Initialize adjustment tracking for this source-warehouse combination
                        if adjustment_key not in adjustment_by_source_warehouse:
                            adjustment_by_source_warehouse[adjustment_key] = {
                                'source_name': source_name,
                                'warehouse': warehouse,
                                'items': []
                            }
                        # Add item to adjustment list
                        adjustment_by_source_warehouse[adjustment_key]['items'].append({
                            'item_code': item_crate.item_code,
                            'qty': abs(qty_diff),
                            'uom': source_item.uom,
                            'is_receipt': qty_diff > 0,  # True for shortages, False for overages
                            'item_crate_name': item_crate.name
                        })
        # Create Stock Entry documents for adjustments
        for adjustment_key, adjustment_data in adjustment_by_source_warehouse.items():
            source_name = adjustment_data['source_name']
            warehouse = adjustment_data['warehouse']
            items = adjustment_data['items']
            # Group by adjustment type (receipts vs issues)
            receipts = [item for item in items if item['is_receipt']]
            issues = [item for item in items if not item['is_receipt']]
            # Create Stock Entry for receipts (verified qty > original qty)
            if receipts:
                receipt_entry = frappe.new_doc('Stock Entry')
                receipt_entry.update({
                    'stock_entry_type': 'Material Receipt',
                    'purpose': 'Material Receipt',
                    'to_warehouse': warehouse,
                    'remarks': (
                        f'Verification adjustment (shortage) for '
                        f'{crate_code if crate_code else identifier_code} '
                        f'(Source: <a href="/app/source/{source_name}">{source_name}</a>)'
                    )
                })
                # Track the index position of each item as we append
                # We'll use this to get the correct detail row after insert
                item_crate_to_index = {}
                for idx, item in enumerate(receipts):
                    receipt_entry.append('items', {
                        'item_code': item['item_code'],
                        't_warehouse': warehouse,
                        'qty': item['qty'],
                        'uom': item['uom']
                    })
                    # Store the index position
                    item_crate_to_index[item['item_crate_name']] = idx
                receipt_entry.insert()
                receipt_entry.submit()
                receipt_entry.add_comment('Info', (
                    f'Verification adjustment (shortage) for '
                    f'{crate_code if crate_code else identifier_code} '
                    f'(Source: <a href="/app/source/{source_name}">{source_name}</a>)'
                ))
                adjustment_entries.append(receipt_entry.name)
                # Update Item Crates with adjustment reference
                for item_crate_name, idx in item_crate_to_index.items():
                    detail_row = receipt_entry.items[idx]
                    for source_name in source_names:
                        source_doc = source_docs[source_name]
                        matching_item_crate = next(
                            (ic for ic in source_doc.item_crates 
                            if ic.name == item_crate_name),
                            None
                        )
                        if matching_item_crate:
                            # Update the IN-MEMORY object
                            matching_item_crate.adjustment_stock_entry = receipt_entry.name
                            matching_item_crate.adjustment_stock_entry_detail = detail_row.name
                            break 
            # Create Stock Entry for issues (verified qty < original qty)
            if issues:
                issue_entry = frappe.new_doc('Stock Entry')
                issue_entry.update({
                    'stock_entry_type': 'Material Issue',
                    'purpose': 'Material Issue',
                    'from_warehouse': warehouse,
                    'remarks': (
                        f'Verification adjustment (overage) for '
                        f'{crate_code if crate_code else identifier_code} '
                        f'(Source: <a href="/app/source/{source_name}">{source_name}</a>)'
                    )
                })
                # Track the index position of each item as we append
                # We'll use this to get the correct detail row after insert
                item_crate_to_index = {}
                for idx, item in enumerate(issues):
                    detail_row = issue_entry.append('items', {
                        'item_code': item['item_code'],
                        's_warehouse': warehouse,
                        'qty': item['qty'],
                        'uom': item['uom']
                    })
                   # Store the index position
                    item_crate_to_index[item['item_crate_name']] = idx
                issue_entry.insert()
                issue_entry.submit()
                issue_entry.add_comment('Info', (
                    f'Verification adjustment (overage) for '
                    f'{crate_code if crate_code else identifier_code} '
                    f'(Source: <a href="/app/source/{source_name}">{source_name}</a>)'
                ))
                adjustment_entries.append(issue_entry.name)
                # Update Item Crates with adjustment reference
                for item_crate_name, idx in item_crate_to_index.items():
                    detail_row = issue_entry.items[idx]
                    for source_name in source_names:
                        source_doc = source_docs[source_name]
                        matching_item_crate = next(
                            (ic for ic in source_doc.item_crates 
                            if ic.name == item_crate_name),
                            None
                        )
                        if matching_item_crate:
                            # Update the IN-MEMORY object
                            matching_item_crate.adjustment_stock_entry = issue_entry.name
                            matching_item_crate.adjustment_stock_entry_detail = detail_row.name
                            break 
        # =================================================
        # SECTION 7: UPDATE ITEM CRATES & SOURCE DOCUMENTS
        # =================================================
        # Update Item Crates records with verification status and quantities
        for source_name in source_names:
            source_doc = source_docs[source_name]
            source_discrepancies = []
            for item_crate in source_doc.item_crates:
                should_update = (
                    (crate_code and item_crate.crate_code == crate_code) or
                    (identifier_code and item_crate.identifier_code == identifier_code)
                )
                if should_update:
                    # Mark as verified
                    item_crate.verified = True
                    item_crate.verifying_user = user
                    item_crate.verified_timestamp = frappe.utils.now()
                    # Update verified_qty if discrepancy exists
                    if (source_name in verified_qty_updates and 
                        item_crate.item_code in verified_qty_updates[source_name]):
                        new_qty = verified_qty_updates[source_name][item_crate.item_code]
                        item_crate.verified_qty = new_qty
                        # Log discrepancy for this source
                        if new_qty != item_crate.qty:
                            source_discrepancies.append(
                                f'Item {item_crate.item_code}: {item_crate.qty} → {new_qty} '
                                f'(diff: {new_qty - item_crate.qty:+d})'
                            )
                    else:
                        # No discrepancy: verified_qty equals original qty
                        item_crate.verified_qty = item_crate.qty
            # Add discrepancy notes to Source document for audit trail
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
        # ========================================
        # SECTION 8: LOG OVERDELIVERY INFORMATION
        # ========================================
        # Log overdelivery items for supervisor review
        if overdelivery_items:
            overdelivery_summary = []
            for item in overdelivery_items:
                overdelivery_summary.append(
                    f'{item.item_code}: +{item.overdelivery_qty} units '
                    f'(requested: {item.requested_qty}, verified: {item.verified_qty})'
                )
            # TODO: This is to be emailed rather than logged
            frappe.log_error(
                title=f'Overdelivery Detected: {crate_code if crate_code else identifier_code}',
                message=(
                    f'User: {user}\n'
                    f'Code: {crate_code if crate_code else identifier_code}\n'
                    f'Overdelivered Items:\n' + 
                    '\n'.join(overdelivery_summary)
                )
            )
        # ============================================================================
        # SECTION 9: RETURN SUCCESS MESSAGE
        # ============================================================================
        # Build success message with details
        success_msg = f'Verification successful for {crate_code if crate_code else identifier_code}.'
        if all_discrepancies:
            success_msg += f' {len(all_discrepancies)} discrepancy/discrepancies found and adjusted.'
        if adjustment_entries:
            success_msg += f' {len(adjustment_entries)} adjustment entry/entries created.'
        return success_msg
    except Exception as e:
        frappe.db.rollback()
        raise exceptions.ValidationError(f'Error during verification: {str(e)}')


def get_transit_list(user: str):
    """
    Returns list of crates and identifiers available for transit for a specific user.
    
    Transit items are determined by workflow configuration:
    - Pick → Transit → Receive → Verify: Items ready after picking (closed crates)
    - Pick → Verify → Transit → Receive: Items ready after verification
    - Pick → Verify → Receive: NO transit (skip these workflows)
    
    Only items that require AND are ready for transit are returned.
    """
    validations.validate_exists('User', user)
    # Get settings and check permissions
    settings = utils.get_settings()
    privileged = utils.has_role(user, settings.privileged_user_role)
    if not privileged:
        # Regular users must have transit permission
        validations.validate_permission(user, 'transit')
    # Get all active workflows
    workflows = utils.get_workflow_details(settings=settings)
    crate_transit_conditions = []
    identifier_transit_conditions = []
    for workflow in workflows:
        target_warehouse = workflow.target_warehouse
        picking_warehouse = workflow.picking_warehouse
        # Determine if this workflow includes transit stage
        # Only two workflow paths include transit:
        if workflow.verification_after_receiving:
            # WORKFLOW PATH: Pick → Transit → Receive → Verify
            # Transit happens AFTER picking but BEFORE receiving/verification
            # Items must be: closed, not verified, not transited, not received
            crate_transit_conditions.append(
                f"(s.from_warehouse = '{picking_warehouse}' "
                f"AND s.to_warehouse = '{target_warehouse}' "
                f"AND ic.crate_closed = 1 "
                f"AND ic.verified = 0 "
                f"AND ic.transited = 0 "
                f"AND ic.received = 0)"
            )
            identifier_transit_conditions.append(
                f"(s.from_warehouse = '{picking_warehouse}' "
                f"AND s.to_warehouse = '{target_warehouse}' "
                f"AND ic.verified = 0 "
                f"AND ic.transited = 0 "
                f"AND ic.received = 0)"
            )
        elif workflow.transit_after_verification:
            # WORKFLOW PATH: Pick → Verify → Transit → Receive
            # Transit happens AFTER verification but BEFORE receiving
            # Items must be: closed, verified, not transited, not received
            crate_transit_conditions.append(
                f"(s.from_warehouse = '{picking_warehouse}' "
                f"AND s.to_warehouse = '{target_warehouse}' "
                f"AND ic.crate_closed = 1 "
                f"AND ic.verified = 1 "
                f"AND ic.transited = 0 "
                f"AND ic.received = 0)"
            )
            identifier_transit_conditions.append(
                f"(s.from_warehouse = '{picking_warehouse}' "
                f"AND s.to_warehouse = '{target_warehouse}' "
                f"AND ic.verified = 1 "
                f"AND ic.transited = 0 "
                f"AND ic.received = 0)"
            )
        elif workflow.receiving_after_verification:
            # WORKFLOW PATH: Pick → Verify → Receive
            # NO TRANSIT in this workflow! Items go directly from verify to receive
            # Skip adding conditions for this workflow
            pass
        else:
            # This should never happen due to validation, but handle it gracefully
            raise exceptions.SystemError(
                f'Invalid workflow configuration for {target_warehouse}. '
                'No workflow timing flag is set. Contact IT.'
            )
    # If no workflows have transit, return empty lists
    if not crate_transit_conditions and not identifier_transit_conditions:
        return {
            'crate_details': [],
            'identifier_details': []
        }
    # Build and execute queries
    crate_data = []
    identifier_data = []
    if crate_transit_conditions:
        crate_where_clause = ' OR '.join(crate_transit_conditions)
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
        crate_data = frappe.db.sql(crate_query, as_dict=True)
    if identifier_transit_conditions:
        identifier_where_clause = ' OR '.join(identifier_transit_conditions)
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
        identifier_data = frappe.db.sql(identifier_query, as_dict=True)
    # Format results
    crate_details = [
        {
            'crate_code': row.crate_code,
            'source_warehouse': row.from_warehouse,
            'target_warehouse': row.to_warehouse
        }
        for row in crate_data
    ]
    identifier_details = [
        {
            'identifier_code': row.identifier_code,
            'source_warehouse': row.from_warehouse,
            'target_warehouse': row.to_warehouse
        }
        for row in identifier_data
    ]
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
        raise exceptions.SystemError('At least one of crate_codes or identifier_codes must be provided for transit processing')

    validations.validate_exists('User', user)
    validations.validate_exists('Warehouse', to_warehouse)
    validations.validate_exists('Warehouse', from_warehouse)

    if crate_codes:
        crate_codes = utils.parse_codes(crate_codes)
        [validations.validate_exists('Crate', crate_code) for crate_code in crate_codes]
    
    if identifier_codes:
        identifier_codes = utils.parse_codes(identifier_codes)
        [validations.validate_exists('Pick Stream Identifier', identifier_code) for identifier_code in identifier_codes]

    workflow_details = utils.get_workflow_details(to_warehouse)
    
    transit_required = utils.check_transit_required(workflow_details.picking_warehouse_stores, from_warehouse, to_warehouse)
    if not transit_required:
        raise exceptions.SystemError(
            f"Transit is not required from '{from_warehouse}' to '{to_warehouse}'. Contact IT."
        )

    if not utils.has_role(user, 'Stock Manager'):
        validate_role(user, workflow_details.transit_user_role)

    source_list = []
    
    for crate_code in crate_codes:
        crate_doc = frappe.get_doc('Crate', crate_code)
        
        if crate_doc.to_warehouse != to_warehouse:
            raise exceptions.SystemError(f"Crate '{crate_code}' destination is '{crate_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")
        
        if crate_doc.from_warehouse != from_warehouse:
            raise exceptions.SystemError(f"Crate '{crate_code}' origin is '{crate_doc.from_warehouse}', not '{from_warehouse}'. Contact IT.")
        
        if not crate_doc.streams:
            raise exceptions.SystemError(f"Crate '{crate_code}' has no streams. Contact IT.")

        if not crate_doc.item_groups:
            raise exceptions.SystemError(f"Crate '{crate_code}' has no item groups. Contact IT.")

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
            raise exceptions.SystemError(f"Identifier '{identifier_code}' destination is '{identifier_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")

        if identifier_doc.from_warehouse != from_warehouse:
            raise exceptions.SystemError(f"Identifier '{identifier_code}' origin is '{identifier_doc.from_warehouse}', not '{from_warehouse}'. Contact IT.")

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
                raise exceptions.SystemError(
                    f"Crate '{crate_code}' has unclosed items in source '{source}'. Contact IT."
                )

            # If workflow requires verification for transit, items must be verified
            if workflow_details.transit_after_verification:
                if any(not item.verified for item in crate_items):
                    raise exceptions.SystemError(
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
                    raise exceptions.SystemError(
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
                    raise exceptions.SystemError(
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
                    raise exceptions.SystemError(
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
        raise exceptions.ValidationError(f'Error during transit: {str(e)}')


def get_receiving_list(user: str) -> Dict:
    """
    Returns list of crates and identifiers available for receiving for a specific user.
    
    Receiving items are determined by workflow configuration:
    - Pick → Transit → Receive → Verify: Items must be transited first, not verified
    - Pick → Verify → Transit → Receive: Items must be verified and transited
    - Pick → Verify → Receive: Items must be verified (no transit required)
    
    Only items that are ready for receiving based on their workflow are returned.
    """
    validations.validate_exists('User', user)
    # Check user permissions
    settings = utils.get_settings()
    stock_manager = utils.has_role(user, 'Stock Manager')
    if not stock_manager:
        # Regular users: Restrict to their assigned branch and workflow
        user_branch = utils.get_user_branch(user)
        target_warehouse = utils.get_workflow_target_warehouse(user, user_branch)
        # Get workflow(s) for this target warehouse
        workflows_for_target = utils.get_workflow_details(target_warehouse=target_warehouse, settings=settings)
        # Validate user has receiving role
        validations.validate_permission(user, 'receiving')
        # Convert to list if single workflow returned
        if isinstance(workflows_for_target, list):
            workflows = workflows_for_target
        else:
            workflows = [workflows_for_target]
    else:
        # Stock Managers: Get ALL workflows (privileged access)
        workflows = utils.get_workflow_details()
    # Build dynamic SQL conditions for each workflow
    crate_receiving_conditions = []
    identifier_receiving_conditions = []
    for workflow in workflows:
        target_warehouse = workflow.target_warehouse
        picking_warehouse = workflow.picking_warehouse
        # Base conditions: Items headed to target warehouse, closed (for crates), not received
        base_crate_condition = (
            f"(s.from_warehouse = '{picking_warehouse}' "
            f"AND s.to_warehouse = '{target_warehouse}' "
            f"AND ic.crate_closed = 1 "
            f"AND ic.received = 0"
        )
        base_identifier_condition = (
            f"(s.from_warehouse = '{picking_warehouse}' "
            f"AND s.to_warehouse = '{target_warehouse}' "
            f"AND ic.received = 0"
        )
        # Determine receiving conditions based on workflow path
        crate_condition = None
        identifier_condition = None
        if workflow.verification_after_receiving:
            # WORKFLOW PATH: Pick → Transit → Receive → Verify
            # Items must be transited, not verified, not received
            # Verification happens AFTER receiving, so we show unverified items
            crate_condition = (
                f"{base_crate_condition} "
                f"AND ic.transited = 1 "
                f"AND ic.verified = 0)"
            )
            identifier_condition = (
                f"{base_identifier_condition} "
                f"AND ic.transited = 1 "
                f"AND ic.verified = 0)"
            )
        elif workflow.transit_after_verification:
            # WORKFLOW PATH: Pick → Verify → Transit → Receive
            # Items must be verified, transited, not received
            # Verification happened before transit
            crate_condition = (
                f"{base_crate_condition} "
                f"AND ic.verified = 1 "
                f"AND ic.transited = 1)"
            )
            identifier_condition = (
                f"{base_identifier_condition} "
                f"AND ic.verified = 1 "
                f"AND ic.transited = 1)"
            )
        elif workflow.receiving_after_verification:
            # WORKFLOW PATH: Pick → Verify → Receive (NO TRANSIT!)
            # Items must be verified, no transit required, not received
            # Transit is not part of this workflow
            crate_condition = (
                f"{base_crate_condition} "
                f"AND ic.verified = 1)"
            )
            identifier_condition = (
                f"{base_identifier_condition} "
                f"AND ic.verified = 1)"
            )
        else:
            # This should never happen due to validation, but handle it gracefully
            raise exceptions.SystemError(
                f'Invalid workflow configuration for {target_warehouse}. '
                'No workflow timing flag is set. Contact IT.'
            )
        # Add conditions if they were properly defined
        if crate_condition:
            crate_receiving_conditions.append(crate_condition)
        if identifier_condition:
            identifier_receiving_conditions.append(identifier_condition)
    # If no receiving conditions, return empty lists
    if not crate_receiving_conditions:
        return {
            'crate_details': [],
            'identifier_details': []
        }
    # Combine all workflow conditions with OR
    crate_where_clause = ' OR '.join(crate_receiving_conditions)
    identifier_where_clause = ' OR '.join(identifier_receiving_conditions)
    # Build and execute queries
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
    # Format results
    crate_details = [
        {
            'crate_code': row.crate_code,
            'source_warehouse': row.from_warehouse,
            'target_warehouse': row.to_warehouse
        }
        for row in crate_data
    ]
    identifier_details = [
        {
            'identifier_code': row.identifier_code,
            'source_warehouse': row.from_warehouse,
            'target_warehouse': row.to_warehouse
        }
        for row in identifier_data
    ]
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
    validations.validate_exists('User', user)
    validations.validate_exists('Warehouse', to_warehouse)
    validations.validate_exists('Warehouse', from_warehouse)

    code = code.strip().strip('"').strip("'")
    
    crate_code = False
    identifier_code = False
    
    try:
        validations.validate_exists('Crate', code)
        crate_code = True
        filter_field = 'crate_code'
        code_doc = frappe.get_doc('Crate', code)

    except exceptions.DoesNotExistError:
        try:
            validations.validate_exists('Pick Stream Identifier', code)
            identifier_code = True
            filter_field = 'identifier_code'
            code_doc = frappe.get_doc('Pick Stream Identifier', code)

        except exceptions.DoesNotExistError:
            raise exceptions.DoesNotExistError(f'Code {code} not found.')
    
    workflow_details = utils.get_workflow_details(to_warehouse)
    if not utils.has_role(user, 'Stock Manager'):
        # TODO: Create global receiving role rather than basing it off workflow
        validate_role(user, workflow_details.receiving_user_role)

    # Check if transit was required based on from and to warehouse
    transit_required = utils.check_transit_required(workflow_details.picking_warehouse_stores, from_warehouse, to_warehouse)

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
                    raise exceptions.ValidationError(
                        f"Crate '{code}' cannot be received. Crate must be verified and transited."
                    )

                else:
                    raise exceptions.ValidationError(
                        f"Crate '{code}' cannot be received. Crate must be transited."
                    )
                    
            else:  # identifier_code
                if workflow_details.transit_after_verification:
                    raise exceptions.ValidationError(
                        f"Identifier '{code}' cannot be received. Items must be verified and transited."
                    )
                    
                else:
                    raise exceptions.ValidationError(
                        f"Identifier '{code}' cannot be received. Items must be transited."
                    )
                    
        else:
            if crate_code:
                raise exceptions.ValidationError(
                    f"Crate '{code}' cannot be received. Crate is not verified or closed."
                )
                
            else:  # identifier_code
                raise exceptions.ValidationError(
                    f"Identifier '{code}' cannot be received. Items are not verified."
                )
            
    if code_doc.to_warehouse != to_warehouse:
        raise exceptions.SystemError(f"Code '{crate_code}' destination is '{code_doc.to_warehouse}', not '{to_warehouse}'. Contact IT.")

    if code_doc.doctype == 'Crate':
        if not code_doc.streams:
            raise exceptions.SystemError(f"Crate '{crate_code}' has no streams. Contact IT.")

        if not code_doc.item_groups:
            raise exceptions.SystemError(f"Crate '{crate_code}' has no item groups. Contact IT.")

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
            raise exceptions.SystemError(f"No items found for code '{crate_code}' in source '{source}'. Contact IT.")
        
        for row in code_items:
            source_item = next((item for item in source_doc.items if item.name == row.source_item), None)
            if not source_item:
                raise exceptions.SystemError(f"Source item '{row.source_item}' not found in source '{source}'. Contact IT.")
            
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
            raise exceptions.SystemError(f"Stock entry discrepancy in source '{source}'. Contact IT.")

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
        raise exceptions.ValidationError(f'Error during receiving: {str(e)}')