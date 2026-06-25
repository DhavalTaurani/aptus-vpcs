# Implementation Guide - Progressive Payment Terms

## Overview

This guide provides comprehensive implementation details for the Construction Progressive Payment Terms module. The system provides complete milestone-based payment management with advanced features including sub-milestones, automated invoicing, and comprehensive reset functionality.

## ✅ Implemented Architecture

### Core Models

#### 1. Sale Order Payment Milestone (`sale.order.payment.milestone`)
**Purpose**: Main milestone tracking with complete state workflow

**Key Fields**:
```python
# Core identification
milestone_name = fields.Char(required=True)
milestone_type = fields.Selection(related='payment_term_line_id.milestone_type')
sequence = fields.Integer(default=10)

# Financial tracking  
percentage = fields.Float(digits=(5, 2))
amount = fields.Monetary(currency_field='currency_id')
currency_id = fields.Many2one(related='sale_order_id.currency_id')

# State management
state = fields.Selection([
    ('draft', 'Draft'),
    ('ready', 'Ready'), 
    ('invoiced', 'Invoiced'),
    ('paid', 'Paid'),
    ('cancelled', 'Cancelled')
], default='draft')

# Progress tracking
progress_percentage = fields.Float(compute='_compute_progress_percentage', store=True)
planned_date = fields.Date()
actual_date = fields.Date()

# Sub-milestone support
allow_sub_milestones = fields.Boolean(default=False)
sub_milestone_ids = fields.One2many('sale.order.payment.milestone.sub', 'parent_milestone_id')

# Invoice integration
invoice_id = fields.Many2one('account.move')
invoice_line_ids = fields.One2many('account.move.line', 'milestone_id')
```

**Key Methods**:
```python
def action_set_ready(self):
    """Mark milestone as ready with sub-milestone validation"""
    
def action_invoice(self):
    """Create invoice using account.move.create_milestone_invoice()"""
    
def action_reset_to_draft(self):
    """Complete reset with payment cleanup and sale line restoration"""
    
@api.depends('sub_milestone_ids.state', 'state')
def _compute_progress_percentage(self):
    """Smart progress calculation based on sub-milestones or state"""
    
def _restore_original_sale_lines(self):
    """Restore original sale order line amounts after reset"""
```

#### 2. Sale Order Payment Sub-milestone (`sale.order.payment.milestone.sub`)
**Purpose**: Independent sub-milestone workflow with parent updates

**Key Fields**:
```python
parent_milestone_id = fields.Many2one('sale.order.payment.milestone', required=True)
name = fields.Char(required=True)
percentage = fields.Float(digits=(5, 2))
amount = fields.Monetary(compute='_compute_amount', store=True)

state = fields.Selection([
    ('draft', 'Draft'),
    ('ready', 'Ready'),
    ('completed', 'Completed'),
    ('invoiced', 'Invoiced'),
    ('cancelled', 'Cancelled')
], default='draft')
```

**Key Methods**:
```python
def action_complete(self):
    """Mark completed and check parent status"""
    
def action_create_invoice(self):
    """Create individual sub-milestone invoice"""
    
def _check_parent_milestone_status(self):
    """Update parent milestone based on sub-milestone states"""
```

#### 3. Extended Account Move (`account.move`)
**Purpose**: Milestone invoice creation with dedicated sale order lines

**Key Methods**:
```python
@api.model
def create_milestone_invoice(self, milestone_ids, invoice_vals=None):
    """
    Create milestone invoice with:
    - Dedicated sale order lines (sequence >= 9999)
    - Proportional deduction from original lines
    - Immediate payment terms
    - Proper milestone linking
    """
    
def _create_milestone_sale_line(self, sale_order, milestone, sub_milestone=None):
    """Create dedicated sale order line for milestone tracking"""
    
def _update_original_sale_lines(self, sale_order, milestones):
    """Proportionally reduce original sale order line amounts"""
```

#### 4. Sub-milestone Template (`account.payment.term.sub.template`)
**Purpose**: Standardized sub-milestone templates for common milestone breakdowns

**Key Fields**:
```python
name = fields.Char(required=True)  # Template name
sequence = fields.Integer(default=10)  # Display order
percentage = fields.Float(digits=(5, 2))  # Percentage of parent milestone
description = fields.Text()  # Template description
```

**Key Methods**:
```python
def create_sub_milestones_from_template(self, parent_milestone):
    """Create sub-milestones from template for given parent milestone"""
```

#### 5. Extended Sale Order (`sale.order`)
**Purpose**: Milestone tracking and progress calculation

**Key Computed Fields**:
```python
@api.depends('payment_milestone_ids.amount', 'payment_milestone_ids.state', 
             'payment_milestone_ids.sub_milestone_ids.amount',
             'payment_milestone_ids.sub_milestone_ids.state',
             'payment_milestone_ids.invoice_id.payment_state',
             'payment_milestone_ids.invoice_id.amount_residual')
def _compute_milestone_amounts(self):
    """Calculate total, invoiced, and paid milestone amounts"""
    
@api.depends('payment_milestone_ids.progress_percentage',
             'payment_milestone_ids.sub_milestone_ids.state')  
def _compute_milestone_progress(self):
    """Calculate overall milestone progress percentage"""
```

## Implementation Workflows

### 1. Milestone Generation Workflow

```python
def action_confirm(self):
    """Override to generate milestones on order confirmation"""
    result = super().action_confirm()
    
    for order in self:
        if order.has_progressive_payment and not order.payment_milestone_ids:
            order._generate_payment_milestones()
    
    return result

def _generate_payment_milestones(self):
    """Generate milestones from progressive payment terms"""
    if not self.payment_term_id or not self.payment_term_id.is_progressive:
        return
    
    milestone_lines = self.payment_term_id.line_ids.filtered('is_milestone')
    milestone_vals = []
    
    for line in milestone_lines.sorted(lambda l: (l.sequence, l.nb_days, l.id)):
        # Calculate planned date
        planned_date = self.date_order.date() + relativedelta(days=line.nb_days)
        
        # Calculate amount
        amount = self.amount_total * (line.value_amount / 100.0)
        
        milestone_vals.append((0, 0, {
            'payment_term_line_id': line.id,
            'milestone_name': line.milestone_display_name,
            'percentage': line.value_amount,
            'amount': amount,
            'planned_date': planned_date,
            'sequence': line.sequence,
            'state': 'draft',
            'allow_sub_milestones': line.allow_sub_milestones,
        }))
    
    self.payment_milestone_ids = milestone_vals
    
    # Generate sub-milestones from templates
    self._generate_sub_milestones()

def _generate_sub_milestones(self):
    """Generate sub-milestones from templates for milestones that allow them"""
    for milestone in self.payment_milestone_ids.filtered('allow_sub_milestones'):
        if milestone.payment_term_line_id.sub_milestone_template_ids:
            for template in milestone.payment_term_line_id.sub_milestone_template_ids:
                self.env['sale.order.payment.milestone.sub'].create({
                    'parent_milestone_id': milestone.id,
                    'sub_milestone_template_id': template.id,
                    'name': template.name,
                    'sequence': template.sequence,
                    'percentage': template.percentage,
                    'description': template.description,
                })
```

### 2. Invoice Creation Workflow

```python
@api.model
def create_milestone_invoice(self, milestone_ids, invoice_vals=None):
    """Complete milestone invoice creation process"""
    milestones = self.env['sale.order.payment.milestone'].browse(milestone_ids)
    
    # Validation
    for milestone in milestones:
        if milestone.state != 'ready':
            raise ValidationError(_('Only ready milestones can be invoiced'))
    
    sale_order = milestones[0].sale_order_id
    
    # Create invoice with immediate payment terms
    immediate_payment_term = self._get_immediate_payment_term()
    
    invoice_vals = {
        'move_type': 'out_invoice',
        'partner_id': sale_order.partner_id.id,
        'currency_id': sale_order.currency_id.id,
        'invoice_payment_term_id': immediate_payment_term.id,
        'invoice_origin': sale_order.name,
        'is_milestone_invoice': True,
        'source_sale_order_id': sale_order.id,
    }
    
    invoice = self.create(invoice_vals)
    
    # Create invoice lines with dedicated sale order lines
    for milestone in milestones:
        if milestone.sub_milestone_ids:
            # Handle sub-milestones
            completed_subs = milestone.sub_milestone_ids.filtered(
                lambda s: s.state == 'completed'
            )
            for sub_milestone in completed_subs:
                sale_line = self._create_milestone_sale_line(
                    sale_order, milestone, sub_milestone
                )
                self._create_invoice_line(invoice, milestone, sub_milestone, sale_line)
        else:
            # Handle regular milestone
            sale_line = self._create_milestone_sale_line(sale_order, milestone)
            self._create_invoice_line(invoice, milestone, None, sale_line)
    
    # Update original sale order lines
    self._update_original_sale_lines(sale_order, milestones)
    
    # Link milestones to invoice
    milestones.write({'invoice_id': invoice.id})
    
    return invoice
```

### 3. Reset Workflow with Complete Cleanup

```python
def action_reset_to_draft(self):
    """Complete milestone reset with payment cleanup - FIXED VERSION"""
    self.ensure_one()
    
    if self.invoice_id:
        # Restore sale order lines first
        self._restore_original_sale_lines()
        
        # Handle different invoice states
        if self.invoice_id.state == 'draft':
            self.invoice_id.unlink()
        elif self.invoice_id.state == 'posted':
            # Handle payments if invoice is paid
            if self.invoice_id.payment_state in ('paid', 'in_payment', 'partial'):
                self._remove_invoice_payments(self.invoice_id)
            
            # Cancel and reset invoice
            self.invoice_id.button_cancel()
            self.invoice_id.button_draft()
    
    # Reset sub-milestones first
    for sub_milestone in self.sub_milestone_ids:
        if sub_milestone.state != 'draft':
            sub_milestone.action_reset_to_draft()
    
    # Reset milestone state - FIXED: State reset moved to main method
    self.write({
        'state': 'draft',
        'actual_date': False,
        'approved_by': False,
        'approved_date': False
    })
    
    return True

def _remove_invoice_payments(self, invoice):
    """Remove payments and reconciliation for paid invoices"""
    # Find payment moves
    payment_moves = self.env['account.move'].search([
        ('line_ids.matched_debit_ids.debit_move_id', 'in', invoice.line_ids.ids),
        ('move_type', 'in', ['entry', 'in_receipt', 'out_receipt']),
        ('state', '=', 'posted')
    ])
    
    payment_moves |= self.env['account.move'].search([
        ('line_ids.matched_credit_ids.credit_move_id', 'in', invoice.line_ids.ids),
        ('move_type', 'in', ['entry', 'in_receipt', 'out_receipt']),
        ('state', '=', 'posted')
    ])
    
    # Remove reconciliation
    for line in invoice.line_ids.filtered(lambda l: l.account_id.reconcile):
        if line.matched_debit_ids or line.matched_credit_ids:
            line.remove_move_reconcile()
    
    # Cancel and unlink payment moves
    for payment_move in payment_moves:
        if payment_move.state == 'posted':
            payment_move.button_cancel()
        payment_move.unlink()
```

### 4. Sale Order Line Management

```python
def _create_milestone_sale_line(self, sale_order, milestone, sub_milestone=None):
    """Create dedicated sale order line for milestone tracking"""
    original_line = sale_order.order_line[0] if sale_order.order_line else None
    
    if sub_milestone:
        line_name = f"{milestone.milestone_name} - {sub_milestone.name}"
        amount = sub_milestone.amount
    else:
        line_name = milestone.milestone_name
        amount = milestone.amount
    
    sale_line_vals = {
        'order_id': sale_order.id,
        'name': line_name,
        'product_uom_qty': 1.0,
        'price_unit': amount,
        'sequence': 9999,  # Put milestone lines at the end
    }
    
    # Copy product info from original line
    if original_line:
        sale_line_vals.update({
            'product_id': original_line.product_id.id if original_line.product_id else False,
            'product_uom': original_line.product_uom.id if original_line.product_uom else False,
            'tax_id': [(6, 0, original_line.tax_id.ids)],
        })
    
    return self.env['sale.order.line'].create(sale_line_vals)

def _update_original_sale_lines(self, sale_order, milestones):
    """Proportionally reduce original sale order line amounts"""
    if not sale_order.order_line:
        return
    
    # Calculate current milestone invoice amount
    current_invoice_amount = 0.0
    for milestone in milestones:
        if milestone.sub_milestone_ids:
            completed_subs = milestone.sub_milestone_ids.filtered(
                lambda s: s.state == 'completed'
            )
            current_invoice_amount += sum(completed_subs.mapped('amount'))
        else:
            current_invoice_amount += milestone.amount
    
    # Get original lines (sequence < 9999)
    original_lines = sale_order.order_line.filtered(lambda l: l.sequence < 9999)
    total_original = sum(original_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
    
    # Deduct proportionally from original lines
    for line in original_lines:
        line_total = line.price_unit * line.product_uom_qty
        line_proportion = line_total / total_original if total_original else 0
        deduction = current_invoice_amount * line_proportion
        
        new_line_total = line_total - deduction
        if new_line_total > 0:
            new_price_unit = new_line_total / line.product_uom_qty if line.product_uom_qty else 0
            line.write({'price_unit': new_price_unit})
        else:
            line.write({'price_unit': 0.01})  # Minimal amount to keep line visible

def _restore_original_sale_lines(self):
    """Restore original sale order line amounts when resetting"""
    if not self.invoice_id or not self.sale_order_id:
        return
    
    # Find milestone-specific sale order lines
    milestone_lines = self.sale_order_id.order_line.filtered(
        lambda l: l.sequence >= 9999 and (
            self.milestone_name in l.name or 
            any(sub.name in l.name for sub in self.sub_milestone_ids)
        )
    )
    
    # Calculate total amount to restore
    restore_amount = sum(milestone_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
    
    # Set milestone lines quantity to zero (can't unlink in confirmed orders)
    milestone_lines.write({'product_uom_qty': 0})
    
    # Restore original lines proportionally
    if restore_amount > 0:
        original_lines = self.sale_order_id.order_line.filtered(lambda l: l.sequence < 9999)
        if original_lines:
            current_total = sum(original_lines.mapped(lambda l: l.price_unit * l.product_uom_qty))
            
            for line in original_lines:
                current_line_total = line.price_unit * line.product_uom_qty
                if current_total > 0:
                    line_proportion = current_line_total / current_total
                    additional_amount = restore_amount * line_proportion
                    new_line_total = current_line_total + additional_amount
                    new_price_unit = new_line_total / line.product_uom_qty if line.product_uom_qty else 0
                    line.write({'price_unit': new_price_unit})
```

## Progress Calculation Implementation

### Smart Progress Calculation
```python
@api.depends('sub_milestone_ids.state', 'state')
def _compute_progress_percentage(self):
    """Compute progress based on sub-milestones or milestone state"""
    for milestone in self:
        if milestone.sub_milestone_ids:
            # Calculate based on sub-milestone states
            total_subs = len(milestone.sub_milestone_ids)
            if total_subs > 0:
                completed_subs = len(milestone.sub_milestone_ids.filtered(
                    lambda s: s.state in ('completed', 'invoiced')
                ))
                milestone.progress_percentage = (completed_subs / total_subs) * 100.0
            else:
                milestone.progress_percentage = 0.0
        else:
            # For milestones without sub-milestones, base on state
            if milestone.state == 'draft':
                milestone.progress_percentage = 0.0
            elif milestone.state == 'ready':
                milestone.progress_percentage = 50.0
            elif milestone.state in ('invoiced', 'paid'):
                milestone.progress_percentage = 100.0
            else:
                milestone.progress_percentage = 0.0
```

### Payment Amount Tracking
```python
@api.depends('payment_milestone_ids.invoice_id.payment_state',
             'payment_milestone_ids.invoice_id.amount_residual')
def _compute_milestone_amounts(self):
    """Calculate milestone amounts including payment tracking"""
    for order in self:
        milestones = order.payment_milestone_ids
        order.total_milestone_amount = sum(milestones.mapped('amount'))
        
        invoiced_amount = 0.0
        paid_amount = 0.0
        
        for milestone in milestones:
            if milestone.sub_milestone_ids:
                # Count invoiced sub-milestones
                invoiced_subs = milestone.sub_milestone_ids.filtered(
                    lambda s: s.state == 'invoiced'
                )
                invoiced_amount += sum(invoiced_subs.mapped('amount'))
            else:
                # Count invoiced milestones
                if milestone.state in ('invoiced', 'paid'):
                    invoiced_amount += milestone.amount
        
        # Calculate paid amounts from invoice payments
        for milestone in milestones:
            if milestone.invoice_id and milestone.invoice_id.state == 'posted':
                # Calculate paid amount based on invoice total - residual
                invoice_paid = milestone.invoice_id.amount_total - milestone.invoice_id.amount_residual
                if invoice_paid > 0:
                    paid_amount += invoice_paid
        
        order.invoiced_milestone_amount = invoiced_amount
        order.paid_milestone_amount = paid_amount
```

## User Interface Implementation

### Smart Buttons and Actions
```xml
<!-- Smart buttons in sale order form -->
<button name="action_view_milestones" type="object" class="oe_stat_button" 
        icon="fa-tasks" invisible="not has_progressive_payment">
    <div class="o_field_widget o_stat_info">
        <field name="milestone_count" widget="statinfo" string="Milestones"/>
    </div>
</button>

<button name="action_view_all_milestones" type="object" class="oe_stat_button" 
        icon="fa-list-ul" invisible="not has_progressive_payment">
    <div class="o_stat_info">
        <span class="o_stat_text">All Milestones</span>
    </div>
</button>
```

### Progress Visualization
```xml
<!-- Progress bars and monetary summaries -->
<group string="Milestone Summary">
    <field name="total_milestone_amount" widget="monetary"/>
    <field name="invoiced_milestone_amount" widget="monetary"/>
    <field name="paid_milestone_amount" widget="monetary"/>
    <field name="milestone_progress" widget="progressbar"/>
</group>
```

### State-based Decorations
```xml
<!-- Color-coded milestone tree view -->
<tree decoration-info="state=='draft'" 
      decoration-success="state=='ready'" 
      decoration-warning="state=='invoiced'" 
      decoration-muted="state=='cancelled'">
    <field name="milestone_name"/>
    <field name="state" widget="badge"/>
    <field name="progress_percentage" widget="progressbar"/>
    <button name="action_set_ready" string="Set Ready" type="object" 
            icon="fa-check" invisible="state != 'draft'"/>
    <button name="action_invoice" string="Invoice" type="object" 
            icon="fa-file-text-o" invisible="state != 'ready'"/>
</list>
```

## Testing Implementation

### Unit Tests
```python
class TestProgressivePaymentTerms(TransactionCase):
    
    def test_milestone_generation(self):
        """Test automatic milestone generation from payment terms"""
        
    def test_sub_milestone_workflow(self):
        """Test complete sub-milestone workflow"""
        
    def test_invoice_creation(self):
        """Test milestone invoice creation with dedicated lines"""
        
    def test_reset_functionality(self):
        """Test complete reset with payment cleanup"""
        
    def test_progress_calculation(self):
        """Test progress percentage calculation"""
        
    def test_payment_tracking(self):
        """Test payment amount tracking from invoices"""
```

## Performance Considerations

### Database Optimization
- Proper indexes on milestone state and invoice fields
- Efficient computed field dependencies
- Batch operations for multiple milestone updates
- Optimized queries for progress calculations

### Memory Management
- Lazy loading of related records
- Efficient filtering and mapping operations
- Proper cleanup of temporary records
- Minimal database queries in loops

## Security Implementation

### Access Controls
```xml
<!-- Security groups and access rules -->
<record id="group_milestone_manager" model="res.groups">
    <field name="name">Milestone Manager</field>
    <field name="category_id" ref="base.module_category_construction"/>
</record>

<record id="access_milestone_manager" model="ir.model.access">
    <field name="name">Milestone Manager Access</field>
    <field name="model_id" ref="model_sale_order_payment_milestone"/>
    <field name="group_id" ref="group_milestone_manager"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_write" eval="1"/>
    <field name="perm_create" eval="1"/>
    <field name="perm_unlink" eval="1"/>
</record>
```

### Data Validation
```python
@api.constrains('percentage')
def _check_percentage_range(self):
    """Validate percentage is within valid range"""
    for milestone in self:
        if milestone.percentage < 0 or milestone.percentage > 100:
            raise ValidationError(_('Milestone percentage must be between 0 and 100'))

@api.constrains('amount')
def _check_amount_positive(self):
    """Ensure milestone amount is positive"""
    for milestone in self:
        if milestone.amount < 0:
            raise ValidationError(_('Milestone amount must be positive'))
```

This implementation guide provides the complete technical foundation for the Progressive Payment Terms system, covering all implemented features, workflows, and technical considerations.
## Analytic Distribution Implementation

### Enhanced Models with Project Integration

#### Extended Sale Order Payment Milestone
```python
# Additional analytic tracking field
analytic_account_id = fields.Many2one(
    'account.analytic.account',
    string='Analytic Account',
    compute='_compute_analytic_account_id',
    store=True,
    help='Analytic account for project costing'
)

@api.depends('sale_order_id.project_id.analytic_account_id', 
             'sale_order_id.analytic_account_id', 
             'sale_order_id.order_line.project_id.analytic_account_id')
def _compute_analytic_account_id(self):
    """Compute analytic account from linked project or sale order"""
    for milestone in self:
        analytic_account = False
        
        # Priority 1: Sale order linked project
        if (hasattr(milestone.sale_order_id, 'project_id') and 
            milestone.sale_order_id.project_id and 
            milestone.sale_order_id.project_id.analytic_account_id):
            analytic_account = milestone.sale_order_id.project_id.analytic_account_id
        
        # Priority 2: Sale order direct analytic account
        elif (hasattr(milestone.sale_order_id, 'analytic_account_id') and 
              milestone.sale_order_id.analytic_account_id):
            analytic_account = milestone.sale_order_id.analytic_account_id
        
        # Priority 3: Sale order line project
        elif milestone.sale_order_id.order_line:
            for line in milestone.sale_order_id.order_line:
                if (hasattr(line, 'project_id') and 
                    line.project_id and 
                    line.project_id.analytic_account_id):
                    analytic_account = line.project_id.analytic_account_id
                    break
        
        milestone.analytic_account_id = analytic_account
```

#### Extended Sale Order Payment Sub-milestone
```python
# Inherit analytic account from parent milestone
analytic_account_id = fields.Many2one(
    related='parent_milestone_id.analytic_account_id',
    string='Analytic Account',
    store=True,
    help='Analytic account from parent milestone'
)

def action_create_invoice(self):
    """Enhanced sub-milestone invoice creation with analytic distribution"""
    # ... existing code ...
    
    try:
        # Create invoice using temp milestone
        invoice = self.env['account.move'].create_milestone_invoice([temp_milestone.id])
        
        # Ensure invoice lines have analytic distribution
        if self.analytic_account_id:
            income_lines = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'income')
            for line in income_lines:
                if not line.analytic_distribution:
                    line.analytic_distribution = {self.analytic_account_id.id: 100}
        
        # ... rest of existing code ...
```

#### Enhanced Account Move with Analytic Distribution
```python
def _get_milestone_analytic_distribution(self, sale_order):
    """Get analytic distribution for milestone invoice lines from linked project"""
    analytic_distribution = {}
    
    # Check if sale order has a linked project (from sale_project module)
    if hasattr(sale_order, 'project_id') and sale_order.project_id:
        project = sale_order.project_id
        if project.analytic_account_id:
            analytic_distribution[project.analytic_account_id.id] = 100
    
    # Check if sale order has analytic account directly
    elif hasattr(sale_order, 'analytic_account_id') and sale_order.analytic_account_id:
        analytic_distribution[sale_order.analytic_account_id.id] = 100
    
    # Check if any sale order line has project_id (from sale_project module)
    elif sale_order.order_line:
        for line in sale_order.order_line:
            if hasattr(line, 'project_id') and line.project_id and line.project_id.analytic_account_id:
                analytic_distribution[line.project_id.analytic_account_id.id] = 100
                break
    
    return analytic_distribution

@api.model
def create_milestone_invoice(self, milestone_ids, invoice_vals=None):
    """Enhanced milestone invoice creation with analytic distribution"""
    # ... existing validation and setup code ...
    
    # Create invoice lines for each milestone with analytic distribution
    for milestone in milestones:
        if milestone.sub_milestone_ids:
            # Create invoice lines for completed sub-milestones
            completed_subs = milestone.sub_milestone_ids.filtered(
                lambda s: s.state == 'completed'
            )
            for sub_milestone in completed_subs:
                sale_line = self._create_milestone_sale_line(sale_order, milestone, sub_milestone)
                
                invoice_line_vals = {
                    'move_id': invoice.id,
                    'name': f"{milestone.milestone_name} - {sub_milestone.name}",
                    'quantity': 1.0,
                    'price_unit': sub_milestone.amount,
                    'milestone_id': milestone.id,
                    'account_id': self._get_milestone_account(milestone).id,
                    'sale_line_ids': [(6, 0, [sale_line.id])],
                }
                
                # Add analytic distribution from project
                analytic_distribution = self._get_milestone_analytic_distribution(sale_order)
                if analytic_distribution:
                    invoice_line_vals['analytic_distribution'] = analytic_distribution
                
                self.env['account.move.line'].create(invoice_line_vals)
        else:
            # Create invoice line for milestone without sub-milestones
            sale_line = self._create_milestone_sale_line(sale_order, milestone)
            
            invoice_line_vals = {
                'move_id': invoice.id,
                'name': f"{milestone.milestone_name} - {sale_order.name}",
                'quantity': 1.0,
                'price_unit': milestone.amount,
                'milestone_id': milestone.id,
                'account_id': self._get_milestone_account(milestone).id,
                'sale_line_ids': [(6, 0, [sale_line.id])],
            }
            
            # Add analytic distribution from project
            analytic_distribution = self._get_milestone_analytic_distribution(sale_order)
            if analytic_distribution:
                invoice_line_vals['analytic_distribution'] = analytic_distribution
            
            self.env['account.move.line'].create(invoice_line_vals)
    
    # ... rest of existing code ...

def _create_milestone_sale_line(self, sale_order, milestone, sub_milestone=None):
    """Enhanced sale line creation with project tracking"""
    # ... existing code ...
    
    # Copy project_id if available for analytic tracking
    if original_line:
        sale_line_vals.update({
            # ... existing fields ...
        })
        # Copy project_id if available for analytic tracking
        if hasattr(original_line, 'project_id') and original_line.project_id:
            sale_line_vals['project_id'] = original_line.project_id.id
    
    return self.env['sale.order.line'].create(sale_line_vals)
```

### UI Integration for Analytic Accounts

#### Milestone Views with Analytic Display
```xml
<!-- Enhanced milestone form view -->
<group>
    <group>
        <field name="milestone_name"/>
        <field name="milestone_type"/>
        <field name="sale_order_id"/>
        <field name="payment_term_line_id"/>
        <field name="analytic_account_id" readonly="1" groups="analytic.group_analytic_accounting"/>
    </group>
    <!-- ... rest of form ... -->
</group>

<!-- Enhanced milestone tree view -->
<list string="Payment Milestones" decoration-info="state=='draft'" 
      decoration-success="state=='ready'" decoration-warning="state=='invoiced'">
    <field name="milestone_name"/>
    <field name="milestone_type"/>
    <field name="percentage"/>
    <field name="amount" widget="monetary"/>
    <field name="state" widget="badge"/>
    <field name="progress_percentage" widget="progressbar"/>
    <field name="analytic_account_id" optional="hide" groups="analytic.group_analytic_accounting"/>
</list>
```

#### Sub-milestone Views with Analytic Inheritance
```xml
<!-- Sub-milestone form view with analytic account -->
<group>
    <group>
        <field name="payment_term_line_id" readonly="1"/>
        <field name="sequence"/>
        <field name="percentage"/>
        <field name="analytic_account_id" readonly="1" groups="analytic.group_analytic_accounting"/>
    </group>
    <!-- ... rest of form ... -->
</group>

<!-- Sub-milestone tree view in milestone form -->
<list>
    <field name="sequence" widget="handle"/>
    <field name="name"/>
    <field name="percentage"/>
    <field name="amount" widget="monetary"/>
    <field name="planned_date"/>
    <field name="state" widget="badge"/>
    <field name="analytic_account_id" optional="hide" groups="analytic.group_analytic_accounting"/>
    <!-- ... action buttons ... -->
</list>
```

### Testing Analytic Integration

#### Unit Tests for Analytic Distribution
```python
def test_milestone_analytic_distribution(self):
    """Test that milestone invoices include analytic distribution from linked project"""
    # Create analytic account for project
    analytic_account = self.env['account.analytic.account'].create({
        'name': 'Test Project Analytics',
        'code': 'TEST-PROJ-001',
    })
    
    # Create project with analytic account (if sale_project is available)
    project = None
    if 'project.project' in self.env:
        project = self.env['project.project'].create({
            'name': 'Test Construction Project',
            'analytic_account_id': analytic_account.id,
        })
    
    # Create sale order with project link
    sale_order_vals = {
        'partner_id': self.partner.id,
        'payment_term_id': self.progressive_payment_term.id,
        'order_line': [(0, 0, {
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 1000.0,
        })]
    }
    
    # Add project link if available
    if project:
        sale_order_vals['project_id'] = project.id
    elif 'analytic_account_id' in self.env['sale.order']._fields:
        sale_order_vals['analytic_account_id'] = analytic_account.id
    
    sale_order = self.env['sale.order'].create(sale_order_vals)
    sale_order.action_confirm()
    
    # Get milestone and check analytic account
    milestone = sale_order.payment_milestone_ids[0]
    if project or 'analytic_account_id' in sale_order_vals:
        self.assertEqual(milestone.analytic_account_id, analytic_account)
    
    # Create invoice and verify analytic distribution
    milestone.action_set_ready()
    invoice = self.env['account.move'].create_milestone_invoice([milestone.id])
    
    # Check invoice lines have analytic distribution
    invoice_lines = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'income')
    for line in invoice_lines:
        if project or 'analytic_account_id' in sale_order_vals:
            self.assertTrue(line.analytic_distribution)
            self.assertIn(str(analytic_account.id), line.analytic_distribution)
            self.assertEqual(line.analytic_distribution[str(analytic_account.id)], 100)

def test_sub_milestone_analytic_inheritance(self):
    """Test that sub-milestones inherit analytic account from parent milestone"""
    # Create milestone with analytic account
    milestone = self.create_milestone_with_project()
    
    # Create sub-milestone
    sub_milestone = self.env['sale.order.payment.milestone.sub'].create({
        'parent_milestone_id': milestone.id,
        'name': 'Test Sub-milestone',
        'percentage': 100.0,
        'state': 'completed',
    })
    
    # Check sub-milestone inherits analytic account
    self.assertEqual(sub_milestone.analytic_account_id, milestone.analytic_account_id)
    
    # Create invoice and verify analytic distribution
    result = sub_milestone.action_create_invoice()
    if result.get('res_id'):
        invoice = self.env['account.move'].browse(result['res_id'])
        income_lines = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'income')
        
        for line in income_lines:
            self.assertTrue(line.analytic_distribution)
            self.assertIn(str(milestone.analytic_account_id.id), line.analytic_distribution)
```

### Integration with Standard Odoo Modules

#### Compatibility with sale_project Module
```python
# Automatic detection of project links from sale_project module
def _compute_analytic_account_id(self):
    """Enhanced computation with sale_project compatibility"""
    for milestone in self:
        analytic_account = False
        
        # Check for sale_project module integration
        if hasattr(milestone.sale_order_id, 'project_id'):
            # sale_project module is installed
            if (milestone.sale_order_id.project_id and 
                milestone.sale_order_id.project_id.analytic_account_id):
                analytic_account = milestone.sale_order_id.project_id.analytic_account_id
        
        # Check for direct analytic account on sale order
        if not analytic_account and hasattr(milestone.sale_order_id, 'analytic_account_id'):
            if milestone.sale_order_id.analytic_account_id:
                analytic_account = milestone.sale_order_id.analytic_account_id
        
        # Check for project_id on sale order lines
        if not analytic_account:
            for line in milestone.sale_order_id.order_line:
                if (hasattr(line, 'project_id') and 
                    line.project_id and 
                    line.project_id.analytic_account_id):
                    analytic_account = line.project_id.analytic_account_id
                    break
        
        milestone.analytic_account_id = analytic_account
```

#### Project Costing Integration
```python
# Ensure proper project costing entries are generated
def update_milestone_payment_status(self):
    """Enhanced payment status update with project costing"""
    for move in self:
        if move.is_milestone_invoice and move.milestone_ids:
            # Standard payment status update
            if move.payment_state == 'paid':
                for milestone in move.milestone_ids:
                    if milestone.state == 'invoiced':
                        milestone.write({
                            'state': 'paid',
                            'progress_percentage': 100.0
                        })
            
            # Trigger project costing updates if analytic accounts are present
            analytic_lines = move.line_ids.filtered(lambda l: l.analytic_distribution)
            if analytic_lines:
                # Project costing entries are automatically created by Odoo's analytic system
                # when analytic_distribution is set on invoice lines
                pass
            
            # Trigger sale order amount recalculation
            sale_orders = move.milestone_ids.mapped('sale_order_id')
            if sale_orders:
                sale_orders._compute_milestone_amounts()
                sale_orders._compute_milestone_progress()
```

This enhanced implementation guide now includes complete analytic distribution integration, ensuring proper project costing and financial tracking for construction milestone management while maintaining compatibility with standard Odoo modules.