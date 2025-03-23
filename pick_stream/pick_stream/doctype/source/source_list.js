frappe.listview_settings['Source'] = {
    hide_name_column: true,
    has_indicator_for_draft: true,

    get_indicator: function(doc) {
        const status_colors = {
            "Working": "blue",           
            "Completed": "green"
        };
        console.log(status_colors)
      return [__(doc.status), status_colors[doc.status], "status,=,"+doc.status];
    }
}
  