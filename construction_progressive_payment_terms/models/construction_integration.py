# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ConstructionProjectTemplate(models.Model):
    """Extend construction project template with progressive payment integration"""
    
    _inherit = 'construction.project.template'
    
    def _apply_dynamic_milestones(self, project):
        """Override to create milestones from progressive payment terms"""
        self.ensure_one()

        try:
            # Check if project has sale order with progressive payment terms
            sale_order = (
                project.sale_order_id or project.sale_line_id.order_id
                if project.sale_line_id
                else False
            )

            # Check if sale order has progressive payments
            has_progressive_payment = False
            if sale_order:
                has_progressive_payment = (
                    hasattr(sale_order, 'has_progressive_payment') and 
                    sale_order.has_progressive_payment and
                    hasattr(sale_order, 'payment_milestone_ids') and
                    sale_order.payment_milestone_ids
                )

            if has_progressive_payment:
                # Use progressive payment milestones as project milestones
                milestone_count = 0
                for payment_milestone in sale_order.payment_milestone_ids:
                    try:
                        milestone_vals = {
                            "name": f"🎯 {payment_milestone.milestone_name}",
                            "description": payment_milestone.description or f"Payment milestone: {getattr(payment_milestone, 'percentage', 0)}%",
                            "project_id": project.id,
                            "sequence": getattr(payment_milestone, 'sequence', 900) + 900,  # Put milestones at the end
                            "date_deadline": getattr(payment_milestone, 'planned_date', False),
                            # Link to payment milestone for tracking
                            "payment_milestone_id": payment_milestone.id,
                            # Mark as milestone task (not BOQ item)
                            "is_boq_item": False,
                        }

                        milestone_task = self.env["project.task"].create(milestone_vals)
                        milestone_count += 1

                        _logger.debug(
                            "Created dynamic milestone '%s' from payment terms in project '%s'",
                            payment_milestone.milestone_name,
                            project.name,
                        )
                    except Exception as e:
                        _logger.warning(
                            "Failed to create milestone from payment milestone %s: %s",
                            payment_milestone.id,
                            str(e)
                        )
                        continue
                
                _logger.info(
                    "Created %d dynamic milestones from progressive payment terms for project '%s'",
                    milestone_count,
                    project.name,
                )
                return True  # Indicate that dynamic milestones were created
            else:
                # Call parent method to use template milestones
                return super()._apply_dynamic_milestones(project)

        except Exception as e:
            _logger.error(
                "Error applying dynamic milestones to project '%s': %s. Falling back to parent method.",
                project.name,
                str(e)
            )
            # Fallback to parent method on any error
            return super()._apply_dynamic_milestones(project)


class ProjectTask(models.Model):
    """Extend project.task to integrate with progressive payment milestones"""
    
    _inherit = 'project.task'
    
    # Link to payment milestone for tracking
    payment_milestone_id = fields.Many2one(
        'sale.order.payment.milestone',
        string='Payment Milestone',
        help='Link to payment milestone from progressive payment terms'
    )
    
    # Milestone progress tracking
    milestone_progress = fields.Float(
        string='Milestone Progress (%)',
        compute='_compute_milestone_progress',
        help='Progress of linked payment milestone'
    )
    
    milestone_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('ready', 'Ready for Invoicing'),
            ('invoiced', 'Invoiced'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        string='Milestone State',
        compute='_compute_milestone_fields',
        help='State of linked payment milestone'
    )

    milestone_amount = fields.Monetary(
        string='Milestone Amount',
        compute='_compute_milestone_fields',
        help='Amount of linked payment milestone'
    )

    milestone_percentage = fields.Float(
        string='Milestone Percentage',
        compute='_compute_milestone_fields',
        help='Percentage of linked payment milestone'
    )

    @api.depends('payment_milestone_id', 'payment_milestone_id.state', 'payment_milestone_id.amount', 'payment_milestone_id.percentage')
    def _compute_milestone_fields(self):
        for task in self:
            if task.payment_milestone_id:
                # Safely access milestone fields with fallbacks
                task.milestone_state = getattr(task.payment_milestone_id, 'state', False)
                task.milestone_amount = getattr(task.payment_milestone_id, 'amount', 0.0)
                task.milestone_percentage = getattr(task.payment_milestone_id, 'percentage', 0.0)
            else:
                task.milestone_state = False
                task.milestone_amount = 0.0
                task.milestone_percentage = 0.0

    @api.depends('payment_milestone_id.progress_percentage')
    def _compute_milestone_progress(self):
        """Compute milestone progress from linked payment milestone"""
        for task in self:
            try:
                if task.payment_milestone_id:
                    # Use progress_percentage if available, otherwise calculate from state
                    if hasattr(task.payment_milestone_id, 'progress_percentage'):
                        task.milestone_progress = getattr(task.payment_milestone_id, 'progress_percentage', 0.0)
                    else:
                        # Fallback calculation based on state
                        state_progress = {
                            'draft': 0.0,
                            'ready': 25.0,
                            'invoiced': 75.0,
                            'paid': 100.0,
                            'cancelled': 0.0,
                        }
                        milestone_state = getattr(task.payment_milestone_id, 'state', 'draft')
                        task.milestone_progress = state_progress.get(milestone_state, 0.0)
                else:
                    task.milestone_progress = 0.0
            except Exception as e:
                _logger.warning(f"Error computing milestone progress for task {task.id}: {e}")
                task.milestone_progress = 0.0
    
    def action_view_payment_milestone(self):
        """Open linked payment milestone"""
        self.ensure_one()
        if not self.payment_milestone_id:
            raise ValidationError(_('No payment milestone linked to this task'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Milestone'),
            'res_model': 'sale.order.payment.milestone',
            'res_id': self.payment_milestone_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_update_milestone_progress(self):
        """Update milestone progress based on task completion"""
        self.ensure_one()
        if not self.payment_milestone_id:
            return
        
        # Update milestone progress based on task progress
        if hasattr(self.payment_milestone_id, 'task_progress'):
            self.payment_milestone_id.task_progress = self.progress
        
        # Auto-advance milestone state based on task completion
        if self.stage_id.name in ['Done', 'Completed'] and self.payment_milestone_id.state == 'draft':
            self.payment_milestone_id.state = 'ready'
            _logger.info(
                "Advanced milestone '%s' to 'ready' state based on task completion",
                self.payment_milestone_id.milestone_name
            )


class SaleOrderPaymentMilestone(models.Model):
    """Extend payment milestone to link with project tasks"""
    
    _inherit = 'sale.order.payment.milestone'
    
    # Link to project tasks
    project_task_ids = fields.One2many(
        'project.task',
        'payment_milestone_id',
        string='Project Tasks',
        help='Project tasks linked to this payment milestone'
    )
    
    task_count = fields.Integer(
        string='Task Count',
        compute='_compute_task_count',
        help='Number of linked project tasks'
    )
    
    task_progress = fields.Float(
        string='Task Progress (%)',
        help='Progress of linked project tasks'
    )
    
    # Enhanced progress calculation including task progress
    combined_progress = fields.Float(
        string='Combined Progress (%)',
        compute='_compute_combined_progress',
        help='Combined progress from payment and task completion'
    )
    
    @api.depends('project_task_ids')
    def _compute_task_count(self):
        """Compute number of linked tasks"""
        for milestone in self:
            milestone.task_count = len(milestone.project_task_ids)
    
    @api.depends('progress_percentage', 'task_progress', 'project_task_ids.progress')
    def _compute_combined_progress(self):
        """Compute combined progress from payment and task completion"""
        for milestone in self:
            if milestone.project_task_ids:
                # Calculate average task progress
                task_progress = sum(milestone.project_task_ids.mapped('progress')) / len(milestone.project_task_ids)
                # Weight: 70% task progress, 30% payment progress
                payment_progress = getattr(milestone, 'progress_percentage', 0.0)
                milestone.combined_progress = (task_progress * 0.7) + (payment_progress * 0.3)
            else:
                # Use payment progress only if no tasks linked
                milestone.combined_progress = getattr(milestone, 'progress_percentage', 0.0)
    
    def action_view_project_tasks(self):
        """Open linked project tasks"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Project Tasks'),
            'res_model': 'project.task',
            'view_mode': 'list,form',
            'domain': [('payment_milestone_id', '=', self.id)],
            'context': {
                'default_payment_milestone_id': self.id,
            }
        }
    
    def action_sync_task_progress(self):
        """Synchronize milestone state with task progress"""
        self.ensure_one()
        if not self.project_task_ids:
            return
        
        # Calculate completion percentage
        completed_tasks = self.project_task_ids.filtered(lambda t: t.stage_id.name in ['Done', 'Completed'])
        completion_rate = len(completed_tasks) / len(self.project_task_ids) * 100
        
        # Auto-advance milestone state based on task completion
        if completion_rate >= 100 and self.state == 'draft':
            self.state = 'ready'
            _logger.info(
                "Advanced milestone '%s' to 'ready' state - all tasks completed",
                self.milestone_name
            )
        elif completion_rate >= 50 and self.state == 'draft':
            # Could add intermediate states here if needed
            pass
        
        # Update task progress field
        self.task_progress = completion_rate
    
    @api.model
    def create_project_milestones(self, sale_order):
        """Create project milestones from payment milestones when project is created"""
        if not sale_order.has_progressive_payment:
            return
        
        # Find related projects
        projects = self.env['project.project'].search([
            '|',
            ('sale_order_id', '=', sale_order.id),
            ('sale_line_id.order_id', '=', sale_order.id)
        ])
        
        for project in projects:
            if hasattr(project, 'construction_template_id') and project.construction_template_id:
                # Let the construction template handle milestone creation
                project.construction_template_id._apply_dynamic_milestones(project)
                _logger.info(
                    "Triggered dynamic milestone creation for construction project '%s'",
                    project.name
                )


class SaleOrder(models.Model):
    """Extend sale order to trigger project milestone creation"""
    
    _inherit = 'sale.order'
    
    def action_confirm(self):
        """Override to create project milestones after order confirmation"""
        result = super().action_confirm()
        
        # Create project milestones for construction projects with progressive payments
        if self.has_progressive_payment:
            self.env['sale.order.payment.milestone'].create_project_milestones(self)
        
        return result


class ProjectProject(models.Model):
    """Extend project to add payment milestone integration"""
    
    _inherit = 'project.project'
    
    payment_milestone_count = fields.Integer(
        string='Payment Milestone Count',
        compute='_compute_payment_milestone_count',
        help='Number of payment milestones linked to this project'
    )
    
    @api.depends('task_ids.payment_milestone_id')
    def _compute_payment_milestone_count(self):
        """Compute number of payment milestones linked to project tasks"""
        for project in self:
            milestone_ids = project.task_ids.mapped('payment_milestone_id').ids
            project.payment_milestone_count = len(set(milestone_ids)) if milestone_ids else 0
    
    def action_view_payment_milestones(self):
        """Open payment milestones linked to this project"""
        self.ensure_one()
        milestone_ids = self.task_ids.mapped('payment_milestone_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment Milestones'),
            'res_model': 'sale.order.payment.milestone',
            'view_mode': 'list,form',
            'domain': [('id', 'in', milestone_ids)],
            'context': {
                'default_project_id': self.id,
            }
        }