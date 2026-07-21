# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import requests
import json

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    zkteco_api_url = fields.Char(string='ZKTeco API URL', config_parameter='zkteco_integration.api_url', default='http://89.147.152.188:8080')
    zkteco_username = fields.Char(string='Username', config_parameter='zkteco_integration.username')
    zkteco_password = fields.Char(string='Password', config_parameter='zkteco_integration.password')
    zkteco_last_sync = fields.Datetime(string='Last Sync Time', config_parameter='zkteco_integration.last_sync')

    def action_test_connection(self):
        self.ensure_one()
        url = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.api_url')
        username = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.username')
        password = self.env['ir.config_parameter'].sudo().get_param('zkteco_integration.password')
        
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
                    self.env['ir.config_parameter'].sudo().set_param('zkteco_integration.token', token)
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

