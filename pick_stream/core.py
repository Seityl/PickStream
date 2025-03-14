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
    if not frappe.db.exists("ToDo", {
        "allocated_to": user,
        "reference_name": mr_name,
        "status": "Open"
    }):
        e = frappe.exceptions.DoesNotExistError(f"ToDo for user {user} to MR {mr_name} not found")
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
    try:
        parent = frappe.db.get_value('Item Barcode', {'barcode':barcode}, 'parent')
        if parent != item_code:
            return False
        return True
        
    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

def check_crate_availability(crate_code:str) -> bool:
    """Validates crate existence then returns True if crate is available and False if crate is not"""
    try:
        validate_exists('Crate', crate_code)
        crate_status = frappe.get_value('Crate', crate_code, 'status')
        if crate_status != 'Available':
            return False
        return True
        
    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

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

def get_mr_item_groups_for_user(mr_name:str, user:str) -> list:
    try:
        user_item_groups = get_assigned_item_groups(user)
        mr_groups = frappe.get_all(
            "Material Request Item",
            filters={"parent": mr_name, "item_group": ["in", user_item_groups]},
            pluck="item_group",
            distinct=True
        )
        for mr_group in mr_groups:
            validate_user_assigned_to_item_group(user, mr_group)
        return mr_groups

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

# TODO: Have this also check based on the ordered qty for mr items
def get_mr_available_item_groups_for_user(mr_name:str, user:str) -> dict:
    """Returns item groups which don't already have completed stream for material request"""
    out = {}
    try:
        user_item_groups = get_mr_item_groups_for_user(mr_name, user)
        for item_group in user_item_groups:
            if frappe.db.exists('Stream', {
                'item_group': item_group, 
                'material_request': mr_name,
                'status': ['!=', 'Picking']
                }):
                out[item_group] = False
            else:
                out[item_group] = True

        return out            

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

# TODO: Have this also check based on already created streams for mr
def get_user_material_requests(user:str) -> dict:
    validate_exists('User', user)
    user_item_groups = get_assigned_item_groups(user)
    warehouse_group = get_warehouse_group(user)
    child_warehouses = get_child_warehouses(warehouse_group)
    try:
        mr_list = frappe.db.sql(
            """
                SELECT 
                    mr.name,
                    mr.set_warehouse AS target_warehouse,
                    mr.set_from_warehouse AS source_warehouse,
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
                "user": user,
                "user_item_groups": tuple(user_item_groups),
                "child_warehouses": tuple(child_warehouses)
            },
            as_dict=True
        ) or {}
        
        for mr in mr_list:
            mr_name = mr.get("name")
            validate_exists('Material Request', mr_name)
            availability = get_mr_available_item_groups_for_user(mr_name, user)
            mr["item_group_availability"] = availability
        
        return mr_list

    except Exception as e:
        return exception_handler(e)

def get_material_request_item_groups_view_details(mr_name:str, user:str) -> dict:
    validate_exists('User', user)
    validate_exists('Material Request', mr_name)
    validate_user_assigned_to_mr(mr_name, user)
    try:
        out = frappe.db.sql(
            """
                SELECT 
                    mr.name AS mr_name,
                    mr.set_warehouse AS target_warehouse,
                    mr.set_from_warehouse AS source_warehouse
                FROM `tabMaterial Request` mr
                WHERE
                    mr.name = %(mr_name)s
            """, { 
                'mr_name': mr_name
            },
            as_dict=True
        )[0]
        out['item_group_availability'] = get_mr_available_item_groups_for_user(mr_name, user)
        return out
    
    except Exception as e:
        return exception_handler(e)

def get_material_request_item_group_view_details(mr_name:str, user:str, item_group:str) -> dict:
    validate_exists('User', user)
    validate_exists('Material Request', mr_name)
    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, item_group)
    try:
        out = frappe.db.sql(
            """
            SELECT 
                mr.name,
                mr.set_warehouse AS target_warehouse,
                mr.set_from_warehouse AS source_warehouse,
                JSON_ARRAYAGG(
                    JSON_OBJECT(
                        'crate_code', ps.crate_code,
                        'item_group', ps.item_group,
                        'status', ps.status
                    )
                ) AS crates
            FROM `tabMaterial Request` mr
            LEFT JOIN `tabStream` ps
                ON mr.name = ps.material_request
            WHERE
                mr.name = %(mr_name)s
            """, {
                "mr_name": mr_name
            },
            as_dict=True
        )[0] or {}

        if out:
            out['item_group'] = item_group
            
        return out
    
    except Exception as e:
        return exception_handler(e)

@frappe.whitelist()
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
    try:
        user_item_groups = frappe.get_all(
            "User Group",
            filters={
                "custom_is_item_group": 1,
                "name": ["in", frappe.get_all(
                    "User Group Member",
                    filters={"parenttype": "User Group", "user": user},
                    pluck="parent"
                )]
            },
            fields=["name"],
            pluck="name",
            distinct=True
        )
        if not user_item_groups:
            e = frappe.exceptions.ValidationError(f"User '{user}' has no assigned item groups. Contact IT.")
            frappe.response = exception_handler(e)   
            raise e

        return user_item_groups

    except Exception as e:
        return exception_handler(e)

def get_user_branch(user:str) -> str:
    """Returns employee branch based on user"""
    validate_employee_exists(user)
    branch = frappe.db.get_value("Employee", {"user_id": user}, ["branch"])
    if not branch:
        e = frappe.exceptions.ValidationError(f"Employee for user '{user}' has no branch")
        frappe.response = exception_handler(e)   
        raise e

    return branch

def get_warehouse_group(user:str) -> str:
    user_branch = get_user_branch(user)
    match user_branch:
        case 'King George':
            return 'KG Warehouse - JP'
        case 'JP Mega':
            return 'JP Mega - JP'
        case _:
            e = frappe.exceptions.ValidationError(f"Employee for user '{user}' branch is not set to 'King George' or 'JP Mega'.")
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

def get_material_request_picking_view_details(mr_name:str, user:str, item_group:str) -> dict:
    try:
        if check_source_exists(mr_name, item_group, user):
            source_name = get_source_name(mr_name, item_group, user)
            return get_relevant_source_item(source_name)

        else:
            source = create_source(mr_name, item_group, user)
            return get_relevant_source_item(source.name)
            
    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

def get_relevant_source_item(source_name:str) -> dict:
    try:
        out = frappe._dict()
        doc = frappe.get_doc('Source', source_name)
        for item in doc.items:
            if not item.scanned:
                out['item_code'] = item.item_code
                out['description'] = item.description
                out['requested_qty'] = item.requested_qty
                out['uom'] = item.uom
                out['from_warehouse'] = item.from_warehouse
                return out

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

def get_pick_stream_settings() -> dict:
    return frappe.get_doc('Pick Stream Settings') 
    
def create_source(mr_name:str, item_group:str, user:str) -> dict:
    source = frappe.new_doc('Source')
    source.update({
        'material_request': mr_name,
        'item_group': item_group,
        'user': user
    })
    items = get_material_request_items_details(mr_name, user, item_group)

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
            'available_qty': item.get('available_qty'),
            'material_request': item.get('material_request'),
            'material_request_item': item.get('material_request_item')
        })

    frappe.db.savepoint('sp')

    try:
        source.insert()
        frappe.db.commit()
        return source

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e

def process_scan_details(
        user:str,
        mr_name:str,
        item_code:str,
        item_group:str,
        crate_code:str,
        scanned_qty:int,
        skipped:bool = False
    ) -> dict:
    out = frappe._dict()
    out['success'] = True

    validate_exists('User', user)
    validate_exists('Item', item_code)
    validate_exists('Crate', crate_code)
    validate_exists('Item Group', item_group)
    validate_exists('Material Request', mr_name)

    validate_user_assigned_to_mr(mr_name, user)
    validate_user_assigned_to_item_group(user, item_group)

    source_name = get_source_name(mr_name, item_group, user)
    if not source_name:
        out['success'] = False
        out['message'] = f'Source based on material request {mr_name} for user {user} and item_group {item_group} does not exist.'
        return out

    relevant_item = get_relevant_source_item(source_name) 
    if relevant_item.item_code != item_code:
        out['success'] = False
        out['message'] = f'Scanned item {item_code} does not match relevant item {relevant_item.item_code}.'
        return out

    doc = frappe.get_doc('Source', source_name)
    found = False

    for item in doc.items:
        if item.item_code == item_code:
            item.scanned = 1
            item.crate_code = crate_code
            item.scanned_qty = scanned_qty
            out['message'] = f'Scanned {scanned_qty} {item.uom} for item {item_code}'

            if skipped:
                item.skipped = 1
                out['message'] = f'Skipped item {item_code}'
            
            found = True
            break

    if not found:
        e = frappe.exceptions.DoesNotExistError(f"Item {item_code} not found in Source {source_name}.")
        frappe.response = exception_handler(e)   
        raise e
    
    frappe.db.savepoint('sp')

    try:
        doc.save()
        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.response = exception_handler(e)   
        raise e
        
    return out

def create_crate_log(crate_code: str, stream: str, to_warehouse: str, from_warehouse: str, picked_by: str, items: list) -> dict:
    try:
        crate_log = frappe.get_doc({
            'doctype': 'Crate Log',
            'crate_code': crate_code,
            'stream': stream,
            'to_warehouse': to_warehouse,
            'from_warehouse': from_warehouse,
            'picked_by': picked_by,
            'items': items,
        })
        crate_log.insert()
        return {'status': 'success', 'crate_log': crate_log}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    
@frappe.whitelist()
def create_stream(crate_code:str='BE-0001', item_group:str='FOOD/SNACK', material_request:str='MAT-MR-2025-00065', from_warehouse:str='KG Warehouse - JP', to_warehouse:str='GG Stock - JP', items:list=[]) -> dict:
    try:
        crate_validated = validate_crate(crate_code) 

        if crate_validated.get('status') != 'success':
            return crate_validated

        stream = frappe.get_doc({
            'doctype': 'Stream',
            'crate_code': crate_code,
            'item_group': item_group,
            'material_request': material_request,
            'from_warehouse': from_warehouse,
            'to_warehouse': to_warehouse,
            'items': items
        })
        stream.insert()
        return {'status': 'success', 'stream': stream}
        
    except Exception as e:
        frappe.log_error(message=str(e), title="Error in create_stream", reference_doctype='Stream')
        return {'status': 'error', 'message': str(e)}

def update_crate(
        stream: str = 'PICK-STR-2025-012663',
        is_insert: bool = False,
        is_update: bool = False,
        is_waiting: bool = False,
        is_transit: bool = False,
        is_verifying: bool = False,
        is_clear: bool = False
    ) -> dict:
    try:
        stream_doc = frappe.get_doc('Stream', stream)
        crate_doc = frappe.get_doc('Crate', stream_doc.crate_code)
        previous_status = crate_doc.status
        out = []

        if is_insert:
            crate_validated = validate_crate(stream_doc.crate_code)

            if crate_validated.get('status') != 'success':
                return crate_validated
                
            crate_doc.update({
                'status': 'Picking',
                'stream': stream_doc.name,
                'item_group': stream_doc.item_group,
                'from_warehouse': stream_doc.from_warehouse,
                'to_warehouse': stream_doc.to_warehouse
            })
            out.append(
                f"Updated: Status 'Available' -> 'Picking', Stream -> {stream_doc.name}, "
                f"Item Group -> {stream_doc.item_group}, From Warehouse -> {stream_doc.from_warehouse}, "
                f"To Warehouse -> {stream_doc.to_warehouse}"
            )

        elif is_update:
            crate_doc.items.clear()
            
            for item in stream_doc.items:
                crate_doc.append('items', {
                    'item_code': item.item_code,
                    'item_name': item.item_name,
                    'item_group': item.item_group,
                    'uom': item.uom,
                    'qty': item.qty,
                    'from_warehouse': item.from_warehouse,
                    'to_warehouse': item.to_warehouse,
                    'material_request': item.material_request,
                    'material_request_item': item.material_request_item
                })
                
            out.append("Synchronized crate items with stream.")

        elif is_waiting:
            crate_doc.update({'status': 'Waiting'})
            out.append(f"Updated: Status '{previous_status}' -> 'Waiting'.")

        elif is_transit:
            crate_doc.update({'status': 'In Transit'})
            out.append(f"Updated: Status '{previous_status}' -> 'In Transit'.")

        elif is_verifying:
            crate_doc.update({'status': 'Verifying'})
            out.append(f"Updated: Status '{previous_status}' -> 'Verifying'.")

        elif is_clear:
            crate_doc.update({
                'status': 'Available',
                'stream': None,
                'item_group': None,
                'from_warehouse': None,
                'to_warehouse': None
            })
            crate_doc.items.clear()
            out.append(f"Updated: Status '{previous_status}' -> 'Available'. Cleared Items Table.")

        crate_doc.save()
        return {
            'status': 'success',
            'message': "Crate updated successfully.",
            'details': ' '.join(out)
        }

    except Exception as e:
        frappe.log_error(message=str(e), title="Error in update_crate", reference_doctype='Crate')
        return {'status': 'error', 'message': str(e)}

def update_stream(stream:str, data:dict):
    try:
        stream_doc = frappe.get_doc('Stream', stream)

        for key in data:
            if not stream_doc.key:
                return
                
            elif stream_doc.key != key:
                stream_doc.key = key
                
    except Exception as e:
        frappe.log_error(message=str(e), title='Error in update_stream', reference_doctype='Stream')
        return {'status': 'error', 'message': str(e)}

def update_stream_items(stream:str, items:list) -> dict:
    try:
        stream_doc = frappe.get_doc('Stream', stream)
        out = ''
        existing_items = {item.item_code: item for item in stream_doc.items} if stream_doc.items else {}
        
        for item in items:
            item_code = item.get('item_code')
            
            if not item_code:
                frappe.log_error(
                    message=f"Each item must have an item_code: {item}",
                    title="Error in update_stream_items",
                    reference_doctype='Stream',
                    reference_name=stream_doc.name
                )
                return {'status': 'error', 'message': 'Each item must have an item_code.'}
                
            if item_code in existing_items:
                matched_item = existing_items[item_code]
                
                for key, value in item.items():
                    if hasattr(matched_item, key) and getattr(matched_item, key) != value:
                        previous_value = getattr(matched_item, key)
                        setattr(matched_item, key, value)
                        out += f'Updated {key} of Item {item_code} from {previous_value} to {value}, '

            else:
                stream_doc.append('items', item)
                out += f'Added Item {item}, '
                
        stream_doc.save()
        return {
            'status': 'success',
            'message': out
        }

    except Exception as e:
        frappe.log_error(
            message=str(e),
            title="Error in update_stream_items",
            reference_doctype='Stream',
            reference_name=stream
        )
        return {'status': 'error', 'message': str(e)}

def update_crate_log(stream_name: str) -> dict:
    pass
