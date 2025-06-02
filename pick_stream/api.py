import frappe
import pick_stream
from pick_stream.api_utils import generate_response
from pick_stream.core import (
    check_crate_availability,
    check_item_against_barcode,
    close_crate,
    get_identifier_details,
    get_identifier_list,
    get_material_request_item_group_view_details,
    get_verification_list,
    get_crate_details_,
    get_material_request_item_groups_view_details,
    get_material_request_picking_view_details,
    get_printers,
    get_user_crate,
    get_user_crate_details,
    get_user_material_requests,
    get_transit_list,
    get_receiving_list,
    process_print_request,
    process_verification_request,
    process_transit_request,
    process_receiving_request,
    process_scan_details,
)

# API Docs: \\storage\it\IT_Vault\IT_Team_Vault\06_Projects\Current Projects\Pick Stream\Documentation\API 

#=====# UTILS #=================================================================#

@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def validate_crate(crate_code:str, user:str) -> dict:
    if check_crate_availability(crate_code, user):
        return generate_response(200, None, True)
    return generate_response(200, None, False)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def validate_item_against_barcode(item_code:str, barcode:str) -> dict:
    if check_item_against_barcode(item_code, barcode):
        return generate_response(200, None, True)
    return generate_response(200, None, False)


# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_crate_details(
    user:str,
    crate_code:str,
    to_verify:bool=False,
    to_transit:bool=False,
    to_receive:bool=False,
) -> dict:
    crate_details = get_crate_details_(
        user,
        crate_code,
        to_verify,
        to_transit,
        to_receive
    )
    return generate_response(200, None, crate_details)

#=====# ----- #=================================================================#


#=====# PRINTING #=================================================================#

@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET', 'POST'])
def get_printer_list_view() -> dict:
    printers = get_printers()
    return generate_response(200, None, printers)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET', 'POST'])
def submit_print_request(
    printer:str,
    mr_name:str=None,
    item_code:str=None,
    item_type:str=None,
    user:str=None,
    qty:int=0, 
    item_identifier:str=None,
    crate_code:str=None
) -> dict:
    message = process_print_request(printer, mr_name, item_code, item_type, user, qty, item_identifier, crate_code)
    return generate_response(200, None, message)

#=====# -------- #=================================================================#


#=====# PICKING #=================================================================#

@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_material_request_available_item_groups_view(user:str, mr_name:str) -> dict:
    view_details = get_material_request_item_groups_view_details(mr_name, user)
    return generate_response(200, None, view_details)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_material_request_list_view(user:str) -> dict:
    view_details = get_user_material_requests(user)
    return generate_response(200, None, view_details)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_material_request_picking_view(user:str, mr_name:str, item_group:str) -> dict:
    view_details = get_material_request_picking_view_details(mr_name, user, item_group)
    return generate_response(200, None, view_details)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_user_active_crate(user:str) -> dict:
    active_crate = get_user_crate(user)
    return generate_response(200, None, active_crate)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_user_active_crate_details(user:str) -> dict:
    crate_details = get_user_crate_details(user)
    return generate_response(200, None, crate_details)


# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def submit_close_crate_request(crate_code:str) -> dict:
    crate_details = close_crate(crate_code)
    return generate_response(200, None, crate_details)


@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def submit_scan_details(
    user:str,
    mr_name:str,
    item_code:str,
    item_group:str,
    crates:any = [],
    as_box:bool = False,
    scanned_qty:int = 0,
    skipped:bool = False,
    as_other:bool = False,
    crate_code:str = None
) -> dict:
    result = process_scan_details(
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


# Made obsolete by get_material_request_available_item_groups_view() 14/05/2025
# @frappe.whitelist()
# @pick_stream.api_utils.handler(methods=['GET'])
# def get_material_request_item_group_view(user:str, mr_name:str, item_group:str) -> dict:
#     """Retrieve item group view for Material Request based on the specified user and item group"""
#     view_details = get_material_request_item_group_view_details(mr_name, user, item_group)
#     return generate_response(200, None, view_details)

#=====# ------- #=================================================================#


#=====# TOOLS #=================================================================#

@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_item_identifier_list(user, limit:int=20) -> dict:
    """Returns list of associated details"""
    identifier_list = get_identifier_list(user, limit)
    return generate_response(200, None, identifier_list)

@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_item_identifier_details(item_identifier:str) -> dict:
    """Returns associated details of item identifier"""
    identifier_details = get_identifier_details(item_identifier)
    return generate_response(200, None, identifier_details)

#=====# ----- #=================================================================#


#=====# VERIFICATION #=================================================================#

# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_verification_list_view(user:str) -> dict:
    verification_list = get_verification_list(user)
    return generate_response(200, None, verification_list)


# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def submit_verification_request(
    user:str,
    source:str,
    crate_code:str,
    items:any=[]
) -> dict:
    verification_request = process_verification_request(
        user,
        items,
        source,
        crate_code
    )
    return generate_response(200, None, verification_request)

#=====# ------------ #=================================================================#


#=====# TRANSIT #=================================================================#

# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_transit_list_view(user:str) -> dict:
    transit_list = get_transit_list(user)
    return generate_response(200, None, transit_list)


# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def submit_transit_request(
    user:str,
    crate_codes:any,
    to_warehouse:str,
    from_warehouse:str
) -> dict:
    transit_request = process_transit_request(
        user,
        crate_codes,
        to_warehouse,
        from_warehouse
    )
    return generate_response(200, None, transit_request)

#=====# ------- #=================================================================#


#=====# RECEIVING #=================================================================#

# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def get_receiving_list_view(user:str) -> dict:
    receiving_list = get_receiving_list(user)
    return generate_response(200, None, receiving_list)


# TODO: Add docs
@frappe.whitelist()
@pick_stream.api_utils.handler(methods=['GET'])
def submit_receiving_request(
    user:str,
    crate_codes:any,
    to_warehouse:str,
    from_warehouse:str
) -> dict:
    receiving_request = process_receiving_request(
        user,
        crate_codes,
        to_warehouse,
        from_warehouse
    )
    return generate_response(200, None, receiving_request)

#=====# --------- #=================================================================#


# @frappe.whitelist()
# @pick_stream.api_utils.handler(methods=['GET'])
# def get_user_crate_list(user:str) -> dict:
#     """Returns currently picking crates for associated user"""
#     user_crate_details = get_user_crate_details(user)
#     return generate_response(200, None, user_crate_details)

# @frappe.whitelist()
# @pick_stream.api_utils.handler(methods=['GET'])
# def get_user_crate_items(user:str, crate_code:str) -> dict:
#     """Returns items currently in crate"""
#     user_crate_details = get_user_crate_items_details(user, crate_code)
#     return generate_response(200, None, user_crate_details)