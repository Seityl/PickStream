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
		if (validate_workflow_flags(frm, cdt, cdn)) {
			validate_workflow_uniqueness(frm, cdt, cdn);
		}
	},
	
	receiving_after_verification: function(frm, cdt, cdn) {
		if (validate_workflow_flags(frm, cdt, cdn)) {
			validate_workflow_uniqueness(frm, cdt, cdn);
		}
	},
	
	verification_after_receiving: function(frm, cdt, cdn) {
		if (validate_workflow_flags(frm, cdt, cdn)) {
			validate_workflow_uniqueness(frm, cdt, cdn);
		}
	},
	
	receiving_after_transit: function(frm, cdt, cdn) {
		if (validate_workflow_flags(frm, cdt, cdn)) {
			validate_workflow_uniqueness(frm, cdt, cdn);
		}
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
	if (row.verification_after_receiving) {
		return "Pick → Transit → Receive → Verify";
	}
	
	if (row.transit_after_verification) {
		return "Pick → Verify → Transit → Receive";
	}
	
	if (row.receiving_after_verification) {
		return "Pick → Verify → Receive";
	}
	
	return null;
}

function validate_workflow_uniqueness(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	let workflows = frm.doc.workflow_settings || [];
	
	// Get the workflow path for the current row
	let current_workflow_path = get_workflow_path(row);
	
	// Skip validation if no workflow path is defined
	if (!current_workflow_path) {
		return;
	}
	
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
	
	// Count active flags
	let active_flags = [];
	
	if (row.verification_after_receiving) {
		active_flags.push('Verification After Receiving');
	}
	if (row.transit_after_verification) {
		active_flags.push('Transit After Verification');
	}
	if (row.receiving_after_verification) {
		active_flags.push('Receiving After Verification');
	}
	
	// Validation logic
	if (active_flags.length === 0) {
		frappe.msgprint({
			title: __('Missing Configuration'),
			message: __('At least one workflow flag must be enabled to define the workflow path'),
			indicator: 'orange'
		});
		return false;
	} else if (active_flags.length > 1) {
		frappe.msgprint({
			title: __('Invalid Configuration'),
			message: __('Only one workflow flag can be enabled at a time. Currently enabled: {0}', 
				[active_flags.join(', ')]),
			indicator: 'red'
		});
		return false;
	}
	
	return true;
}

function validate_warehouse_branch_match(frm, cdt, cdn, warehouse_field, branch_field) {
	let row = locals[cdt][cdn];
	let warehouse = row[warehouse_field];
	
	if (!warehouse) {
		frappe.model.set_value(cdt, cdn, branch_field, '');
		return;
	}
	
	let warehouse_maps = frm.doc.warehouse_group_map || [];
	let matching_map = warehouse_maps.find(map => map.warehouse === warehouse);
	
	if (matching_map) {
		frappe.model.set_value(cdt, cdn, branch_field, matching_map.branch);
		frappe.show_alert({
			message: __('Auto-selected branch: {0}', [matching_map.branch]),
			indicator: 'green'
		});
	}
}