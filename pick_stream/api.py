import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils.nestedset import get_descendants_of
from frappe.utils import add_to_date, strip_html_tags

from datetime import datetime 

from pick_stream.api_utils import generate_response, exception_handler, generate_key, pick_stream_validate

from pick_stream.core import get_material_request_item_groups_view_details
from pick_stream.core import get_material_request_item_group_view_details
from pick_stream.core import get_material_request_picking_view_details
from pick_stream.core import check_item_against_barcode
from pick_stream.core import get_user_material_requests
from pick_stream.core import check_crate_availability
from pick_stream.core import process_scan_details

@frappe.whitelist(allow_guest=True)
def login_user(usr, pwd):
  try:
    login_manager = LoginManager()
    login_manager.authenticate(usr, pwd)
    login_manager.post_login()
    # validate_branch(login_manager.user)
    if frappe.response['message'] == 'Logged In':
        frappe.response['user'] = login_manager.user
        frappe.response['keys'] = generate_keys(login_manager.user)
  except frappe.exceptions.InvalidAuthorizationHeader as e:
      frappe.response["http_status_code"] = 400
      frappe.response["err"] = {'status': 'failure', 'message': f'{e}'}
  except frappe.exceptions.AuthenticationError as e:
      frappe.local.response["http_status_code"] = 401
      frappe.local.response["message"] = 'Invalid Login. Try again.'


def generate_keys(user: str):
  user_details = frappe.get_doc("User", user)

  api_key = api_secret = ''

  if not user_details.api_key and not user_details.api_secret:
    api_key = frappe.generate_hash(length=15)
    api_secret = frappe.generate_hash(length=15)
    user_details.api_key = api_key
    user_details.api_secret = api_secret
    user_details.save(ignore_permissions = True)
  else:
    api_secret = user_details.get_password('api_secret')
    api_key = user_details.get('api_key')

  return {"api_secret": api_secret, "api_key": api_key}

@frappe.whitelist()
def get_user_notifications():
    try:
      today = datetime.now()
      one_week_ago = add_to_date(today, days=-7).date()
      
      notifications = frappe.db.get_list('Notification Log', {'for_user': frappe.session.user, 'type': ['in', ['Mention', 'Assignment', 'Alert']], 'creation': ['>', one_week_ago]}, ['subject'])
      stripped_notifications = [{'subject': strip_html_tags(notification.subject), 'date': one_week_ago} for notification in notifications]
      frappe.local.response["http_status_code"] = 200 
      frappe.local.response["data"] = stripped_notifications
    except Exception as e:
      print(e)

@frappe.whitelist()
def get_user_info():
    employee_id = ""
    employee_branch = ""
    try:
      current_user = frappe.get_doc('User', frappe.session.user)
      
      employee_doc_exists = frappe.db.exists('Employee', {"user_id": frappe.session.user})

      if employee_doc_exists:
          employee_data = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "branch"])

          employee_id = employee_data[0]
          employee_branch = employee_data[1]

      user_data = {
          "full_name": current_user.full_name,
          "user_id": current_user.name,
          "image_url": current_user.user_image or "",
          "employee_id": employee_id,
          "employee_branch": employee_branch
      }      

      frappe.local.response["http_status_code"] = 200
      frappe.local.response["data"] = user_data
    except Exception as e:
        frappe.local.response["http_status_code"] = 500 
        frappe.local.response["message"] = f'Something went wrong: {e}'

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def validate_crate(crate_code:str) -> dict:
    """Returns data:true if crate is available and data:false if crate is not."""
    try:
        if check_crate_availability(crate_code):
            return generate_response(200, None, True)
        return generate_response(200, None, False)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def validate_item_against_barcode(item_code:str, barcode:str) -> dict:
    """Returns data:true if barcode matches item and data:false if it does not."""
    try:
        if check_item_against_barcode(item_code, barcode):
            return generate_response(200, None, True)
        return generate_response(200, None, False)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_list_view(user:str) -> dict:
    """Retrieve material request list view details for the specified user"""
    try:
        view_details = get_user_material_requests(user)
        return generate_response(200, None, view_details)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_available_item_groups_view(user:str, mr_name:str) -> dict:
    """Retrieve available item groups view for Material Request assigned to the specified user"""
    try:
        view_details = get_material_request_item_groups_view_details(mr_name, user)
        return generate_response(200, None, view_details)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_item_group_view(user:str, mr_name:str, item_group:str) -> dict:
    """Retrieve item group view for Material Request based on the specified user and item group"""
    try:
        view_details = get_material_request_item_group_view_details(mr_name, user, item_group)
        return generate_response(200, None, view_details)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_picking_view(user:str, mr_name:str, item_group:str) -> dict:
    """Retrieve picking view for Material Request based on the specified user and item group"""
    try:
        view_details = get_material_request_picking_view_details(mr_name, user, item_group)
        return generate_response(200, None, view_details)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def submit_scan_details(user:str, mr_name:str, item_code:str, qty:int) -> dict:
    """Endpoint for submission of scans"""
    try:
        scan_details = process_scan_details(user, mr_name, item_code, qty)
        return generate_response(200, None, scan_details)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e

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
