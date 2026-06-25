# -*- coding: utf-8 -*-

from odoo import models, fields


class ContactAccountType(models.Model):
    _name = 'contact.account.type'
    _description = 'Account Type'

    name = fields.Char(string='Name', required=True)


class ContactAccountOwner(models.Model):
    _name = 'contact.account.owner'
    _description = 'Account Type'

    name = fields.Char(string='Name', required=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    account_owner = fields.Many2one('contact.account.owner', string='Account Owner')
    account_type = fields.Many2one('contact.account.type', string='Account Type')
    ownership = fields.Char(string='Ownership')
    kare = fields.Char(string='Kare')
    locked = fields.Boolean(string='Is Locked')
