# -*- coding: utf-8 -*-
from odoo import models, fields, exceptions

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    punch_id = fields.Char(string='ZKTeco Punch ID', help='Unique employee code in ZKTeco BioTime', copy=False)
    
    def action_sync_zkteco_punch_id(self):
        """Server action to map ZKTeco punch_id based on employee name."""
        # Security Check
        if not self.env.user.has_group('zkteco_attendance.group_zkteco_user'):
            raise exceptions.UserError("You must be a ZKTeco User to run this action.")
            
        zkteco_sync_model = self.env['zkteco.sync']
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.api_url')
        if not url:
            raise exceptions.UserError("ZKTeco Sync: API URL not configured.")
        if not url.endswith('/'):
            url += '/'
        headers = zkteco_sync_model._get_api_headers()
        if not headers:
            raise exceptions.UserError("ZKTeco Sync: No Auth token found. Please Test Connection in settings.")

        # Fetch all ZKTeco employees
        import requests
        employees_url = f"{url}personnel/api/employees/"
        params = {'page_size': 1000}
        all_zk_employees = []
        
        try:
            response = requests.get(employees_url, headers=headers, params=params, timeout=20)
            if response.status_code == 404:
                employees_url = f"{url}iclock/api/employees/"
                response = requests.get(employees_url, headers=headers, params=params, timeout=20)
                
            if response.status_code == 200:
                data = response.json()
                all_zk_employees = data.get('data', [])
                next_url = data.get('next')
                while next_url:
                    resp = requests.get(next_url, headers=headers, timeout=20)
                    if resp.status_code == 200:
                        next_data = resp.json()
                        all_zk_employees.extend(next_data.get('data', []))
                        next_url = next_data.get('next')
                    else:
                        break
            else:
                raise exceptions.UserError(f"API Connection Failed: ZKTeco returned HTTP {response.status_code} - {response.text[:100]}")
        except requests.exceptions.RequestException as e:
            raise exceptions.UserError(f"Network Error: Could not connect to ZKTeco Server. Details: {str(e)}")
        except exceptions.UserError:
            raise
        except Exception as e:
            raise exceptions.UserError(f"Unexpected Error: {str(e)}")

        if not all_zk_employees:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Failed',
                    'message': 'No employees found in ZKTeco.',
                    'type': 'danger',
                }
            }

        # Process ZKTeco employees into lookup dictionaries
        zk_email_map = {}
        zk_name_map = {}
        
        for emp in all_zk_employees:
            punch_id = emp.get('emp_code')
            if not punch_id:
                continue
                
            email = emp.get('email') or ''
            first_name = emp.get('first_name') or ''
            last_name = emp.get('last_name') or ''
            emp_name = f"{first_name} {last_name}".strip().lower()
            
            if email:
                zk_email_map[email.lower()] = str(punch_id)
            if emp_name:
                zk_name_map[emp_name] = str(punch_id)

        # Update ONLY the selected Odoo employees
        updated_count = 0
        for employee in self:
            # Skip if they already have a punch ID mapped
            if employee.punch_id:
                continue
                
            match_found = False
            emp_email = employee.work_email.strip().lower() if employee.work_email else ''
            emp_name = employee.name.strip().lower() if employee.name else ''
            
            # 1. Check by email
            if emp_email and emp_email in zk_email_map:
                employee.punch_id = zk_email_map[emp_email]
                match_found = True
            # 2. Check by name
            elif emp_name and emp_name in zk_name_map:
                employee.punch_id = zk_name_map[emp_name]
                match_found = True
                
            if match_found:
                updated_count += 1

        if updated_count > 0:
            message = f"Successfully linked {updated_count} selected Odoo employees to their ZKTeco Punch IDs."
            msg_type = 'success'
        else:
            message = "No matching ZKTeco employees were found for the selected records, or they already have a Punch ID."
            msg_type = 'warning'
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Employee Mapping Complete',
                'message': message,
                'sticky': False,
                'type': msg_type,
            }
        }
