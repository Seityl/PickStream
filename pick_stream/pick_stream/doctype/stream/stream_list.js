frappe.listview_settings['Stream'] = {
    hide_name_column: true,
    
    get_indicator: function(doc) {
		const status_colors = {
            "Picking": "blue",           
            "Waiting": "grey",           
			"In Transit": "yellow",      
			"Verifying": "purple",       
			"Completed": "green"
		};
		return [__(doc.status), status_colors[doc.status], "status,=,"+doc.status];
	},
}