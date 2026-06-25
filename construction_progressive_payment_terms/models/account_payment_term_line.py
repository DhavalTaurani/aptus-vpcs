# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    
    # Progressive milestone fields
    is_milestone = fields.Boolean(
        string='Is Milestone',
        default=False,
        help='Mark this line as a progressive payment milestone'
    )
    milestone_type = fields.Selection([
        ('advance', 'Advance Payment'),
        ('material_delivery', 'Material Delivery'),
        ('installation', 'Installation Completion'),
        ('testing_commissioning', 'Testing & Commissioning'),
        ('retention', 'Retention'),
        ('custom', 'Custom Milestone')
    ], string='Milestone Type',
        help='Type of milestone for progressive payments')
    
    # Milestone configuration
    milestone_description = fields.Html(
        string='Milestone Description',
        help='Detailed description of milestone requirements'
    )
    required_documents = fields.Text(
        string='Required Documents',
        help='Documents required for milestone completion'
    )
    approval_required = fields.Boolean(
        string='Approval Required',
        default=False,
        help='Milestone requires approval before payment'
    )
    
    # Trigger conditions for milestone completion
    trigger_condition = fields.Selection([
        ('manual', 'Manual Trigger'),
        ('date_based', 'Date Based'),
        ('delivery_based', 'Delivery Based'),
        ('progress_based', 'Progress Based'),
        ('approval_based', 'Approval Based')
    ], string='Trigger Condition', 
        default='manual',
        help='Condition that triggers milestone completion')
    
    # Sub-milestone support (handled at sale order level)
    allow_sub_milestones = fields.Boolean(
        string='Allow Sub-milestones',
        default=False,
        help='Enable splitting this milestone into sub-milestones'
    )
    
    # Sub-milestone templates
    sub_milestone_template_ids = fields.One2many(
        'account.payment.term.line.sub.template',
        'payment_term_line_id',
        string='Sub-milestone Templates'
    )
    
    sub_milestone_template_count = fields.Integer(
        string='Template Count',
        compute='_compute_sub_milestone_template_count'
    )
    
    # Display fields
    milestone_display_name = fields.Char(
        string='Milestone Name',
        compute='_compute_milestone_display_name',
        help='Display name for the milestone'
    )
    
    # Sequence field for ordering milestones
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for ordering payment term lines'
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    
    @api.depends('milestone_type', 'value_amount')
    def _compute_milestone_display_name(self):
        """Compute display name for milestone"""
        for line in self:
            if line.is_milestone and line.milestone_type:
                type_name = dict(line._fields['milestone_type'].selection).get(
                    line.milestone_type, line.milestone_type
                )
                if line.value == 'percent':
                    line.milestone_display_name = f"{type_name} ({line.value_amount}%)"
                else:
                    line.milestone_display_name = type_name
            else:
                line.milestone_display_name = ''
    
    @api.depends('sub_milestone_template_ids')
    def _compute_sub_milestone_template_count(self):
        """Compute number of sub-milestone templates"""
        for line in self:
            line.sub_milestone_template_count = len(line.sub_milestone_template_ids)



    # -------------------------------------------------------------------------
    # CONSTRAINS METHODS
    # -------------------------------------------------------------------------
    
    # @api.constrains('is_milestone', 'milestone_type')
    # def _check_milestone_configuration(self):
    #     """Validate milestone configuration"""
    #     for line in self:
    #         if line.is_milestone:
    #             # Milestone must have a type
    #             if not line.milestone_type:
    #                 raise ValidationError(_(
    #                     'Milestone lines must have a milestone type defined.'
    #                 ))
                
    #             # Check for duplicate milestone types within same payment term
    #             if line.payment_id:
    #                 duplicate_milestones = line.payment_id.line_ids.filtered(
    #                     lambda l: l.is_milestone and 
    #                             l.milestone_type == line.milestone_type and 
    #                             l.id != line.id
    #                 )
    #                 if duplicate_milestones:
    #                     raise ValidationError(_(
    #                         'Duplicate milestone type "%s" found in payment term. '
    #                         'Each milestone type can only be used once per payment term.'
    #                     ) % dict(line._fields['milestone_type'].selection)[line.milestone_type])

    @api.constrains('value_amount', 'is_milestone')
    def _check_milestone_percentage(self):
        """Ensure milestone percentages are valid"""
        for line in self:
            if line.is_milestone and line.value == 'percent':
                if line.value_amount < 0 or line.value_amount > 100:
                    raise ValidationError(_(
                        'Milestone percentage must be between 0 and 100. '
                        'Current value: %.2f%%'
                    ) % line.value_amount)



    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------
    
    @api.onchange('is_milestone')
    def _onchange_is_milestone(self):
        """Handle changes to milestone flag"""
        if self.is_milestone:
            # Set default values for milestone
            if not self.milestone_type:
                self.milestone_type = 'custom'
            if not self.value:
                self.value = 'percent'
            if not self.value_amount:
                self.value_amount = 10.0
        else:
            # Clear milestone-specific fields
            self.milestone_type = False
            self.milestone_description = False
            self.required_documents = False
            self.approval_required = False
            self.trigger_condition = 'manual'
            self.allow_sub_milestones = False



    @api.onchange('milestone_type')
    def _onchange_milestone_type(self):
        """Set default values based on milestone type"""
        if self.milestone_type:
            milestone_defaults = {
                'advance': {
                    'value_amount': 20.0,
                    'nb_days': 0,
                    'milestone_description': '<p>Advance payment upon contract signing</p>',
                    'trigger_condition': 'manual',
                },
                'material_delivery': {
                    'value_amount': 30.0,
                    'nb_days': 30,
                    'milestone_description': '<p>Payment upon material delivery to site</p>',
                    'trigger_condition': 'delivery_based',
                    'allow_sub_milestones': True,
                },
                'installation': {
                    'value_amount': 35.0,
                    'nb_days': 60,
                    'milestone_description': '<p>Payment upon installation completion</p>',
                    'trigger_condition': 'progress_based',
                },
                'testing_commissioning': {
                    'value_amount': 10.0,
                    'nb_days': 90,
                    'milestone_description': '<p>Payment upon testing and commissioning completion</p>',
                    'trigger_condition': 'approval_based',
                    'approval_required': True,
                },
                'retention': {
                    'value_amount': 5.0,
                    'nb_days': 365,
                    'milestone_description': '<p>Retention release after warranty period</p>',
                    'trigger_condition': 'date_based',
                },
            }
            
            defaults = milestone_defaults.get(self.milestone_type, {})
            for field, value in defaults.items():
                if not getattr(self, field):
                    setattr(self, field, value)

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------
    
    def name_get(self):
        """Override name_get to show milestone information"""
        result = []
        for line in self:
            if line.is_milestone and line.milestone_display_name:
                name = line.milestone_display_name
            else:
                # Use standard name_get for non-milestone lines
                name = super(AccountPaymentTermLine, line).name_get()[0][1]
            result.append((line.id, name))
        return result

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------
    
    def _get_due_date(self, date_ref):
        """Calculate due date for milestone based on reference date and days offset"""
        from dateutil.relativedelta import relativedelta
        if not date_ref:
            return False
        return date_ref + relativedelta(days=self.nb_days)
    
