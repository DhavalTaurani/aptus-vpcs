from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'


    date_of_joining = fields.Date("Date of Joining", compute='_compute_date_of_joining')
    date_of_resignation = fields.Date("Date of Resignation", compute='_compute_date_of_resignation')


    @api.depends('version_ids.contract_date_start')
    def _compute_date_of_joining(self):
        for employee in self:
            # Get all start dates and filter out any that are False/None
            start_dates = employee.version_ids.mapped('contract_date_start')
            valid_dates = [d for d in start_dates if d]
            
            if valid_dates:
                # Now min() only compares actual date objects
                employee.date_of_joining = min(valid_dates)
            else:
                employee.date_of_joining = False

    @api.depends('version_ids.contract_date_end')
    def _compute_date_of_resignation(self):
        for employee in self:
            # Get the latest contract end date
            if employee.version_ids:
                #  Check if all the versions have an end date
                if not all(employee.version_ids.mapped('contract_date_end')):
                    employee.date_of_resignation = False
                    continue
                # Assuming the latest contract end date indicates resignation
                latest_contract_end = max(employee.version_ids.mapped('contract_date_end'))
                employee.date_of_resignation = latest_contract_end
            else:
                employee.date_of_resignation = False


