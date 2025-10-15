"""
REST API endpoints for Pick Stream system.

Provides HTTP endpoints for all warehouse operations including:
- Picking: Material request management and item scanning
- Verification: Crate and item verification workflows
- Transit: Inter-warehouse transfer operations
- Receiving: Inbound shipment processing
- Printing: Label and barcode generation
- Tools: Crate checking, item identifier lookups, etc.
- Utilities: User management, notifications, and validation helpers

All endpoints use consistent response formatting and automatic exception handling
via the @handler decorator.

Author: Jeriel Francis

Copyright (c) 2025, Jollys Pharmacy Limited and contributors
For license information, please see license.txt
"""


import frappe
from typing import Any, Dict

from pick_stream import core, utils 
from pick_stream.api_utils import handler, generate_response 


#------------------- 
# Picking Endpoints

@frappe.whitelist()
@handler(methods=['GET'])
def get_material_request_list_view(user:str) -> Dict:
    """
    Returns list of material requests for a specific user.
    """
    view_details = core.get_user_material_requests(user)
    return generate_response(200, None, view_details)


@frappe.whitelist()
@handler(methods=['GET'])
def get_material_request_available_item_groups_view(
    user:str,
    mr_name:str
) -> Dict:
    """
    Returns available item groups for a material request for a specific user.
    """
    view_details = core.get_material_request_item_groups_view_details(
        mr_name,
        user
    )
    return generate_response(200, None, view_details)


@frappe.whitelist()
@handler(methods=['GET'])
def get_material_request_picking_view(
    user:str, 
    mr_name:str,
    item_group:str
) -> Dict:
    """
    Returns picking view details for a material request and item group for a specific user.
    """
    view_details = core.get_material_request_picking_view_details(
        mr_name,
        user,
        item_group
    )
    return generate_response(200, None, view_details)


@frappe.whitelist()
@handler(methods=['GET'])
def submit_scan_details(
    user:str,
    mr_name:str,
    item_code:str,
    item_group:str,
    crates:Any = [],
    as_box:bool = False,
    scanned_qty:int = 0,
    skipped:bool = False,
    as_other:bool = False,
    crate_code:str = None
) -> Dict:
    """
    Process and submit scanned item details for a material request.
    """
    result = core.process_scan_details(
        user,
        mr_name,
        item_code,
        item_group,
        crates,
        as_box,
        scanned_qty,
        skipped,
        as_other,
        crate_code
    )
    return generate_response(200, None, result)


#------------------------
# Verification Endpoints

@frappe.whitelist()
@handler(methods=['GET'])
def get_verification_list_view(user:str) -> Dict:
    """
    Returns list of items available for verification for a specific user.
    """
    verification_list = core.get_verification_list(user)
    return generate_response(200, None, verification_list)


@frappe.whitelist()
@handler(methods=['POST'])
def submit_verification_request(
    user:str,
    items:Any,
    crate_code:str=None,
    identifier_code:str=None
) -> Dict:
    """
    Submit a verification request for items assigned to crates or identifier codes.
    """
    verification_request = core.process_verification_request(
        user,
        items,
        crate_code,
        identifier_code
    )
    return generate_response(200, None, verification_request)


#-------------------
# Transit Endpoints

@frappe.whitelist()
@handler(methods=['GET'])
def get_transit_list_view(user:str) -> Dict:
    """
    Returns list of items available for verification for a specific user.
    """
    transit_list = core.get_transit_list(user)
    return generate_response(200, None, transit_list)


@frappe.whitelist()
@handler(methods=['POST'])
def submit_transit_request(
    user:str,
    to_warehouse:str,
    from_warehouse:str,
    crate_codes:Any=[],
    identifier_codes:Any=[]
) -> Dict:
    """
    Submit a transit request for items assigned to crates or identifier codes.
    """
    transit_request = core.process_transit_request(
        user,
        to_warehouse,
        from_warehouse,
        crate_codes,
        identifier_codes
    )
    return generate_response(200, None, transit_request)


# 
# Receiving Endpoints
# 

# TODO: Add docs
@frappe.whitelist()
@handler(methods=['GET'])
def get_receiving_list_view(user:str) -> Dict:
    receiving_list = core.get_receiving_list(user)
    return generate_response(200, None, receiving_list)


# TODO: Add docs
@frappe.whitelist()
@handler(methods=['GET'])
def submit_receiving_request(
    user:str,
    code:str,
    to_warehouse:str,
    from_warehouse:str
) -> Dict:
    receiving_request = core.process_receiving_request(
        user,
        code,
        to_warehouse,
        from_warehouse
    )
    return generate_response(200, None, receiving_request)


#--------------------
# Printing Endpoints

@frappe.whitelist()
@handler(methods=['GET', 'POST'])
def get_printer_list_view() -> Dict:
    printers = utils.get_printers()
    return generate_response(200, None, printers)


@frappe.whitelist()
@handler(methods=['GET', 'POST'])
def submit_print_request(
    printer:str,
    mr_name:str=None,
    item_code:str=None,
    item_type:str=None,
    user:str=None,
    qty:int=0, 
    item_identifier:str=None,
    crate_code:str=None
) -> Dict:
    message = utils.process_print_request(
        printer,
        mr_name,
        item_code,
        item_type,
        user,
        qty,
        item_identifier,
        crate_code
    )
    return generate_response(200, None, message)


#-----------------
# Tools Endpoints

@frappe.whitelist()
@handler(methods=['GET'])
def get_crate_check(crate_code:str) -> Dict:
    """Returns details of specified crate"""
    crate_details = utils.get_crate_check_details(crate_code)
    return generate_response(200, None, crate_details)


@frappe.whitelist()
@handler(methods=['GET'])
def get_item_identifier_list(user, limit:int=20) -> Dict:
    """Returns list of associated details"""
    identifier_list = utils.get_identifier_list(user, limit)
    return generate_response(200, None, identifier_list)


@frappe.whitelist()
@handler(methods=['GET'])
def get_item_identifier_details(item_identifier:str) -> Dict:
    """Returns associated details of item identifier"""
    identifier_details = utils.get_identifier_details(item_identifier)
    return generate_response(200, None, identifier_details)


@frappe.whitelist()
@handler(methods=['GET'])
def get_user_active_crate_details(user:str) -> Dict:
    crate_details = utils.get_user_crate_details(user)
    return generate_response(200, None, crate_details)


#------------------- 
# Utility Endpoints

@frappe.whitelist()
@handler(methods=['GET'])
def get_crate_details(
    user:str,
    crate_code:str,
    to_verify:bool=False,
    to_transit:bool=False,
    to_receive:bool=False,
) -> Dict:
    crate_details = utils.get_crate_details_(
        user,
        crate_code,
        to_verify,
        to_transit,
        to_receive
    )
    return generate_response(200, None, crate_details)


@frappe.whitelist()
@handler(methods=['GET'])
def get_user_active_crate(user:str) -> Dict:
    active_crate = utils.get_user_crate(user)
    return generate_response(200, None, active_crate)


@frappe.whitelist()
@handler(methods=['GET'])
def get_user_workflow_access(user:str) -> Dict:
    workflow_access = utils.get_user_workflow_access(user)
    return generate_response(200, None, workflow_access)


@frappe.whitelist()
@handler(methods=['GET'])
def get_user_profile(user:str) -> Dict:
    user_profile = utils.get_user_profile(user)
    return generate_response(200, None, user_profile)


@frappe.whitelist()
@handler(methods=['GET'])
def get_user_notifications(user:str) -> Dict:
    user_notifications = utils.get_user_notifications(user)
    return generate_response(200, None, user_notifications)


@frappe.whitelist()
@handler(methods=['GET'])
def validate_item_against_barcode(item_code:str, barcode:str) -> Dict:
    if utils.check_item_against_barcode(item_code, barcode):
        return generate_response(200, None, True)
    return generate_response(200, None, False)


@frappe.whitelist()
@handler(methods=['GET'])
def validate_crate(crate_code:str, user:str) -> Dict:
    if utils.check_crate_availability(crate_code, user):
        return generate_response(200, None, True)
    return generate_response(200, None, False)


@frappe.whitelist()
@handler(methods=['POST'])
def submit_close_crate_request(crate_code:str, items:Any=[]) -> Dict:
    close_crate = utils.close_crate(crate_code, items=items, commit=True)
    return generate_response(200, None, close_crate)


@frappe.whitelist()
@handler(methods=['POST'])
def verify_first_crate_quantities(crate_code:str, items:Any=[]) -> Dict:
    """Verify and update quantities for the first crate in multi-crate picking"""
    verified_crate = utils.verify_first_crate(crate_code, items=items, commit=True)
    return generate_response(200, None, verified_crate)



    
#=====# UTILS #=================================================================#




#=====# ----- #=================================================================#


#=====# PRINTING #=================================================================#

#=====# -------- #=================================================================#

#=====# TOOLS #=================================================================#

#=====# ----- #=================================================================#




#=====# TRANSIT #=================================================================#
#=====# ------- #=================================================================#


#=====# RECEIVING #=================================================================#



#=====# --------- #=================================================================#


# @frappe.whitelist()
# @handler(methods=['GET'])
# def get_user_crate_list(user:str) -> Dict:
#     """Returns currently picking crates for associated user"""
#     user_crate_details = get_user_crate_details(user)
#     return generate_response(200, None, user_crate_details)

# @frappe.whitelist()
# @handler(methods=['GET'])
# def get_user_crate_items(user:str, crate_code:str) -> Dict:
#     """Returns items currently in crate"""
#     user_crate_details = get_user_crate_items_details(user, crate_code)


# Made obsolete by get_material_request_available_item_groups_view() 14/05/2025
# @frappe.whitelist()
# @handler(methods=['GET'])
# def get_material_request_item_group_view(user:str, mr_name:str, item_group:str) -> Dict:
#     """Retrieve item group view for Material Request based on the specified user and item group"""
#     view_details = get_material_request_item_group_view_details(mr_name, user, item_group)
#     return generate_response(200, None, view_details)
#     return generate_response(200, None, user_crate_details)