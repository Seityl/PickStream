# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, floor, get_link_to_form
from frappe.utils.nestedset import get_descendants_of

from pick_stream.core import get_pick_stream_settings
from pick_stream.api_utils import exception_handler

class Source(Document):
    def before_save(self):
        self.set_item_locations()

    def set_item_locations(self):
        settings = get_pick_stream_settings()
        items = self.aggregate_item_qty()
        scanned_items_details = self.get_scanned_items_details(items)

        self.item_location_map = frappe._dict()

        # Default to sourcing from KG if no source warehouse is set on Material Request
        default_set_from_warehouse = settings.default_set_from_warehouse
        set_from_warehouse = frappe.db.get_value('Material Request', self.material_request, 'set_from_warehouse')
        from_warehouses = [set_from_warehouse] if set_from_warehouse else [default_set_from_warehouse]
        from_warehouses.extend(get_descendants_of('Warehouse', from_warehouses))

        # Create replica before resetting, to handle empty table on update after submit.
        locations_replica = self.get('items')
        # Reset Items
        self.delete_key('items')

        updated_locations = frappe._dict()
        
        for item_doc in items:
            item_code = item_doc.item_code
            self.item_location_map.setdefault(
                item_code,
                get_available_item_locations(
                    item_code,
                    from_warehouses,
                    self.item_count_map.get(item_code),
                    scanned_item_details=scanned_items_details.get(item_code)
                ),
            )

            locations = get_item_with_location_and_quantity(item_doc, self.item_location_map)

            item_doc.idx = None
            item_doc.name = None

            for row in locations:
                location = item_doc.as_dict()
                location.update(row)
                key = (
                    location.item_code,
                    location.warehouse,
                    location.uom,
                    location.material_request_item
                )

                if key not in updated_locations:
                    updated_locations.setdefault(key, location)
                else:
                    updated_locations[key].qty += location.qty

        sorted_locations = sorted(updated_locations.values(), key=lambda loc: loc.get("from_warehouse", ""))

        for location in sorted_locations:
            if location.scanned_qty > location.requested_qty:
                e = frappe.exceptions.DoesNotExistError(f"Error: Scanned qty {location.scanned_qty} exceeds requests qty {location.requested_qty} for item {location.item_code}")
                frappe.response = exception_handler(e)   
                raise e

            self.append('items', location)

        # This is to avoid empty Sources on update after submit.
        if not self.get('items') and self.docstatus == 1:
            for location in locations_replica:
                location.requested_qty = 0
                location.scanned_qty = 0
                self.append('items', location)
            frappe.log_error(
                message=_(
                    'Please Restock Items and Update the Pick List to continue. To discontinue, cancel the Pick List.'
                ),
                title=_('[Pick Stream] Out of Stock')
            )

    def aggregate_item_qty(self):
        items = self.items
        self.item_count_map = {}

        # Aggregate qty for same item
        item_map = OrderedDict()
        
        for item in items:
            if not item.item_code:
                frappe.throw(f"Row #{item.idx}: Item Code is Mandatory")
            if not cint(
                frappe.get_cached_value("Item", item.item_code, "is_stock_item")
            ) and not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code, "disabled": 0}):
                continue

            item_code = item.item_code
            material_request = item.material_request
            material_request_item = item.material_request_item

            key = (item_code, item.uom, item.to_warehouse, material_request, material_request_item)

            item.idx = None
            item.name = None

            if item_map.get(key):
                item_map[key].requested_qty += item.requested_qty
            else:
                item_map[key] = item

			# Maintain count of each item (useful to limit get query)
            self.item_count_map.setdefault(item_code, 0)
            self.item_count_map[item_code] += item.requested_qty

        return item_map.values()
        
    def get_scanned_items_details(self, items):
        scanned_items = frappe._dict()

        if not items:
            return scanned_items

        items_data = self.get_source_items(items)

        for item_data in items_data:
            key = item_data.to_warehouse

            if item_data.item_code not in scanned_items:
                scanned_items[item_data.item_code] = {}

            if key not in scanned_items[item_data.item_code]:
                scanned_items[item_data.item_code][key] = frappe._dict({
                    'scanned_qty': 0,
                    'to_warehouse': item_data.to_warehouse,
                })

            scanned_items[item_data.item_code][key]['scanned_qty'] += item_data.scanned_qty

        return scanned_items

    def get_source_items(self, items):
        source = frappe.qb.DocType('Source')
        source_item = frappe.qb.DocType('Source Item')
        query = (
            frappe.qb.from_(source)
            .inner_join(source_item)
            .on(source.name == source_item.parent)
            .select(
                source_item.item_code,
                source_item.to_warehouse,
                source_item.scanned_qty,
            )
            .where(
                (source_item.item_code.isin([x.item_code for x in items]))
                & (source_item.scanned_qty > 0)
                & (source.status != 'Completed')
            )
        )

        if self.name:
            query = query.where(source_item.parent != self.name)

        return query.run(as_dict=True)
    
def get_available_item_locations(item_code, from_warehouses, requested_qty, scanned_item_details=None):
    locations = []
    locations = get_available_item_locations_for_item(item_code, from_warehouses)

    if scanned_item_details:
        locations = filter_locations_by_scanned_items(locations, scanned_item_details)

    if locations:
        locations = get_locations_based_on_requested_qty(locations, requested_qty)

    validate_scanned_items(item_code, requested_qty, locations, scanned_item_details)

    return locations

def get_available_item_locations_for_item(item_code, from_warehouses):
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
	filterd_locations = []
	for row in locations:
		key = row.warehouse
		scanned_qty = scanned_item_details.get(key, {}).get('scanned_qty', 0)

		if not scanned_qty:
			filterd_locations.append(row)
			continue

		if scanned_qty > row.qty:
			row.qty = 0
			scanned_item_details[key]['scanned_qty'] -= row.qty

		else:
			row.qty -= scanned_qty
			scanned_item_details[key]['scanned_qty'] = 0.0

		if row.qty > 0:
			filterd_locations.append(row)

	return filterd_locations

def get_locations_based_on_requested_qty(locations, requested_qty):
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
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []

	remaining_stock_qty = item_doc.requested_qty

	while remaining_stock_qty > 0 and available_locations:
		item_location = available_locations.pop(0)
		item_location = frappe._dict(item_location)

		qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		uom_must_be_whole_number = frappe.get_cached_value("UOM", item_doc.uom, "must_be_whole_number")

		if uom_must_be_whole_number:
			qty = floor(qty)

		locations.append(
			frappe._dict({
                "qty": qty,
                "from_warehouse": item_location.warehouse,
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