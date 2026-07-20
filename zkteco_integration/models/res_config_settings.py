# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import requests
import json

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    zkteco_api_url = fields.Char(string='ZKTeco API URL', config_parameter='zkteco_attendance.api_url', default='http://89.147.152.188:8080')
    zkteco_username = fields.Char(string='Username', config_parameter='zkteco_attendance.username')
    zkteco_password = fields.Char(string='Password', config_parameter='zkteco_attendance.password')
    zkteco_token = fields.Char(string='Current Token', config_parameter='zkteco_attendance.token', help="Automatically generated token")
    zkteco_last_sync = fields.Datetime(string='Last Sync Time', config_parameter='zkteco_attendance.last_sync')

    def action_test_connection(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.api_url')
        username = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.username')
        password = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.password')
        
        if not url or not username or not password:
            raise exceptions.UserError('Please save the URL, Username, and Password first.')

        # Ensure URL formatting
        if not url.endswith('/'):
            url += '/'
        
        auth_url = f"{url}jwt-api-token-auth/"
        payload = {
            'username': username,
            'password': password
        }

        try:
            response = requests.post(auth_url, json=payload, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError:
                    raise exceptions.UserError(f"API returned success (200 OK), but the response was not valid JSON. This usually means the URL is incorrect and returning a webpage.\n\nRaw Response:\n{response.text[:500]}")
                
                token = data.get('token')
                if token:
                    self.env['ir.config_parameter'].sudo().set_param('zkteco_attendance.token', token)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Success',
                            'message': 'Connection successful! Token generated and saved.',
                            'sticky': False,
                            'type': 'success',
                        }
                    }
            raise exceptions.UserError(f"Failed to authenticate. Status: {response.status_code}\nResponse: {response.text}")
        except Exception as e:
            raise exceptions.UserError(f"Connection error: {str(e)}")

    def action_test_fetch_transactions(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.api_url')
        token = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.token')

        if not url or not token:
            raise exceptions.UserError('Please configure API settings and test connection to get a token first.')

        if not url.endswith('/'):
            url += '/'
            
        transactions_url = f"{url}iclock/api/transactions/"
        headers = {
            'Authorization': f'JWT {token}',
            'Content-Type': 'application/json'
        }

        try:
            # Fetch last 5 transactions as a test
            response = requests.get(transactions_url, headers=headers, params={'page_size': 5}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                formatted_data = json.dumps(data, indent=4)
                raise exceptions.UserError(f"Successfully fetched sample data:\n\n{formatted_data}")
            elif response.status_code == 401:
                # Token expired, user needs to re-authenticate
                raise exceptions.UserError("Authentication failed (401). Your token may have expired. Please click 'Test Connection' to generate a new token.")
            else:
                raise exceptions.UserError(f"Failed to fetch data. Status: {response.status_code}\nResponse: {response.text}")
        except exceptions.UserError:
            raise
        except Exception as e:
            raise exceptions.UserError(f"API Request Error: {str(e)}")

    def action_test_fetch_employees(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.api_url')
        token = self.env['ir.config_parameter'].sudo().get_param('zkteco_attendance.token')

        if not url or not token:
            raise exceptions.UserError('Please configure API settings and test connection to get a token first.')

        if not url.endswith('/'):
            url += '/'
            
        employees_url = f"{url}personnel/api/employees/"
        headers = {
            'Authorization': f'JWT {token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(employees_url, headers=headers, params={'page_size': 1}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                total_count = data.get('count', 0)
                raise exceptions.UserError(f"Success! Found {total_count} employees registered in ZKTeco.")
            elif response.status_code == 404:
                # Fallback to older API endpoint if personnel app is not used
                employees_url = f"{url}iclock/api/employees/"
                response = requests.get(employees_url, headers=headers, params={'page_size': 1}, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    total_count = data.get('count', 0)
                    raise exceptions.UserError(f"Success! Found {total_count} employees registered in ZKTeco.")
                else:
                    raise exceptions.UserError(f"Failed to fetch employees. Status: {response.status_code}\nResponse: {response.text}")
            elif response.status_code == 401:
                raise exceptions.UserError("Authentication failed (401). Your token may have expired. Please click 'Test Connection' to generate a new token.")
            else:
                raise exceptions.UserError(f"Failed to fetch employees. Status: {response.status_code}\nResponse: {response.text}")
        except exceptions.UserError:
            raise
        except Exception as e:
            raise exceptions.UserError(f"API Request Error: {str(e)}")

    def action_sync_employees(self):
        self.ensure_one()
        try:
            result_msg = self.env['zkteco.sync'].sync_employees()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Employee Sync Complete',
                    'message': result_msg,
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            raise exceptions.UserError(str(e))
