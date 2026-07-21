# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import requests
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse

_logger = logging.getLogger(__name__)

class ZktecoSync(models.AbstractModel):
    _name = 'zkteco.sync'
    _description = 'ZKTeco Attendance Sync Utility'

    @api.model
    def _get_api_headers(self):
        token = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.token')
        if not token:
            return False
        return {
            'Authorization': f'JWT {token}',
            'Content-Type': 'application/json'
        }

    @api.model
    def _refresh_token(self):
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.api_url')
        username = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.username')
        password = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.password')

        if not url or not username or not password:
            _logger.error("ZKTeco Sync: Cannot refresh token. Missing credentials.")
            return False

        if not url.endswith('/'):
            url += '/'
            
        auth_url = f"{url}jwt-api-token-auth/"
        try:
            response = requests.post(auth_url, json={'username': username, 'password': password}, timeout=10)
            if response.status_code == 200:
                token = response.json().get('token')
                if token:
                    self.env['ir.config_parameter'].sudo().set_param('zkteco_integration.token', token)
                    _logger.info("ZKTeco Sync: Token successfully auto-refreshed.")
                    return token
        except Exception as e:
            _logger.error(f"ZKTeco Sync: Auto-refresh failed: {str(e)}")
        return False

    @api.model
    def _fetch_transactions(self, url, headers, last_sync=None, retry=True):
        transactions_url = f"{url}iclock/api/transactions/"
        params = {'page_size': 1000}
        
        # If the API supports filtering by timestamp, you can add it to params here.
        # e.g., if last_sync: params['start_time'] = last_sync.strftime('%Y-%m-%d %H:%M:%S')

        all_transactions = []
        try:
            response = requests.get(transactions_url, headers=headers, params=params, timeout=20)
            if response.status_code == 200:
                data = response.json()
                all_transactions = data.get('data', [])
                
                # Handle pagination if data has 'next' page
                next_url = data.get('next')
                while next_url:
                    resp = requests.get(next_url, headers=headers, timeout=20)
                    if resp.status_code == 200:
                        next_data = resp.json()
                        all_transactions.extend(next_data.get('data', []))
                        next_url = next_data.get('next')
                    else:
                        break
            elif response.status_code == 401 and retry:
                _logger.warning("ZKTeco Sync: Token expired. Attempting to auto-refresh...")
                new_token = self._refresh_token()
                if new_token:
                    headers['Authorization'] = f'JWT {new_token}'
                    return self._fetch_transactions(url, headers, last_sync, retry=False)
                else:
                    _logger.error("ZKTeco Sync: Token auto-refresh failed. Aborting fetch.")
            else:
                _logger.error(f"ZKTeco Sync Failed: {response.status_code} - {response.text}")
        except Exception as e:
            _logger.error(f"ZKTeco Sync API Error: {str(e)}")
            
        return all_transactions


    @api.model
    def sync_attendance(self):
        _logger.info("Starting ZKTeco Attendance Sync...")
        
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.api_url')
        if not url:
            _logger.warning("ZKTeco Sync: API URL not configured.")
            return

        if not url.endswith('/'):
            url += '/'

        headers = self._get_api_headers()
        if not headers:
            return

        last_sync_str = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.last_sync')
        last_sync = fields.Datetime.from_string(last_sync_str) if last_sync_str else None

        transactions = self._fetch_transactions(url, headers, last_sync)
        if not transactions:
            _logger.info("ZKTeco Sync: No new transactions found.")
            return

        # Process transactions
        # Group transactions by employee punch_id and date
        emp_records = {}
        for trans in transactions:
            punch_id = trans.get('emp_code')
            punch_time_str = trans.get('punch_time')
            if not punch_id or not punch_time_str:
                continue
                
            punch_time = parse(punch_time_str) # Requires dateutil.parser
            date_key = punch_time.date()
            
            if punch_id not in emp_records:
                emp_records[punch_id] = {}
            if date_key not in emp_records[punch_id]:
                emp_records[punch_id][date_key] = []
                
            emp_records[punch_id][date_key].append(punch_time)

        # Match with Odoo employees and create/update attendance
        employee_model = self.env['hr.employee']
        attendance_model = self.env['hr.attendance']

        for punch_id, dates in emp_records.items():
            employee = employee_model.search([('punch_id', '=', str(punch_id))], limit=1)
            if not employee:
                _logger.warning(f"ZKTeco Sync: Skipping punch for unknown punch_id {punch_id} (Auto-create disabled)")
                continue
                
            for date_key, times in dates.items():
                times.sort()
                check_in = times[0]
                check_out = times[-1] if len(times) > 1 else False

                # Search if attendance record already exists for this day to avoid duplicates
                domain = [
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', datetime.combine(date_key, datetime.min.time())),
                    ('check_in', '<=', datetime.combine(date_key, datetime.max.time()))
                ]
                existing_attendance = attendance_model.search(domain, limit=1)

                if existing_attendance:
                    # Update checkout if needed
                    if check_out and (not existing_attendance.check_out or existing_attendance.check_out < check_out):
                        existing_attendance.write({'check_out': check_out})
                else:
                    # Close any previous open attendances for this employee to prevent Odoo validation errors
                    open_attendances = attendance_model.search([
                        ('employee_id', '=', employee.id),
                        ('check_out', '=', False)
                    ])
                    for open_att in open_attendances:
                        try:
                            # Auto-close 1 minute after check-in if they forgot to punch out
                            open_att.write({'check_out': open_att.check_in + timedelta(minutes=1)})
                        except Exception as e:
                            _logger.error(f"Failed to auto-close attendance for {employee.name}: {e}")

                    # Create new attendance
                    vals = {
                        'employee_id': employee.id,
                        'check_in': check_in,
                    }
                    if check_out:
                        vals['check_out'] = check_out
                    
                    try:
                        attendance_model.create(vals)
                    except Exception as e:
                        _logger.error(f"Failed to create attendance for {employee.name} on {check_in}: {e}")

        # Update last sync time
        self.env['ir.config_parameter'].sudo().set_param('zkteco_integration.last_sync', fields.Datetime.now())
        _logger.info("ZKTeco Attendance Sync Completed.")
