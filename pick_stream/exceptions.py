from __future__ import unicode_literals

class ValidationError(Exception):
	http_status_code = 417

class DoesNotExistError(Exception):
	http_status_code = 404
	
class PermissionError(Exception):
	http_status_code = 403

class SystemError(Exception):
	http_status_code = 500