from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    _inherit = 'hr.leave'


    leave_type_category = fields.Selection(
        selection=[
            ('annual', 'Annual Leave'),
            ('annual_airticket', 'Annual Leave with Airticket'),
            ('leave_encashment', 'Leave Encashment'),
        ],
        string='Leave Type Category',
        required=False,
        help='Category of the leave type'
    )

    # Override action_approve method to check that leave type category is set to annual_airticket once in the year
    def action_approve(self):
        res = super(HrLeave, self).action_approve()
        for leave in self:
            if leave.leave_type_category == 'annual_airticket':
                # Check if there is already an approved leave of this type for the employee in the current year
                current_year = fields.Date.today().year
                existing_leaves = self.search([
                    ('employee_id', '=', leave.employee_id.id),
                    ('leave_type_category', '=', 'annual_airticket'),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', f'{current_year}-01-01'),
                    ('date_to', '<=', f'{current_year}-12-31'),
                    ('id', '!=', leave.id)
                ])
                if existing_leaves:
                    raise ValidationError("An employee can only have one approved 'Annual Leave with Airticket' per year. Please change the leave type category.")
        return res