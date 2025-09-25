import frappe

def after_migrate():
    create_user_groups_from_item_groups()
    
def create_user_groups_from_item_groups():
    try:
        item_groups = frappe.get_all('Item Group', fields=['name'], order_by='name')
        if not item_groups:
            frappe.log_error(
                message='No Item Groups found in the system',
                title='[Pick Stream] Item Groups Migration'
            )
            return
        
        for item_group in item_groups:
            item_group_name = item_group.name
            
            try:
                existing_user_group = frappe.db.exists('User Group', item_group_name)
                if existing_user_group:
                    user_group_doc = frappe.get_doc('User Group', item_group_name)
                    
                    # Check if custom_is_item_group field exists and set it to 1
                    if hasattr(user_group_doc, 'custom_is_item_group'):
                        if user_group_doc.custom_is_item_group != 1:
                            user_group_doc.custom_is_item_group = 1
                            user_group_doc.save()

                    else:
                        frappe.log_error(
                            title='[Pick Stream]', 
                            message=f"custom_is_item_group field not found in User Group '{item_group_name}'"
                        )

                else:
                    user_group_doc = frappe.new_doc('User Group')
                    user_group_doc.update({
                        'name': item_group_name,
                        'custom_is_item_group': 1
                    })
                    
                    # Mandatory ignored to allow saving with no users
                    user_group_doc.insert(ignore_mandatory=True)
                    
            except Exception as e:
                frappe.log_error(
                    message=f"Error processing Item Group '{item_group_name}': {str(e)}",
                    title='[Pick Stream] Item Group to User Group Migration Error'
                )
                continue
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            message=f"Fatal error during Item Groups to User Groups migration: {str(e)}",
            title="[Pick Stream] Fatal Migration Error"
        )
        raise