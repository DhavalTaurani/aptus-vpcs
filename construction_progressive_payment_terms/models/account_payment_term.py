# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    # Progressive payment fields
    is_progressive = fields.Boolean(
        string='Progressive Payment Term',
        default=False,
        help='Enable progressive payment functionality for construction projects'
    )
    
    # Remove default balance line
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if vals.get('is_progressive'):
                record.line_ids.unlink()
        return records
    
    @api.onchange('is_progressive')
    def _onchange_is_progressive_display(self):
        """Set display_on_invoice to False for progressive payment terms"""
        if self.is_progressive:
            self.display_on_invoice = False
    construction_category = fields.Selection([
        ('elv', 'Extra Low Voltage (ELV)'),
        ('mep', 'Mechanical, Electrical, Plumbing (MEP)'),
        ('civil', 'Civil Construction'),
        ('structural', 'Structural Work'),
        ('infrastructure', 'Infrastructure'),
        ('fitout', 'Fit-out Work'),
        ('specialized', 'Specialized Systems'),
        ('generic', 'Generic Construction')
    ], string='Construction Category', 
        default='generic',
        help='Construction category this payment term is designed for')
    
    # Template management
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
        help='Mark as template for reuse across projects'
    )
    template_description = fields.Text(
        string='Template Description',
        help='Description of this payment term template'
    )
    
    # Progressive payment validation
    total_milestone_percentage = fields.Float(
        string='Total Milestone Percentage',
        compute='_compute_total_milestone_percentage',
        store=True,
        help='Total percentage of all progressive milestones'
    )
    
    # Milestone count for display
    milestone_count = fields.Integer(
        string='Milestone Count',
        compute='_compute_milestone_count',
        help='Number of progressive milestones defined'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('line_ids.value_amount', 'line_ids.is_milestone', 'is_progressive')
    def _compute_total_milestone_percentage(self):
        """Compute total percentage of all progressive milestones"""
        for term in self:
            if term.is_progressive:
                milestone_lines = term.line_ids.filtered('is_milestone')
                term.total_milestone_percentage = sum(
                    line.value_amount for line in milestone_lines 
                    if line.value == 'percent'
                )
            else:
                term.total_milestone_percentage = 0.0

    @api.depends('line_ids.is_milestone', 'is_progressive')
    def _compute_milestone_count(self):
        """Compute number of progressive milestones"""
        for term in self:
            if term.is_progressive:
                term.milestone_count = len(term.line_ids.filtered('is_milestone'))
            else:
                term.milestone_count = 0

    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    
    @api.constrains('is_progressive', 'line_ids')
    def _check_progressive_payment_configuration(self):
        """Validate progressive payment term configuration"""
        # Skip validation during module installation or data loading
        if (self.env.context.get('install_mode') or 
            self.env.context.get('module') or 
            self.env.context.get('import_file') or
            hasattr(self.env, 'registry') and self.env.registry._init):
            return
            
        for term in self:
            if term.is_progressive:
                milestone_lines = term.line_ids.filtered('is_milestone')
                
                # Only validate if we have milestone lines
                if not milestone_lines:
                    continue
                
                # Check percentage total for percent-based milestones
                percent_lines = milestone_lines.filtered(lambda l: l.value == 'percent')
                if percent_lines:
                    total_percentage = sum(line.value_amount for line in percent_lines)
                    if abs(total_percentage - 100.0) > 0.01:  # Allow small rounding differences
                        raise ValidationError(_(
                            'Total milestone percentages must equal 100%%. '
                            'Current total: %.2f%%'
                        ) % total_percentage)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    
    @api.onchange('is_progressive')
    def _onchange_is_progressive(self):
        """Handle changes to progressive payment flag"""
        if self.is_progressive:
            # If enabling progressive payments, ensure we have milestone lines
            if not self.line_ids.filtered('is_milestone'):
                # Create default milestone structure if none exists
                self._create_default_milestone_structure()
        else:
            # If disabling progressive payments, clear milestone flags
            for line in self.line_ids:
                line.is_milestone = False

    def _create_default_milestone_structure(self):
        """Create default milestone structure for progressive payments"""
        # Get default milestone structure based on construction category
        default_milestones = self._get_default_milestones()
        
        # Create all milestone lines in one operation to avoid validation issues
        line_vals = []
        for milestone in default_milestones:
            line_vals.append((0, 0, {
                'value': 'percent',
                'value_amount': milestone['percentage'],
                'nb_days': milestone['days'],
                'is_milestone': True,
                'milestone_type': milestone['type'],
                'milestone_description': milestone['description'],
            }))
        
        # Replace all lines at once to satisfy Odoo's validation
        self.line_ids = [(5, 0, 0)] + line_vals

    def _get_default_milestones(self):
        """Get default milestone structure based on construction category"""
        # Standard construction milestone structure
        default_structure = [
            {
                'type': 'advance',
                'percentage': 20.0,
                'days': 0,
                'description': 'Advance payment upon contract signing'
            },
            {
                'type': 'material_delivery',
                'percentage': 30.0,
                'days': 30,
                'description': 'Material delivery to site'
            },
            {
                'type': 'installation',
                'percentage': 35.0,
                'days': 60,
                'description': 'Installation completion'
            },
            {
                'type': 'testing_commissioning',
                'percentage': 10.0,
                'days': 90,
                'description': 'Testing and commissioning completion'
            },
            {
                'type': 'retention',
                'percentage': 5.0,
                'days': 365,
                'description': 'Retention release after warranty period'
            }
        ]
        
        # Category-specific adjustments could be added here
        category_adjustments = {
            'elv': default_structure,  # ELV uses standard structure
            'mep': default_structure,  # MEP uses standard structure
            'civil': default_structure,  # Civil uses standard structure
            # Add category-specific structures as needed
        }
        
        return category_adjustments.get(self.construction_category, default_structure)

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    
    def copy(self, default=None):
        """Override copy to handle progressive payment terms"""
        default = default or {}
        
        if self.is_progressive and self.is_template:
            # When copying a template, create a new instance
            default.update({
                'name': _('%s (Copy)') % self.name,
                'is_template': False,
            })
        
        return super().copy(default)

    # -------------------------------------------------------------------------
    # PAYMENT TERM COMPUTATION METHODS
    # -------------------------------------------------------------------------
    
    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency, cash_rounding=None):
        """Override to support progressive payment milestones while maintaining compatibility"""
        if not self.is_progressive:
            # Use standard Odoo payment term computation for non-progressive terms
            return super()._compute_terms(
                date_ref, currency, company, tax_amount, tax_amount_currency, 
                sign, untaxed_amount, untaxed_amount_currency, cash_rounding
            )
        
        # Use progressive payment computation for milestone-based terms
        return self._compute_progressive_terms(
            date_ref, currency, company, tax_amount, tax_amount_currency, 
            sign, untaxed_amount, untaxed_amount_currency, cash_rounding
        )
    
    def _compute_progressive_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency, cash_rounding=None):
        """Compute progressive payment terms based on milestones"""
        self.ensure_one()
        company_currency = company.currency_id
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
        
        # Initialize payment term structure (compatible with Odoo standard)
        pay_term = {
            'total_amount': total_amount,
            'discount_percentage': 0.0,  # Progressive payments don't support early discount
            'discount_date': False,
            'discount_balance': 0,
            'line_ids': [],
        }
        
        # Get milestone lines from payment term
        milestone_lines = self.line_ids.filtered('is_milestone')
        if not milestone_lines:
            # Fallback to standard computation if no milestones defined
            return super()._compute_terms(
                date_ref, currency, company, tax_amount, tax_amount_currency, 
                sign, untaxed_amount, untaxed_amount_currency, cash_rounding
            )
        
        # Sort milestone lines by sequence and days
        milestone_lines = milestone_lines.sorted(lambda l: (l.sequence or 0, l.nb_days or 0))
        
        # Track residual amounts for balance calculation
        residual_amount = total_amount
        residual_amount_currency = total_amount_currency
        
        # Process each milestone
        for i, line in enumerate(milestone_lines):
            term_vals = {
                'date': line._get_due_date(date_ref),
                'company_amount': 0,
                'foreign_amount': 0,
                # Add milestone-specific information for tracking
                'milestone_id': line.id,
                'milestone_type': line.milestone_type,
                'milestone_name': line.milestone_display_name or line.milestone_type,
                'is_milestone': True,
            }
            
            # The last milestone is always the balance to handle rounding
            on_balance_line = i == len(milestone_lines) - 1
            
            if on_balance_line:
                # Last milestone gets remaining balance
                term_vals['company_amount'] = residual_amount
                term_vals['foreign_amount'] = residual_amount_currency
            elif line.value == 'fixed':
                # Fixed amount milestones
                term_vals['company_amount'] = sign * company_currency.round(line.value_amount / rate) if rate else 0.0
                term_vals['foreign_amount'] = sign * currency.round(line.value_amount)
            else:
                # Percentage-based milestones (most common for progressive payments)
                line_amount = company_currency.round(total_amount * (line.value_amount / 100.0))
                line_amount_currency = currency.round(total_amount_currency * (line.value_amount / 100.0))
                term_vals['company_amount'] = line_amount
                term_vals['foreign_amount'] = line_amount_currency
            
            # Handle cash rounding for non-balance lines
            if cash_rounding and not on_balance_line:
                cash_rounding_difference_currency = cash_rounding.compute_difference(
                    currency, term_vals['foreign_amount']
                )
                if not currency.is_zero(cash_rounding_difference_currency):
                    term_vals['foreign_amount'] += cash_rounding_difference_currency
                    term_vals['company_amount'] = company_currency.round(
                        term_vals['foreign_amount'] / rate
                    ) if rate else 0.0
            
            # Update residual amounts
            residual_amount -= term_vals['company_amount']
            residual_amount_currency -= term_vals['foreign_amount']
            
            # Add milestone information for sub-milestones if applicable
            if line.allow_sub_milestones and line.sub_milestone_template_ids:
                term_vals['has_sub_milestones'] = True
                term_vals['sub_milestone_count'] = len(line.sub_milestone_template_ids)
                term_vals['sub_milestones'] = self._get_sub_milestone_info(line)
            
            pay_term['line_ids'].append(term_vals)
        
        return pay_term
    
    def _get_sub_milestone_info(self, milestone_line):
        """Get sub-milestone information for tracking purposes"""
        sub_milestones = []
        for sub_template in milestone_line.sub_milestone_template_ids.sorted('sequence'):
            sub_milestones.append({
                'id': sub_template.id,
                'name': sub_template.name,
                'percentage': sub_template.percentage,
                'sequence': sub_template.sequence,
            })
        return sub_milestones
    
    def _get_progressive_milestones_context(self):
        """Get progressive milestones from context (for sale order integration)"""
        # This method will be used when milestones are customized at sale order level
        # For now, return empty list - will be enhanced in future tasks
        context_milestones = self.env.context.get('progressive_milestones', [])
        return context_milestones

    # -------------------------------------------------------------------------
    # VALIDATION METHODS
    # -------------------------------------------------------------------------
    
    def validate_progressive_configuration(self):
        """Validate progressive payment configuration after data loading"""
        for term in self:
            if term.is_progressive:
                milestone_lines = term.line_ids.filtered('is_milestone')
                
                # Check if there are milestone lines
                if not milestone_lines:
                    raise ValidationError(_(
                        'Progressive payment term "%s" must have at least one milestone line.'
                    ) % term.name)
                
                # Check percentage total for percent-based milestones
                percent_lines = milestone_lines.filtered(lambda l: l.value == 'percent')
                if percent_lines:
                    total_percentage = sum(line.value_amount for line in percent_lines)
                    if abs(total_percentage - 100.0) > 0.01:  # Allow small rounding differences
                        raise ValidationError(_(
                            'Progressive payment term "%s": Total milestone percentages must equal 100%%. '
                            'Current total: %.2f%%'
                        ) % (term.name, total_percentage))
    
    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    @api.model
    def create_from_template(self, template_id, name=None):
        """Create a new payment term from a template"""
        template = self.browse(template_id)
        if not template.is_template:
            raise ValidationError(_('Selected payment term is not a template'))
        
        values = {
            'name': name or _('%s (Instance)') % template.name,
            'is_template': False,
            'is_progressive': template.is_progressive,
            'construction_category': template.construction_category,
            'template_description': template.template_description,
        }
        
        return template.copy(values)

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    
    def action_view_milestones(self):
        """Open milestone configuration view"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Milestones'),
            'res_model': 'account.payment.term.line',
            'view_mode': 'list,form',
            'domain': [('payment_id', '=', self.id), ('is_milestone', '=', True)],
            'context': {
                'default_payment_id': self.id,
                'default_is_milestone': True,
            }
        }