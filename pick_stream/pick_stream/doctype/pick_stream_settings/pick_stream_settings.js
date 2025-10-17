// Copyright (c) 2025, Jollys Pharmacy Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on('Pick Stream Settings', {
	refresh: function(frm) {
        frm.set_query('warehouse', 'warehouse_group_map', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		frm.set_query('picking_warehouse_1', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		
		frm.set_query('picking_warehouse_2', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		
		frm.set_query('picking_warehouse_3', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 1
				}
			};
		});
		frm.set_query('target_warehouse', 'workflow_settings', function() {
			return {
				filters: {
					is_group: 0
				}
			};
		});
	},
});

frappe.ui.form.on('Pick Stream Workflow', {
	target_warehouse: function(frm, cdt, cdn) {
		validate_workflow_uniqueness(frm, cdt, cdn);
	},
	
	transit_after_verification: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
		validate_workflow_uniqueness(frm, cdt, cdn);
	},
	
	receiving_after_verification: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
		validate_workflow_uniqueness(frm, cdt, cdn);
	},
	
	verification_after_receiving: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
		validate_workflow_uniqueness(frm, cdt, cdn);
	},
	
	receiving_after_transit: function(frm, cdt, cdn) {
		validate_workflow_flags(frm, cdt, cdn);
		validate_workflow_uniqueness(frm, cdt, cdn);
	},

	picking_warehouse_1: function(frm, cdt, cdn) {
		validate_warehouse_branch_match(frm, cdt, cdn, 'picking_warehouse_1', 'picking_user_branch_1');
	},
	
	picking_warehouse_2: function(frm, cdt, cdn) {
		validate_warehouse_branch_match(frm, cdt, cdn, 'picking_warehouse_2', 'picking_user_branch_2');
	},
	
	picking_warehouse_3: function(frm, cdt, cdn) {
		validate_warehouse_branch_match(frm, cdt, cdn, 'picking_warehouse_3', 'picking_user_branch_3');
	}
});

function get_workflow_path(row) {
	// Pick → Transit → Receive → Verify
	if (row.receiving_after_transit && row.verification_after_receiving) {
		return "Pick → Transit → Receive → Verify";
	}
	
	// Pick → Verify → Transit → Receive
	if (row.transit_after_verification && row.receiving_after_verification) {
		return "Pick → Verify → Transit → Receive";
	}
	
	// Pick → Verify → Receive
	if (row.receiving_after_verification && !row.transit_after_verification) {
		return "Pick → Verify → Receive";
	}
	
	// Pick → Transit → Receive
	if (row.receiving_after_transit && !row.verification_after_receiving) {
		return "Pick → Transit → Receive";
	}
	
	// Pick → Receive → Verify
	if (row.verification_after_receiving && !row.receiving_after_transit) {
		return "Pick → Receive → Verify";
	}
	
	// Pick → Receive (direct)
	if (!row.verification_after_receiving && 
		!row.receiving_after_verification && 
		!row.transit_after_verification && 
		!row.receiving_after_transit) {
		return "Pick → Receive (Direct)";
	}
	
	return "Unknown Workflow";
}

function validate_workflow_uniqueness(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let workflows = frm.doc.workflow_settings || [];
	
	// Get the workflow path for the current row
	let current_workflow_path = get_workflow_path(row);
	
	// Find duplicates: same target warehouse, same workflow path, different row, and active
	let duplicates = workflows.filter(w => {
		if (w.name === row.name || !w.is_active || !row.is_active) {
			return false;
		}
		
		if (w.target_warehouse !== row.target_warehouse) {
			return false;
		}
		
		// Get workflow path for comparison
		let workflow_path = get_workflow_path(w);
		return workflow_path === current_workflow_path;
	});
	
	if (duplicates.length > 0) {
		frappe.msgprint({
			title: __('Duplicate Workflow'),
			message: __('An active workflow already exists for warehouse: {0} with workflow path: {1}', 
				[row.target_warehouse, current_workflow_path]),
			indicator: 'red'
		});
		
		// Clear the is_active flag instead of target_warehouse to allow different workflows
		frappe.model.set_value(cdt, cdn, 'is_active', 0);
	}
}

function validate_workflow_flags(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	
	if (row.transit_after_verification && row.receiving_after_transit) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('Cannot enable both "Transit After Verification" and "Receiving After Transit" simultaneously'),
			indicator: 'red'
		});
		frappe.model.set_value(cdt, cdn, 'receiving_after_transit', 0);
		frappe.model.set_value(cdt, cdn, 'transit_after_verification', 0);
	}
	
	if (row.verification_after_receiving && row.transit_after_verification) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('Cannot enable "Verification After Receiving" and "Transit After Verification" simultaneously.'),
			indicator: 'red'
		});
		frappe.model.set_value(cdt, cdn, 'verification_after_receiving', 0);
		frappe.model.set_value(cdt, cdn, 'transit_after_verification', 0);
	}
	
	if (row.verification_after_receiving && row.receiving_after_verification) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('Cannot enable both "Verification After Receiving" and "Receiving After Verification" simultaneously'),
			indicator: 'red'
		});
		frappe.model.set_value(cdt, cdn, 'verification_after_receiving', 0);
		frappe.model.set_value(cdt, cdn, 'receiving_after_verification', 0);
	}
	
	if (row.receiving_after_transit && !row.verification_after_receiving) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('When "Receiving After Transit" is enabled, "Verification After Receiving" must also be enabled'),
			indicator: 'orange'
		});
		frappe.model.set_value(cdt, cdn, 'receiving_after_transit', 0);
	}
}

function validate_warehouse_branch_match(frm, cdt, cdn, warehouse_field, branch_field) {
	let row = locals[cdt][cdn];
	let warehouse = row[warehouse_field];
	
	if (!warehouse) {
		frappe.model.set_value(cdt, cdn, branch_field, '');
		return;
	}
	
	let warehouse_maps = frm.doc.warehouse_group_map || [];
	let matching_map = warehouse_maps.find(map => {
		return frappe.db.get_value('Warehouse', warehouse, 'parent_warehouse')
			.then(r => r.message && r.message.parent_warehouse === map.warehouse);
	});
	
	if (matching_map && !row[branch_field]) {
		frappe.model.set_value(cdt, cdn, branch_field, matching_map.branch);
		frappe.show_alert({
			message: __('Auto-selected branch: {0}', [matching_map.branch]),
			indicator: 'green'
		});
	}
}