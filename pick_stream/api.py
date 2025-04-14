import frappe

from pick_stream.api_utils import generate_response, pick_stream_validate

from pick_stream.core import get_material_request_item_groups_view_details, get_material_request_item_group_view_details, get_material_request_picking_view_details, get_user_material_requests, get_printers
from pick_stream.core import check_item_against_barcode, check_crate_availability
from pick_stream.core import process_scan_details, process_print_request

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def validate_crate(crate_code:str) -> dict:
    """Returns {data:true} if crate is available and {data:false} if crate is not."""
    if check_crate_availability(crate_code):
        return generate_response(200, None, True)
    return generate_response(200, None, False)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def validate_item_against_barcode(item_code:str, barcode:str) -> dict:
    """Returns {data:true} if barcode matches item and {data:false} if it does not."""
    if check_item_against_barcode(item_code, barcode):
        return generate_response(200, None, True)
    return generate_response(200, None, False)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_list_view(user:str) -> dict:
    """Retrieve material request list view details for the specified user"""
    view_details = get_user_material_requests(user)
    return generate_response(200, None, view_details)
  
@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_available_item_groups_view(user:str, mr_name:str) -> dict:
    """Retrieve available item groups view for Material Request assigned to the specified user"""
    view_details = get_material_request_item_groups_view_details(mr_name, user)
    return generate_response(200, None, view_details)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_item_group_view(user:str, mr_name:str, item_group:str) -> dict:
    """Retrieve item group view for Material Request based on the specified user and item group"""
    view_details = get_material_request_item_group_view_details(mr_name, user, item_group)
    return generate_response(200, None, view_details)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_material_request_picking_view(user:str, mr_name:str, item_group:str, crate_code:str) -> dict:
    """Retrieve picking view for Material Request based on the specified user and item group"""
    view_details = get_material_request_picking_view_details(mr_name, user, item_group, crate_code)
    return generate_response(200, None, view_details)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def get_printer_list_view() -> dict:
    """Retrieve available label printers view"""
    printers = get_printers()
    if printers.exc:
        return generate_response(417, None, printers.exc)
    return generate_response(200, None, printers.printers)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def submit_print_request(item_code:str, item_type:str, user:str, mr_name:str, printer:str) -> dict:
    """Prints label based on params"""
    print_request = process_print_request(item_code, item_type, user, mr_name, printer)
    if print_request.exc:
        return generate_response(417, None, print_request.exc)
    return generate_response(200, None, print_request.message)

@frappe.whitelist()
@pick_stream_validate(methods=['GET'])
def submit_scan_details(
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
    """Endpoint for submission of scans"""
    process_scan = process_scan_details(
        user,
        mr_name,
        item_code,
        item_group,
        scanned_qty,
        crate_code,
        as_box,
        as_other,
        skipped,
        close_crate
    )
    if not process_scan.success:
        return generate_response(417, None, process_scan)
    return generate_response(200, None, process_scan)