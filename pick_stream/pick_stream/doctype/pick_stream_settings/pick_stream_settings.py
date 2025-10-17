# Copyright (c) 2025, Jollys Pharmacy Limited and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class PickStreamSettings(Document):
    def validate(self):
        # Normalize item types
        for row in self.item_types:
            row.item_type = str(row.item_type).lower()
            row.prefix = str(row.prefix).upper()
        # Normalize crate settings
        for row in self.crate_settings:
            row.color = str(row.color).capitalize()
            row.prefix = str(row.prefix).upper()
        # Validate workflow settings
        self.validate_workflow_settings()
    
    def validate_workflow_settings(self):
        """Validate workflow configuration for each workflow"""
        active_workflows = {}
        for workflow in self.workflow_settings:
            if workflow.is_active:
                workflow_path = get_workflow_path(workflow)
                workflow_key = f"{workflow.target_warehouse}||{workflow_path}"
                # Check for duplicate active workflows with same target warehouse AND workflow path
                if workflow_key in active_workflows:
                    frappe.throw(
                        _('Duplicate active workflow found for Target Warehouse: {0} with workflow path: {1}').format(
                            workflow.target_warehouse,
                            workflow_path
                        )
                    )
                active_workflows[workflow_key] = workflow
            # Validate workflow flags
            self.validate_workflow_flags(workflow)
    
    def validate_workflow_flags(self, workflow):
        """Validate workflow flag combinations"""
        # Count how many workflow flags are enabled
        active_flags = []
        if workflow.verification_after_receiving:
            active_flags.append('Verification After Receiving')
        if workflow.transit_after_verification:
            active_flags.append('Transit After Verification')
        if workflow.receiving_after_verification:
            active_flags.append('Receiving After Verification')
        # Only one workflow flag can be active at a time
        if len(active_flags) > 1:
            frappe.throw(
                _("Row #{0}: Only one workflow flag can be enabled at a time. "
                "Currently enabled: {1}").format(
                    workflow.idx,
                    ', '.join(active_flags)
                )
            )
    
    
def get_workflow_path(workflow):
    """Return a human-readable workflow path"""
    if  workflow.verification_after_receiving:
        return 'Pick → Transit → Receive → Verify'
    if workflow.transit_after_verification:
        return 'Pick → Verify → Transit → Receive'
    if workflow.receiving_after_verification:
        return 'Pick → Verify → Receive'
    return 'Unknown Workflow'