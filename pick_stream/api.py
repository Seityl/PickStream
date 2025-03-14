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
@pick_stream_validate(methods=['POST'])
def submit_scan_details(
    user:str,
    mr_name:str,
    item_code:str,
    item_group:str,
    crate_code:str,
    scanned_qty:int,
    skipped:bool = False
    ) -> dict:
    """Endpoint for submission of scans"""
    try:
        process_scan = process_scan_details(
            user,
            mr_name,
            item_code,
            item_group,
            crate_code,
            scanned_qty,
            skipped
        )

        if not process_scan.success:
            return generate_response(417, None, process_scan)

        return generate_response(200, None, process_scan)

    except Exception as e:
        frappe.response = exception_handler(e)   
        raise e