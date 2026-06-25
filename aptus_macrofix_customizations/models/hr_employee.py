from odoo import models, fields, api
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _order = 'employee_grade,name'

    # Basic Info
    employee_code = fields.Char("Employee Code")
    employee_status = fields.Selection([
        ('permanent', 'Permanent'),
        ('contractual', 'Contractual')
    ], string="Employee Status")
    nationality = fields.Many2one('res.country', string="Nationality")
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Designation")
    date_of_joining = fields.Date("Date of Joining")
    upload_cv = fields.Binary("Upload CV")
    upload_cv_filename = fields.Char("CV Filename")

    # Passport Info
    passport_number = fields.Char("Passport Number")
    passport_issue_date = fields.Date("Passport Issue Date")
    passport_expiry_date = fields.Date("Passport Expiry Date")

    # Address Info
    permanent_address = fields.Text("Permanent Address")
    residence_address = fields.Text("Residence Address")
    house_contract = fields.Binary("House Contract")
    house_contract_filename = fields.Char("House Contract")
    house_contract_start_date = fields.Date("House Contract Start Date")
    house_contract_expiry_date = fields.Date("House Contract Expiry Date")

    # Visa Info
    visa_number = fields.Char("Visa Number")
    visa_id_card_number = fields.Char("Visa ID Card Number")
    visa_issue_date = fields.Date("Visa Issue Date")
    visa_expiry_date = fields.Date("Visa Expiry Date")

    # Office Assets
    mobile_number = fields.Char("Mobile Number")
    car_brand = fields.Char("Car Brand")
    car_model = fields.Char("Car Model")
    car_number = fields.Char("Car Number")
    car_registration_number = fields.Char("Car Registration Number")
    car_registration_date = fields.Date("Car Registration Date")
    car_expiry_date = fields.Date("Car Expiry Date")
    insurance_date = fields.Date("Insurance Date")
    insurance_expiry_date = fields.Date("Insurance Expiry Date")
    laptop_brand = fields.Char("Laptop Brand")
    laptop_model = fields.Char("Laptop Model")
    laptop_serial_number = fields.Char("Laptop Serial Number")

    spouse_ids = fields.One2many('hr.employee.spouse', 'employee_id')
    children_ids = fields.One2many('hr.employee.child', 'employee_id')

    employee_grade = fields.Selection(selection=[('1a', '1A'), ('1b', '1B'), ('2a', '2A'), ('2b', '2B'), ('3a', '3A'), ('3b', '3B'), ('3c', '3C'), ('4a', '4A'), ('4b', '4B'), ('5a', '5A'), ('5b', '5B'), ('5c', '5C')], string='Employee Grade')

class HrEmployeeSpouse(models.Model):
    _name = 'hr.employee.spouse'
    _description = 'Employee Spouse Details'

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    name = fields.Char("Spouse Name")
    passport_number = fields.Char("Passport Number")
    passport_issue_date = fields.Date("Passport Issue Date")
    passport_expiry_date = fields.Date("Passport Expiry Date")
    id_card_number = fields.Char("ID Card Number")
    id_issue_date = fields.Date("ID Issue Date")
    id_expiry_date = fields.Date("ID Expiry Date")

class HrEmployeeChild(models.Model):
    _name = 'hr.employee.child'
    _description = 'Employee Children Details'

    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade')
    name = fields.Char("Child Name")
    passport_number = fields.Char("Passport Number")
    passport_issue_date = fields.Date("Passport Issue Date")
    passport_expiry_date = fields.Date("Passport Expiry Date")
    id_card_number = fields.Char("ID Card Number")
    id_issue_date = fields.Date("ID Issue Date")
    id_expiry_date = fields.Date("ID Expiry Date")
