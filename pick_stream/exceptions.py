"""
Custom exception classes for Pick Stream system.

Defines HTTP-aware exceptions for various error scenarios:
- ValidationError: Business logic validation failures (HTTP 417)
- DoesNotExistError: Resource not found errors (HTTP 404)
- PermissionError: Access control violations (HTTP 403)
- SystemError: Internal system/configuration errors (HTTP 500)

Author: Jeriel Francis

Copyright (c) 2025, Jollys Pharmacy Limited and contributors
For license information, please see license.txt
"""



from __future__ import unicode_literals


class ValidationError(Exception):
	http_status_code = 417


class DoesNotExistError(Exception):
	http_status_code = 404


class PermissionError(Exception):
	http_status_code = 403


class SystemError(Exception):
	http_status_code = 500