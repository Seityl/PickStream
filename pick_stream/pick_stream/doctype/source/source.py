# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt


import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.nestedset import get_descendants_of
from frappe.utils import cint, flt, floor, get_link_to_form

import pick_stream


class Source(Document):
    def before_save(self):
        self.set_item_locations()

    def validate(self):
        self.validate_scanned_qty()
        self.validate_stock_qty()
        self.update_streams()

    def on_update(self):
        if self.is_completed() and self.status != 'Completed':
            self.db_set('status', 'Completed')
            
    def is_completed(self):
        return all(item.scanned or item.skipped for item in self.items)

    def update_streams(self):
        crates_status = self.get_crates_status()

        if not crates_status:
            return

        for crate_code, status in crates_status.items():
            stream_name = frappe.db.get_value(
                'Stream', 
                {
                    'crate_code': crate_code,
                    'source': self.name
                }, 
                'name'
            )
            
            if not stream_name:
                stream_name = pick_stream.core.create_stream(self, crate_code)

            else:
                pick_stream.core.update_stream(self, stream_name, status)

    def get_crates_status(self):
        crates_status = frappe._dict()
        crate_items = frappe._dict()

        for row in self.item_crates:
            if row.crate_code == None:
                continue
            
            if row.crate_code not in crate_items:
                crate_items[row.crate_code] = []

            crate_items[row.crate_code].append(row)
        frappe.log_error('item crates', frappe.as_json(crate_items, indent=2))
        partially_fulfilled_crates = []
        workflow = pick_stream.utils.get_workflow_details(self.to_warehouse)

        for crate_code, items in crate_items.items():
            total_items = len(items)
            
            closed_items = sum(1 for item in items if item.crate_closed)
            verified_items = sum(1 for item in items if item.verified)
            transited_items = sum(1 for item in items if item.transited)
            received_items = sum(1 for item in items if item.received)

            if (received_items == total_items and 
                (not workflow.verification_after_receiving or verified_items == total_items)):
                current_status = 'Completed'  # Workflow complete - all items verified AND received

            elif (received_items == total_items and 
                workflow.verification_after_receiving):
                current_status = 'Received'  # Received, awaiting verification

            elif transited_items == total_items:
                current_status = 'In Transit' # In Transit

            elif (verified_items == total_items and 
                workflow.receiving_after_verification):
                current_status = 'Verified'  # Verified, awaiting receiving

            elif (verified_items == total_items and 
                workflow.transit_after_verification):
                current_status = 'Verified'  # Verified, awaiting transit

            elif closed_items == total_items:
                current_status = 'Waiting'  # Picked, waiting for verification or transit

            else:
                current_status = 'Picking' # Still picking

            is_partially_fulfilled = (
                (0 < closed_items < total_items) or
                (0 < verified_items < total_items) or
                (0 < transited_items < total_items) or
                (0 < received_items < total_items)
            )

            if not is_partially_fulfilled:
                crates_status[crate_code] = current_status

            else:
                # This indicates system a system failure of some sort.
                # Reset items to previous stage to ensure forward correctness.
                partially_fulfilled_crates.append(crate_code)
                try:
                    stream_doc = frappe.get_doc('Stream', {
                        'crate_code': crate_code,
                        'source': self.name
                    })
                    previous_status = stream_doc.previous_status if stream_doc.previous_status else 'Picking'
                    
                except frappe.DoesNotExistError:
                    # If no stream doc exists, default to 'Picking' as the previous status
                    previous_status = 'Picking'

                frappe.log_error('previous_status', previous_status)

                reset_values = {
                    'crate_closed': 0,
                    'verified': 0,
                    'transited': 0,
                    'received': 0
                }
                
                if previous_status == 'Waiting':
                    reset_values['crate_closed'] = 1

                elif previous_status == 'Verified':
                    reset_values['crate_closed'] = 1
                    reset_values['verified'] = 1
                    
                elif previous_status == 'In Transit':
                    reset_values['crate_closed'] = 1
                    reset_values['transited'] = 1

                    if workflow.transit_after_verification:
                        reset_values['verified'] = 1
                        
                elif previous_status == 'Received':
                    reset_values['crate_closed'] = 1
                    reset_values['received'] = 1

                    if workflow.receiving_after_verification:
                        reset_values['verified'] = 1
                        
                    if workflow.transit_required:
                        reset_values['transited'] = 1
                        
                    # For 'Picking' stage, all remain 0

                for item in items:
                    frappe.log_error('item', frappe.as_json(item, indent=2))
                    frappe.log_error('reset_values', frappe.as_json(reset_values, indent=2))

                    # frappe.db.set_value('Item Crates', item.name, reset_values)
                    # frappe.db.commit()

                    for field, value in reset_values.items():
                            setattr(item, field, value)

                    frappe.log_error('item after update', frappe.as_json(item, indent=2))

                crates_status[crate_code] = previous_status

        if partially_fulfilled_crates:
            crate_list = ', '.join(partially_fulfilled_crates)
            raise pick_stream.exceptions.SystemError(
                f'System Error: Crate(s) {crate_list} were partially fulfilled. Item statuses have been reset to previous value ensure data integrity.'
            )

        saved_crate_codes = set(frappe.get_all('Item Crates',
            filters={'parent': self.name, 'crate_code': ('is', 'set')},
            pluck='crate_code'
        ))
        
        # Only process picking crates that are saved in the database to avoid double closing
        picking_crates = [
            (crate_code, status) 
            for crate_code, status in crates_status.items() 
            if status == 'Picking' and crate_code in saved_crate_codes
        ]
        
        if len(picking_crates) > 1:
            def get_min_idx_for_crate(crate_code):
                return min(item.idx for item in self.item_crates if item.crate_code == crate_code)
            
            picking_crates.sort(key=lambda x: get_min_idx_for_crate(x[0]))
            
            crates_to_close = picking_crates[:-1]
            for crate_code, _ in crates_to_close:
                pick_stream.core.close_crate(crate_code, commit=False)
                crates_status[crate_code] = 'Waiting' # Update the status after closing

        return crates_status
    
    def validate_stock_qty(self):
        """
        Validates that scanned quantities don't exceed allocated quantities for each Source Item row.
        
        This method is called AFTER validate_scanned_qty() has recalculated scanned_qty from item_crates,
        so it validates the final calculated quantities against what was allocated during set_item_locations().
        
        Validates against available_qty (allocated at creation), not live bin qty (prevents race conditions).
        """
        for row in self.items:
            # Skip rows with no scanned quantity
            if not row.scanned_qty:
                continue
            # Use allocated quantity (set during set_item_locations) as the validation baseline
            allocated_qty = flt(row.available_qty) if row.available_qty else 0
            scanned_qty = flt(row.scanned_qty)
            # Check if scanned exceeds allocated
            if scanned_qty > allocated_qty:
                # Get detailed breakdown of what's in this Source Item
                crate_details = []
                for crate in self.item_crates:
                    if crate.source_item == row.name:
                        crate_details.append({
                            'crate': crate.crate_code or crate.identifier_code,
                            'qty': crate.qty,
                            'warehouse': crate.from_warehouse
                        })
                # Format detailed message for error log
                crate_list = '\n'.join([
                    f"  - {c['crate']}: {c['qty']} (from {c['warehouse']})"
                    for c in crate_details
                ]) if crate_details else '  No crates found'
                detailed_error_msg = (
                    f'Validation Error: Scanned quantity exceeds allocated quantity\n\n'
                    f'Item: {row.item_code}\n'
                    f'Warehouse: {row.from_warehouse}\n'
                    f'Source Item: {row.name}\n'
                    f'Scanned: {scanned_qty} {row.uom}\n'
                    f'Allocated: {allocated_qty} {row.uom}\n'
                    f'Excess: {scanned_qty - allocated_qty} {row.uom}\n\n'
                    f'Crates/Identifiers assigned to this Source Item:\n{crate_list}\n\n'
                    f'This error indicates that items from multiple warehouses were incorrectly '
                    f'assigned to the same Source Item row. This is a system error.'
                )
                # Log detailed error for investigation
                frappe.log_error(
                    title=f'Stock Validation Failed - {row.item_code} - {row.from_warehouse}',
                    message=detailed_error_msg + '\n\n' + 
                        f'Full Source Item Data:\n{frappe.as_json(row.as_dict(), indent=2)}\n\n'
                        f'Item Crates for this source_item:\n{frappe.as_json(crate_details, indent=2)}'
                )
                # Simple user-facing error message
                user_error_msg = (
                    f'Scanned quantity ({scanned_qty} {row.uom}) exceeds available quantity '
                    f'({allocated_qty} {row.uom}) for item {row.item_code} from {row.from_warehouse}. '
                )
                raise pick_stream.exceptions.ValidationError(user_error_msg)

    def validate_scanned_qty(self):
        item_qty_map = {}
        for crate in self.item_crates:
            if crate.source_item in item_qty_map:
                item_qty_map[crate.source_item] += crate.qty
            else:
                item_qty_map[crate.source_item] = crate.qty
        for row in self.items:
            row.scanned_qty = item_qty_map.get(row.name, 0)
            if row.scanned_qty == 0:
                continue
            if row.scanned and row.scanned_qty < 0:
                raise pick_stream.exceptions.ValidationError(
                    f'Scanned qty {row.scanned_qty} cannot be less than 0 for item {row.item_code}'
                )
            if row.scanned and row.scanned_qty > row.requested_qty:
                raise pick_stream.exceptions.ValidationError(
                    f'Scanned qty {row.scanned_qty} exceeds requested qty {row.requested_qty} for item {row.item_code}'
                )          
            
    def set_item_locations(self):
        """
        Recalculates and rebuilds the entire items child table by allocating stock from available warehouses,
        excluding already-scanned/skipped items, and splitting items across multiple locations as needed.
        
        Process: Aggregates items → finds available locations → allocates across warehouses → rebuilds items table.

        Mutates: Clears and repopulates self.items with warehouse-specific rows, sorted naturally by warehouse name.
        """
        items = self.aggregate_item_qty()
        scanned_items_details = self.get_scanned_items_details(items)
        settings = pick_stream.utils.get_settings()
        # Set default source warehouse if none is set on Material Request
        default_set_from_warehouse = settings.default_set_from_warehouse
        set_from_warehouse = frappe.db.get_value(
            'Material Request',
            self.material_request,
            'set_from_warehouse'
        )
        from_warehouses = [set_from_warehouse] if set_from_warehouse else [default_set_from_warehouse]
        from_warehouses.extend(get_descendants_of('Warehouse', from_warehouses))
        # Reset Items
        reset_rows = []
        for row in self.get('items'):
            if not row.scanned_qty and not row.skipped:
                reset_rows.append(row)
        for row in reset_rows:
            self.remove(row)
        updated_locations = frappe._dict()
        self.item_location_map = frappe._dict()
        for item_doc in items:
            item_code = item_doc.item_code
            self.item_location_map.setdefault(
                item_code,
                get_available_item_locations(
                    item_code,
                    from_warehouses,
                    self.item_count_map.get(item_code),
                    scanned_item_details=scanned_items_details.get(item_code)
                )
            )
            locations = get_item_with_location_and_quantity(item_doc, self.item_location_map)
            item_doc.idx = None
            item_doc.name = None
            for row in locations:
                location = item_doc.as_dict()
                location.update(row)
                key = (
                    location.item_code,
                    location.from_warehouse,
                    location.uom,
                    location.material_request_item
                )
                if key not in updated_locations:
                    updated_locations.setdefault(key, location)
                else:
                    updated_locations[key].qty += location.qty
        sorted_locations = sorted(updated_locations.values(), key=lambda loc: natural_sort_key(loc.get('from_warehouse', '')))
        for location in sorted_locations:
            self.append('items', location)

    def aggregate_item_qty(self):
        """
        Filters out already-processed items (scanned/skipped) and non-stock items, then 
        calculates total requested quantity per item.
        
        Sets self.item_count_map = {item_code: total_requested_qty}
        
        Returns: List of unprocessed items ready for warehouse location assignment.
        """
        items = self.items
        self.item_count_map = {}
        item_list = []
        for item in items:
            # Skip items that are already processed (scanned or skipped)
            if item.scanned_qty or item.skipped:
                continue
            if not cint(frappe.get_cached_value('Item', item.item_code, 'is_stock_item')):
                continue
            item_code = item.item_code
            # Reset idx and name for processing
            item.idx = None
            item.name = None
            item_list.append(item)
            # Maintain count of each item - sum up all unprocessed items for this item_code
            self.item_count_map.setdefault(item_code, 0)
            self.item_count_map[item_code] += flt(item.requested_qty)
        return item_list
        
    def get_scanned_items_details(self, items):
        """
        Returns quantities already scanned for items in other incomplete Source documents,
        plus quantities from current Source, to prevent double-allocation of stock.
        
        Returns: {item_code: {warehouse: {'scanned_qty': float}}}
        
        Used by: get_available_item_locations() to exclude already-scanned stock from new picks.
        """
        scanned_items = frappe._dict()
        if not items:
            return scanned_items
        items_data = self.get_source_items(items)
        for item_data in items_data:
            key = item_data.from_warehouse  
            if item_data.item_code not in scanned_items:
                scanned_items[item_data.item_code] = {}
            if key not in scanned_items[item_data.item_code]:
                scanned_items[item_data.item_code][key] = frappe._dict({
                    'scanned_qty': 0
                })
            scanned_items[item_data.item_code][key]['scanned_qty'] += flt(item_data.scanned_qty)
        self.update_scanned_item_from_current_source(scanned_items)
        return scanned_items

    def get_source_items(self, items):
        """
        Queries other incomplete Source documents for items already scanned but not yet completed,
        to prevent concurrent sources from allocating the same stock.
        
        Returns: [{item_code, from_warehouse, scanned_qty}] from other in-progress Sources.
        """
        source = frappe.qb.DocType('Source')
        source_item = frappe.qb.DocType('Source Item')
        query = (
            frappe.qb.from_(source)
            .inner_join(source_item)
            .on(source.name == source_item.parent)
            .select(
                source_item.item_code,
                source_item.from_warehouse,
                source_item.scanned_qty,
            )
            .where(
                (source_item.item_code.isin([x.item_code for x in items]))
                & (source.status != 'Completed')
                & (source_item.scanned_qty > 0)
                & (source.name != self.name)
                & (source.docstatus != 1)
                & (source.docstatus != 2)
            )
        )
        if self.name:
            query = query.where(source_item.parent != self.name)
        query = query.for_update()
        return query.run(as_dict=True)
    
    def update_scanned_item_from_current_source(self, scanned_items):
        """
        Adds currently scanned/skipped items to the scanned_items dict to prevent re-allocation.
        For skipped items, marks entire warehouse stock as "scanned" to block future picks from that location.
        
        Mutates: scanned_items dict in-place by adding/updating scanned quantities per warehouse.
        """
        for row in self.items:
            if flt(row.scanned_qty) > 0 or row.skipped:
                key = row.from_warehouse
                if row.item_code not in scanned_items:
                    scanned_items[row.item_code] = {}
                if key not in scanned_items[row.item_code]:
                    scanned_items[row.item_code][key] = frappe._dict({'scanned_qty': 0})
                if flt(row.scanned_qty) > 0:
                    scanned_items[row.item_code][key]['scanned_qty'] += flt(row.scanned_qty)
                # For skipped items, mark the entire available quantity as 'scanned' 
                # to prevent new items from being created for this warehouse
                elif row.skipped:
                    # Get the actual available quantity in this warehouse
                    bin_qty = frappe.db.get_value('Bin', {
                        'item_code': row.item_code, 
                        'warehouse': row.from_warehouse
                    }, 'actual_qty') or 0
                    scanned_items[row.item_code][key]['scanned_qty'] += flt(bin_qty)

    
def get_available_item_locations(item_code, from_warehouses, requested_qty, scanned_item_details=None):
    """
    Returns list of warehouses with available stock for an item, filtered by already-scanned quantities
    and limited to the requested quantity needed.
    
    Returns: [{warehouse, qty}] - warehouses with allocable stock after excluding scanned items.
    """
    locations = []
    locations = get_available_item_locations_for_item(item_code, from_warehouses)
    if scanned_item_details:
        locations = filter_locations_by_scanned_items(locations, scanned_item_details)
    if locations:
        locations = get_locations_based_on_requested_qty(locations, requested_qty)
    validate_scanned_items(item_code, requested_qty, locations, scanned_item_details)
    return locations


def get_available_item_locations_for_item(item_code, from_warehouses):
    """
    Queries Bin table for warehouses that have actual stock (qty > 0) for the given item,
    filtered to allowed warehouses, ordered by creation date (FIFO).
    
    Returns: [{warehouse, qty}] - all locations with positive stock, oldest first.
    """
    bin = frappe.qb.DocType('Bin')
    query = (
        frappe.qb.from_(bin)
        .select(bin.warehouse, bin.actual_qty.as_('qty'))
        .where((bin.item_code == item_code) & (bin.actual_qty > 0))
        .orderby(bin.creation)
    )
    query = query.where(bin.warehouse.isin(from_warehouses))
    item_locations = query.run(as_dict=True)
    return item_locations


def filter_locations_by_scanned_items(locations, scanned_item_details) -> list[dict]:
    """
    Reduces available quantities in each location by subtracting already-scanned quantities
    from other Sources, removing locations with zero remaining stock.

    Mutates: scanned_item_details (resets scanned_qty to 0 after deduction).

    Returns: Filtered locations list with adjusted quantities excluding scanned stock.
    """
    filterd_locations = []
    for row in locations:
        key = row.warehouse
        scanned_qty = scanned_item_details.get(key, {}).get('scanned_qty', 0)
        if not scanned_qty:
            filterd_locations.append(row)
            continue
        if scanned_qty >= row.qty:
            row.qty = 0
        else:
            row.qty -= scanned_qty
            scanned_item_details[key]['scanned_qty'] = 0.0
        if row.qty > 0:
            filterd_locations.append(row)
    return filterd_locations
    

def get_locations_based_on_requested_qty(locations, requested_qty):
    """
    Allocates stock from warehouses sequentially until requested quantity is fulfilled,
    taking full warehouse quantity or partial as needed.
    
    Returns: [{warehouse, qty}] - minimum set of locations needed to meet requested_qty.

    Stops: When requested_qty is satisfied or all locations exhausted.
    """
    filtered_locations = []
    for location in locations:
        if location.qty >= requested_qty:
            location.qty = requested_qty
            filtered_locations.append(location)
            break
        requested_qty -= location.qty
        filtered_locations.append(location)
    return filtered_locations


def validate_scanned_items(item_code, requested_qty, locations, scanned_item_details=None):
    """
    Removes negative quantity locations and logs errors if total available stock is insufficient
    to fulfill requested quantity after accounting for already-scanned items.
    
    Mutates: Removes invalid locations from the list in-place.

    Logs: Different error messages for stock scanned elsewhere vs. insufficient stock.
    """
    for location in list(locations):
        if location['qty'] < 0:
            locations.remove(location)
    total_qty_available = sum(location.get('qty') for location in locations)
    remaining_qty = requested_qty - total_qty_available
    if remaining_qty > 0:
        if scanned_item_details:
            frappe.log_error(
                message=_('{0} units of Item {1} is scanned already in another Source.').format(
                    remaining_qty, get_link_to_form('Item', item_code)
                ),
                title=_('[Pick Stream] Already Scanned'),
            )
        else:
            frappe.log_error(
                message=_('{0} units of Item {1} is not available in any of the warehouses.').format(
                    remaining_qty, get_link_to_form('Item', item_code)
                ),
                title=_('[Pick Stream] Insufficient Stock'),
            )

               
def get_item_with_location_and_quantity(item_doc, item_location_map):
    """
    Allocates requested quantity across available warehouse locations, rounding down for whole-number UOMs,
    and updates item_location_map to track remaining stock in each warehouse.
    
    Returns: [{qty, from_warehouse, available_qty}] - warehouse allocations for this item.

    Mutates: item_location_map to reflect consumed stock, re-adding locations with remaining qty.
    """
    available_locations = item_location_map.get(item_doc.item_code)
    locations = []
    remaining_stock_qty = item_doc.requested_qty
    while remaining_stock_qty > 0 and available_locations:
        item_location = available_locations.pop(0)
        item_location = frappe._dict(item_location)
        original_qty = frappe.db.get_value('Bin', {
            'warehouse': item_location.warehouse,
            'item_code': item_doc.item_code
        }, ['actual_qty'])
        qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
        uom_must_be_whole_number = frappe.get_cached_value('UOM', item_doc.uom, 'must_be_whole_number')
        if uom_must_be_whole_number:
            qty = floor(qty)
        locations.append(
            frappe._dict({
                'qty': qty,
                'from_warehouse': item_location.warehouse,
                'available_qty': original_qty
            })
        )
        remaining_stock_qty -= qty
        qty_diff = item_location.qty - qty
        # if extra quantity is available push current warehouse to available locations
        if qty_diff > 0:
            item_location.qty = qty_diff
            available_locations = [item_location, *available_locations]
    # update available locations for the item
    item_location_map[item_doc.item_code] = available_locations
    return locations


def natural_sort_key(warehouse_name):
    # Split the string into text and number parts
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split(r'(\d+)', warehouse_name)]