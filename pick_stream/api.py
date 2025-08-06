import frappe
from typing import Any, Dict
from pick_stream import api_utils, core 

# API Docs: \\storage\it\IT_Vault\IT_Team_Vault\06_Projects\Current Projects\Pick Stream\Documentation\API 

# 
# Picking Endpoints
# 

@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_material_request_list_view(user:str) -> Dict:
    view_details = core.get_user_material_requests(user)
    return api_utils.generate_response(200, None, view_details)


@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_material_request_available_item_groups_view(user:str, mr_name:str) -> Dict:
    view_details = core.get_material_request_item_groups_view_details(mr_name, user)
    return api_utils.generate_response(200, None, view_details)


@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_material_request_picking_view(user:str, mr_name:str, item_group:str) -> Dict:
    view_details = core.get_material_request_picking_view_details(mr_name, user, item_group)
    return api_utils.generate_response(200, None, view_details)


@frappe.whitelist()
@api_utils.handler(methods=['GET'])
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
    return api_utils.generate_response(200, None, result)

# 
# Verification Endpoints
# 

# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_verification_list_view(user:str) -> Dict:
    verification_list = core.get_verification_list(user)
    return api_utils.generate_response(200, None, verification_list)


# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['POST'])
def submit_verification_request(
    user:str,
    items:Any,
    crate_code:str=None,
    identifier_code:str=None
) -> Dict:
    verification_request = core.process_verification_request(
        user,
        items,
        crate_code,
        identifier_code
    )
    return api_utils.generate_response(200, None, verification_request)

# 
# Transit Endpoints
# 

# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_transit_list_view(user:str) -> Dict:
    transit_list = core.get_transit_list(user)
    return api_utils.generate_response(200, None, transit_list)


# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['POST'])
def submit_transit_request(
    user:str,
    to_warehouse:str,
    from_warehouse:str,
    crate_codes:Any=[],
    identifier_codes:Any=[]
) -> Dict:
    transit_request = core.process_transit_request(
        user,
        to_warehouse,
        from_warehouse,
        crate_codes,
        identifier_codes
    )
    return api_utils.generate_response(200, None, transit_request)

# 
# Receiving Endpoints
# 

# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_receiving_list_view(user:str) -> Dict:
    receiving_list = core.get_receiving_list(user)
    return api_utils.generate_response(200, None, receiving_list)


# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['GET'])
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
    return api_utils.generate_response(200, None, receiving_request)

# 
# Utility Endpoints
# 

@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_user_active_crate(user:str) -> Dict:
    active_crate = core.get_user_crate(user)
    return api_utils.generate_response(200, None, active_crate)


@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_user_active_crate_details(user:str) -> Dict:
    crate_details = core.get_user_crate_details(user)
    return api_utils.generate_response(200, None, crate_details)



@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def validate_item_against_barcode(item_code:str, barcode:str) -> Dict:
    if core.check_item_against_barcode(item_code, barcode):
        return api_utils.generate_response(200, None, True)
    return api_utils.generate_response(200, None, False)


@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def validate_crate(crate_code:str, user:str) -> Dict:
    if core.check_crate_availability(crate_code, user):
        return api_utils.generate_response(200, None, True)
    return api_utils.generate_response(200, None, False)


# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['POST'])
def submit_close_crate_request(crate_code:str) -> Dict:
    close_crate = core.close_crate(crate_code, commit=True)
    return api_utils.generate_response(200, None, close_crate)


# 
# Printing Endpoints
# 

@frappe.whitelist()
@api_utils.handler(methods=['GET', 'POST'])
def get_printer_list_view() -> Dict:
    printers = core.get_printers()
    return api_utils.generate_response(200, None, printers)


@frappe.whitelist()
@api_utils.handler(methods=['GET', 'POST'])
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
    message = core.process_print_request(printer, mr_name, item_code, item_type, user, qty, item_identifier, crate_code)
    return api_utils.generate_response(200, None, message)
    
#=====# UTILS #=================================================================#


# TODO: Add docs
@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_crate_details(
    user:str,
    crate_code:str,
    to_verify:bool=False,
    to_transit:bool=False,
    to_receive:bool=False,
) -> Dict:
    crate_details = core.get_crate_details_(
        user,
        crate_code,
        to_verify,
        to_transit,
        to_receive
    )
    return api_utils.generate_response(200, None, crate_details)

#=====# ----- #=================================================================#


#=====# PRINTING #=================================================================#

#=====# -------- #=================================================================#

#=====# TOOLS #=================================================================#

@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_item_identifier_list(user, limit:int=20) -> Dict:
    """Returns list of associated details"""
    identifier_list = core.get_identifier_list(user, limit)
    return api_utils.generate_response(200, None, identifier_list)


@frappe.whitelist()
@api_utils.handler(methods=['GET'])
def get_item_identifier_details(item_identifier:str) -> Dict:
    """Returns associated details of item identifier"""
    identifier_details = core.get_identifier_details(item_identifier)
    return api_utils.generate_response(200, None, identifier_details)








#=====# ----- #=================================================================#




#=====# TRANSIT #=================================================================#
#=====# ------- #=================================================================#


#=====# RECEIVING #=================================================================#



#=====# --------- #=================================================================#


# @frappe.whitelist()
# @api_utils.handler(methods=['GET'])
# def get_user_crate_list(user:str) -> Dict:
#     """Returns currently picking crates for associated user"""
#     user_crate_details = get_user_crate_details(user)
#     return api_utils.generate_response(200, None, user_crate_details)

# @frappe.whitelist()
# @api_utils.handler(methods=['GET'])
# def get_user_crate_items(user:str, crate_code:str) -> Dict:
#     """Returns items currently in crate"""
#     user_crate_details = get_user_crate_items_details(user, crate_code)


# Made obsolete by get_material_request_available_item_groups_view() 14/05/2025
# @frappe.whitelist()
# @api_utils.handler(methods=['GET'])
# def get_material_request_item_group_view(user:str, mr_name:str, item_group:str) -> Dict:
#     """Retrieve item group view for Material Request based on the specified user and item group"""
#     view_details = get_material_request_item_group_view_details(mr_name, user, item_group)
#     return api_utils.generate_response(200, None, view_details)
#     return api_utils.generate_response(200, None, user_crate_details)