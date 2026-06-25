# API Reference - Progressive Payment Terms

## Overview

This document provides comprehensive API reference for the Construction Progressive Payment Terms module. All implemented methods, computed fields, and integration points are documented with examples.

## Core Models API

### Sale Order Payment Milestone (`sale.order.payment.milestone`)

#### Fields

##### Core Fields
```python
# Identification
milestone_name = fields.Char(string='Milestone Name', required=True)
milestone_type = fields.Selection(related='payment_term_line_id.milestone_type', store=True)
sequence = fields.Integer(string='Sequence', default=10)

# Relationships
sale_order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
payment_term_line_id = fields.Many2one('account.payment.term.line')

# Financial
percentage = fields.Float(string='Percentage (%)', digits=(5, 2))
amount = fields.Monetary(string='Amount', currency_field='currency_id')
currency_id = fields.Many2one(related='sale_order_id.currency_id', store=True)

# State Management
state = fields.Selection([
    ('draft', 'Draft'),
    ('ready', 'Ready'),
    ('invoiced', 'Invoiced'),
    ('paid', 'Paid'),
    ('cancelled', 'Cancelled')
], string='Status', default='draft')

# Progress Tracking
progress_percentage = fields.Float(
    string='Progress (%)', 
    compute='_compute_progress_percentage', 
    store=True,
    digits=(5, 2)
)

# Dates
planned_date = fields.Date(string='Planned Date')
actual_date = fields.Date(string='Actual Date')

# Sub-milestone Support
allow_sub_milestones = fields.Boolean(string='Allow Sub-milestones', default=False)
sub_milestone_ids = fields.One2many('sale.order.payment.milestone.sub', 'parent_milestone_id')
has_sub_milestones = fields.Boolean(compute='_compute_has_sub_milestones')

# Invoice Integration
invoice_id = fields.Many2one('account.move', string='Invoice')
invoice_line_ids = fields.One2many('account.move.line', 'milestone_id')

# Approval Workflow
approval_required = fields.Boolean(related='payment_term_line_id.approval_required', store=True)
approved_by = fields.Many2one('res.users', string='Approved By')
approved_date = fields.Datetime(string='Approved Date')
```

#### Methods

##### State Management Methods

```python
def action_set_ready(self):
    """
    Mark milestone as ready for invoicing
    
    Validates:
    - All sub-milestones are completed (if applicable)
    - Milestone is in draft state
    
    Returns:
        bool: True if successful
        
    Raises:
        ValidationError: If validation fails
    """
    
def action_invoice(self):
    """
    Create invoice for this milestone
    
    Process:
    1. Validates milestone is in ready state
    2. Creates invoice using account.move.create_milestone_invoice()
    3. Updates milestone state to invoiced
    4. Sets actual_date to today
    
    Returns:
        account.move: Created invoice record
        
    Raises:
        ValidationError: If milestone not ready
    """
    
def action_mark_paid(self):
    """
    Mark milestone as paid
    
    Returns:
        bool: True if successful
    """
    
def action_cancel(self):
    """
    Cancel milestone
    
    Returns:
        bool: True if successful
    """
    
def action_reset_to_draft(self):
    """
    Reset milestone to draft state with complete cleanup - FIXED VERSION
    
    Process:
    1. Restore original sale order line amounts
    2. Handle invoice based on state:
       - Draft: Unlink invoice
       - Posted: Cancel and reset to draft
       - Paid: Remove payments, reconciliation, then cancel
    3. Reset all sub-milestones to draft first
    4. Reset milestone fields to draft state (FIXED: moved to main method)
    
    Returns:
        bool: True if successful
        
    Fix Applied:
    - State reset logic moved from helper method to main action method
    - Ensures proper state updates and return values
    """
```

##### Computed Methods

```python
@api.depends('sub_milestone_ids.state', 'state')
def _compute_progress_percentage(self):
    """
    Compute progress percentage based on sub-milestones or milestone state
    
    Logic:
    - With sub-milestones: (completed + invoiced) / total * 100
    - Without sub-milestones: 
      - Draft: 0%
      - Ready: 50%
      - Invoiced/Paid: 100%
    """
    
@api.depends('sub_milestone_ids')
def _compute_has_sub_milestones(self):
    """Check if milestone has sub-milestones"""
    
@api.depends('planned_date', 'state')
def _compute_is_overdue(self):
    """Compute if milestone is overdue"""
```

##### Business Logic Methods

```python
def calculate_amount(self):
    """
    Recalculate milestone amount based on current order total
    
    Formula: amount = sale_order.amount_total * (percentage / 100.0)
    """
    
def update_progress(self, progress_percentage):
    """
    Update milestone progress
    
    Args:
        progress_percentage (float): Progress percentage (0-100)
        
    Auto-actions:
    - Sets milestone to ready if 100% complete and in draft state
    
    Returns:
        bool: True if successful
    """
    
def _restore_original_sale_lines(self):
    """
    Restore original sale order line amounts when resetting milestone
    
    Process:
    1. Find milestone-specific sale order lines (sequence >= 9999)
    2. Calculate total amount to restore
    3. Set milestone lines quantity to 0
    4. Restore original lines proportionally
    """
```

##### Action Methods

```python
def action_view_invoice(self):
    """
    Open related invoice
    
    Returns:
        dict: Action dictionary for invoice form view
        
    Raises:
        ValidationError: If no invoice found
    """
    
def action_view_sub_milestones(self):
    """
    Open sub-milestones view
    
    Returns:
        dict: Action dictionary for sub-milestones tree/form view
    """
    
def action_create_milestone_invoice(self):
    """
    Create invoice for this milestone directly
    
    Returns:
        dict: Action dictionary for created invoice form view
        
    Raises:
        ValidationError: If milestone not ready
    """
```

### Sub-milestone Template (`account.payment.term.sub.template`)

#### Fields

```python
# Core Fields
name = fields.Char(string='Template Name', required=True)
sequence = fields.Integer(string='Sequence', default=10)
percentage = fields.Float(string='Percentage (%)', digits=(5, 2))
description = fields.Text(string='Description')
```

#### Methods

```python
def create_sub_milestones_from_template(self, parent_milestone):
    """
    Create sub-milestones from this template for given parent milestone
    
    Args:
        parent_milestone (sale.order.payment.milestone): Parent milestone
        
    Returns:
        sale.order.payment.milestone.sub: Created sub-milestone record
    """
    
@api.constrains('percentage')
def _check_percentage_range(self):
    """Validate percentage is within 0-100 range"""
```

### Sale Order Payment Sub-milestone (`sale.order.payment.milestone.sub`)

#### Fields

```python
# Relationships
parent_milestone_id = fields.Many2one('sale.order.payment.milestone', required=True, ondelete='cascade')
sub_milestone_template_id = fields.Many2one('account.payment.term.sub.template')

# Identification
name = fields.Char(string='Sub-milestone Name', required=True)
sequence = fields.Integer(string='Sequence', default=10)

# Financial
percentage = fields.Float(string='Percentage (%)', digits=(5, 2))
amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True)
currency_id = fields.Many2one(related='parent_milestone_id.currency_id')

# State Management
state = fields.Selection([
    ('draft', 'Draft'),
    ('ready', 'Ready'),
    ('completed', 'Completed'),
    ('invoiced', 'Invoiced'),
    ('cancelled', 'Cancelled')
], string='Status', default='draft')

# Dates
planned_date = fields.Date(string='Planned Date')
actual_date = fields.Date(string='Actual Date')
```

#### Methods

```python
def action_set_ready(self):
    """
    Mark sub-milestone as ready
    
    Side effects:
    - Updates parent milestone progress
    
    Returns:
        bool: True if successful
    """
    
def action_complete(self):
    """
    Mark sub-milestone as completed
    
    Process:
    1. Set state to completed
    2. Set actual_date to today
    3. Check if all parent sub-milestones are completed
    4. If yes, set parent milestone to ready
    5. Update parent progress
    
    Returns:
        bool: True if successful
    """
    
def action_create_invoice(self):
    """
    Create invoice for this sub-milestone
    
    Process:
    1. Create temporary milestone record
    2. Generate invoice using create_milestone_invoice()
    3. Link invoice to parent milestone
    4. Mark sub-milestone as invoiced
    5. Update parent milestone status
    
    Returns:
        dict: Action dictionary for created invoice
        
    Raises:
        ValidationError: If sub-milestone not completed
    """
    
def action_reset_to_draft(self):
    """
    Reset sub-milestone to draft state with cleanup
    
    Process:
    1. Restore sale order lines for this sub-milestone
    2. Handle parent invoice cleanup if needed
    3. Reset sub-milestone state
    4. Update parent milestone status
    
    Returns:
        bool: True if successful
    """
    
def _check_parent_milestone_status(self):
    """
    Check if parent milestone should be updated based on sub-milestone states
    
    Logic:
    - If all sub-milestones invoiced: set parent to invoiced
    - If not all invoiced but parent is invoiced: set parent to ready
    - Trigger parent progress recalculation
    """
    
def _restore_sub_milestone_sale_lines(self):
    """
    Restore sale order line amounts when resetting sub-milestone
    
    Process:
    1. Find sub-milestone specific sale order lines
    2. Calculate amount to restore
    3. Set sub-milestone lines quantity to 0
    4. Restore original lines proportionally
    """
```

### Extended Account Move (`account.move`)

#### Methods

```python
@api.model
def create_milestone_invoice(self, milestone_ids, invoice_vals=None):
    """
    Create invoice for specific milestones
    
    Args:
        milestone_ids (list): List of milestone IDs
        invoice_vals (dict, optional): Additional invoice values
        
    Process:
    1. Validate milestones are ready
    2. Create invoice with immediate payment terms
    3. Create dedicated sale order lines for each milestone/sub-milestone
    4. Create invoice lines linked to dedicated sale lines
    5. Update original sale order lines proportionally
    6. Link milestones to invoice
    
    Returns:
        account.move: Created invoice record
        
    Raises:
        ValidationError: If validation fails
    """
    
def _create_milestone_sale_line(self, sale_order, milestone, sub_milestone=None):
    """
    Create dedicated sale order line for milestone invoicing
    
    Args:
        sale_order (sale.order): Source sale order
        milestone (sale.order.payment.milestone): Milestone record
        sub_milestone (sale.order.payment.milestone.sub, optional): Sub-milestone record
        
    Returns:
        sale.order.line: Created sale order line
        
    Features:
    - Sets sequence to 9999+ for milestone tracking
    - Copies product info from original lines
    - Uses milestone/sub-milestone amount as price_unit
    """
    
def _update_original_sale_lines(self, sale_order, milestones):
    """
    Update original sale order lines to reflect remaining amounts
    
    Args:
        sale_order (sale.order): Sale order to update
        milestones (sale.order.payment.milestone): Milestones being invoiced
        
    Process:
    1. Calculate total milestone invoice amount
    2. Get original lines (sequence < 9999)
    3. Deduct milestone amount proportionally from original lines
    4. Maintain minimum price_unit of 0.01 for visibility
    """
    
def _get_milestone_account(self, milestone):
    """
    Get account for milestone invoice lines
    
    Args:
        milestone (sale.order.payment.milestone): Milestone record
        
    Returns:
        account.account: Account for invoice line
        
    Logic:
    1. Try sale order line product accounts
    2. Fallback to company default income account
    """
    
def update_milestone_payment_status(self):
    """
    Update milestone payment status based on invoice payment
    
    Process:
    1. Check invoice payment_state
    2. Update milestone states accordingly:
       - paid: Mark milestones as paid
       - not_paid/partial: Revert to invoiced
    3. Trigger sale order amount recalculation
    """
```

### Extended Sale Order (`sale.order`)

#### Fields

```python
# Progressive Payment Support
has_progressive_payment = fields.Boolean(
    string='Has Progressive Payment',
    compute='_compute_has_progressive_payment',
    store=True
)
payment_milestone_ids = fields.One2many('sale.order.payment.milestone', 'sale_order_id')
milestone_count = fields.Integer(compute='_compute_milestone_count')

# Milestone Amounts
total_milestone_amount = fields.Monetary(
    string='Total Milestone Amount',
    compute='_compute_milestone_amounts',
    store=True
)
invoiced_milestone_amount = fields.Monetary(
    string='Invoiced Milestone Amount', 
    compute='_compute_milestone_amounts',
    store=True
)
paid_milestone_amount = fields.Monetary(
    string='Paid Milestone Amount',
    compute='_compute_milestone_amounts', 
    store=True
)

# Progress Tracking
milestone_progress = fields.Float(
    string='Milestone Progress (%)',
    compute='_compute_milestone_progress'
)
```

#### Methods

```python
@api.depends('payment_term_id.is_progressive')
def _compute_has_progressive_payment(self):
    """Check if order uses progressive payment terms"""
    
@api.depends('payment_milestone_ids')
def _compute_milestone_count(self):
    """Compute number of milestones"""
    
@api.depends('payment_milestone_ids.amount', 'payment_milestone_ids.state',
             'payment_milestone_ids.sub_milestone_ids.amount',
             'payment_milestone_ids.sub_milestone_ids.state',
             'payment_milestone_ids.invoice_id.payment_state',
             'payment_milestone_ids.invoice_id.amount_residual')
def _compute_milestone_amounts(self):
    """
    Compute milestone amounts by state including sub-milestones
    
    Calculations:
    - total_milestone_amount: Sum of all milestone amounts
    - invoiced_milestone_amount: Sum of invoiced milestone/sub-milestone amounts
    - paid_milestone_amount: Sum based on invoice payment status (total - residual)
    """
    
@api.depends('payment_milestone_ids.progress_percentage',
             'payment_milestone_ids.sub_milestone_ids.state')
def _compute_milestone_progress(self):
    """
    Compute overall milestone progress including sub-milestones
    
    Formula: Weighted average based on milestone amounts
    """
    
def _generate_payment_milestones(self):
    """
    Generate payment milestones based on payment term
    
    Process:
    1. Clear existing milestones
    2. Get milestone lines from payment term
    3. Create milestone instances with calculated amounts and dates
    4. Generate sub-milestones from templates if applicable
    """
    
def _generate_sub_milestones(self):
    """
    Generate sub-milestones from templates for milestones that allow them
    
    Process:
    1. Find milestones with allow_sub_milestones = True
    2. Get associated sub-milestone templates from payment term line
    3. Create sub-milestone records with template data
    4. Link sub-milestones to source template for tracking
    
    Template Integration:
    - Uses template name, sequence, percentage, description
    - Maintains link to template via sub_milestone_template_id
    - Allows post-generation customization per project
    """
    
def regenerate_payment_milestones(self):
    """
    Regenerate payment milestones (useful after payment term changes)
    
    Restrictions:
    - Only allowed for draft or sent orders
    
    Returns:
        bool: True if successful
        
    Raises:
        ValidationError: If order state not valid
    """
```

#### Action Methods

```python
def action_view_milestones(self):
    """
    Open milestones view
    
    Returns:
        dict: Action dictionary for milestone tree/form view
    """
    
def action_create_milestone_invoice(self):
    """
    Open wizard to create milestone invoice
    
    Returns:
        dict: Action dictionary for milestone invoice wizard
        
    Raises:
        ValidationError: If no ready milestones found
    """
    
def action_milestone_dashboard(self):
    """
    Open milestone dashboard
    
    Returns:
        dict: Action dictionary for milestone kanban/tree view grouped by state
    """
    
def action_view_all_milestones(self):
    """
    Open unified view of all milestones and sub-milestones
    
    Returns:
        dict: Action dictionary for comprehensive milestone view
    """
```

## Integration APIs

### Payment Term Extensions

#### Extended Account Payment Term (`account.payment.term`)

```python
# Additional Fields
is_progressive = fields.Boolean(string='Progressive Payment Term', default=False)
construction_category = fields.Selection([
    ('elv', 'ELV (Extra Low Voltage)'),
    ('mep', 'MEP (Mechanical, Electrical, Plumbing)'),
    ('civil', 'Civil Works'),
    ('structural', 'Structural Works'),
    ('infrastructure', 'Infrastructure'),
    ('fitout', 'Fit-out Works'),
    ('specialized', 'Specialized Systems'),
    ('generic', 'Generic Construction')
], string='Construction Category')
```

#### Extended Account Payment Term Line (`account.payment.term.line`)

```python
# Milestone Support
is_milestone = fields.Boolean(string='Is Milestone', default=False)
milestone_type = fields.Selection([
    ('advance', 'Advance Payment'),
    ('material_delivery', 'Material Delivery'),
    ('work_completion', 'Work Completion'),
    ('testing_commissioning', 'Testing & Commissioning'),
    ('final_payment', 'Final Payment'),
    ('retention_release', 'Retention Release')
], string='Milestone Type')

milestone_display_name = fields.Char(string='Milestone Display Name')
milestone_description = fields.Html(string='Milestone Description')
required_documents = fields.Text(string='Required Documents')
approval_required = fields.Boolean(string='Approval Required', default=False)
```

## Usage Examples

### Creating Sub-milestone Templates

```python
# Create Material Delivery template
material_template = env['account.payment.term.sub.template'].create({
    'name': 'Steel Delivery',
    'sequence': 10,
    'percentage': 40.0,
    'description': 'Steel materials delivery and inspection',
})

concrete_template = env['account.payment.term.sub.template'].create({
    'name': 'Concrete Delivery', 
    'sequence': 20,
    'percentage': 35.0,
    'description': 'Concrete materials delivery and testing',
})

finishing_template = env['account.payment.term.sub.template'].create({
    'name': 'Finishing Materials',
    'sequence': 30, 
    'percentage': 25.0,
    'description': 'Finishing materials delivery',
})
```

### Creating Payment Terms with Templates

```python
# Create progressive payment term with sub-milestone templates
payment_term = env['account.payment.term'].create({
    'name': 'Construction Progressive with Templates',
    'is_progressive': True,
    'construction_category': 'civil',
    'line_ids': [
        (0, 0, {
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'value': 'percent',
            'value_amount': 40.0,
            'nb_days': 15,
            'milestone_display_name': 'Material Delivery',
            'allow_sub_milestones': True,
            'sub_milestone_template_ids': [(6, 0, [
                material_template.id,
                concrete_template.id, 
                finishing_template.id
            ])],
        }),
    ]
})
```

### Creating Milestones Programmatically

```python
# Create progressive payment term
payment_term = env['account.payment.term'].create({
    'name': 'Construction Progressive Payment',
    'is_progressive': True,
    'construction_category': 'mep',
    'line_ids': [
        (0, 0, {
            'is_milestone': True,
            'milestone_type': 'advance',
            'value': 'percent',
            'value_amount': 20.0,
            'nb_days': 0,
            'milestone_display_name': 'Advance Payment',
        }),
        (0, 0, {
            'is_milestone': True,
            'milestone_type': 'material_delivery',
            'value': 'percent', 
            'value_amount': 30.0,
            'nb_days': 30,
            'milestone_display_name': 'Material Delivery',
        }),
    ]
})

# Apply to sale order
sale_order = env['sale.order'].create({
    'partner_id': partner.id,
    'payment_term_id': payment_term.id,
    'order_line': [(0, 0, {
        'product_id': product.id,
        'product_uom_qty': 1,
        'price_unit': 10000,
    })]
})

# Confirm order to generate milestones
sale_order.action_confirm()

# Access generated milestones and sub-milestones
milestones = sale_order.payment_milestone_ids
print(f"Generated {len(milestones)} milestones")

# Check auto-generated sub-milestones
for milestone in milestones:
    if milestone.sub_milestone_ids:
        print(f"Milestone '{milestone.milestone_name}' has {len(milestone.sub_milestone_ids)} sub-milestones:")
        for sub in milestone.sub_milestone_ids:
            print(f"  - {sub.name}: {sub.percentage}% (from template: {sub.sub_milestone_template_id.name})")
```

### Milestone Workflow Management

```python
# Get first milestone
milestone = sale_order.payment_milestone_ids[0]

# Set milestone ready
milestone.action_set_ready()

# Create invoice
invoice = milestone.action_invoice()
print(f"Created invoice: {invoice.name}")

# Check progress
print(f"Milestone progress: {milestone.progress_percentage}%")
print(f"Order progress: {sale_order.milestone_progress}%")

# Reset if needed
milestone.action_reset_to_draft()
```

### Sub-milestone Management

```python
# Sub-milestones are auto-generated from templates during order confirmation
# Access existing sub-milestones
sub_milestones = milestone.sub_milestone_ids
print(f"Found {len(sub_milestones)} sub-milestones")

# Manually create additional sub-milestones if needed
sub_milestone_1 = env['sale.order.payment.milestone.sub'].create({
    'parent_milestone_id': milestone.id,
    'name': 'Custom Phase',
    'percentage': 60.0,
    'sequence': 10,
})

sub_milestone_2 = env['sale.order.payment.milestone.sub'].create({
    'parent_milestone_id': milestone.id,
    'name': 'Phase 2 Delivery', 
    'percentage': 40.0,
    'sequence': 20,
})

# Complete sub-milestones
sub_milestone_1.action_set_ready()
sub_milestone_1.action_complete()

# Create individual invoice
invoice = sub_milestone_1.action_create_invoice()
```

### Payment Tracking

```python
# Check payment amounts
print(f"Total milestone amount: {sale_order.total_milestone_amount}")
print(f"Invoiced amount: {sale_order.invoiced_milestone_amount}")
print(f"Paid amount: {sale_order.paid_milestone_amount}")

# Check individual milestone payment status
for milestone in sale_order.payment_milestone_ids:
    if milestone.invoice_id:
        paid_amount = milestone.invoice_id.amount_total - milestone.invoice_id.amount_residual
        print(f"Milestone {milestone.milestone_name}: Paid {paid_amount}")
```

## Error Handling

### Common Exceptions

```python
# ValidationError examples
try:
    milestone.action_set_ready()
except ValidationError as e:
    # Handle validation errors
    print(f"Validation failed: {e}")

try:
    milestone.action_invoice()
except ValidationError as e:
    # Handle invoicing errors
    print(f"Invoice creation failed: {e}")
```

### Error Codes and Messages

| Error Code | Message | Solution |
|------------|---------|----------|
| `MILESTONE_NOT_READY` | Only ready milestones can be invoiced | Set milestone to ready state first |
| `SUB_MILESTONES_INCOMPLETE` | Complete all sub-milestones first | Complete all sub-milestones before setting parent ready |
| `INVALID_PERCENTAGE` | Percentage must be between 0 and 100 | Check milestone/template percentage values |
| `NEGATIVE_AMOUNT` | Amount must be positive | Verify milestone amount calculation |
| `TEMPLATE_NOT_FOUND` | Sub-milestone template not found | Ensure template exists and is linked to payment term |
| `RESET_FAILED` | Reset to draft failed | Check invoice state and payment status |

## Performance Considerations

### Optimized Queries
- Use `filtered()` instead of loops for record filtering
- Batch operations when possible
- Proper use of `@api.depends` for computed fields
- Efficient database queries with proper indexes

### Memory Management
- Use `ensure_one()` for single record operations
- Avoid loading unnecessary related records
- Use `mapped()` for efficient field extraction
- Proper cleanup of temporary records

This API reference provides complete documentation for all implemented functionality in the Progressive Payment Terms module.
## Analytic Distribution API

### Extended Account Move (`account.move`)

#### Analytic Integration Methods

```python
def _get_milestone_analytic_distribution(self, sale_order):
    """
    Get analytic distribution for milestone invoice lines from linked project
    
    Args:
        sale_order (sale.order): Sale order to extract analytic account from
        
    Returns:
        dict: Analytic distribution dictionary {account_id: percentage}
        
    Detection Logic:
    1. Check if sale order has linked project (project_id.analytic_account_id)
    2. Check if sale order has direct analytic account (analytic_account_id)
    3. Check if any sale order line has project_id with analytic account
    
    Example:
        {123: 100}  # 100% allocation to analytic account ID 123
    """
```

### Extended Sale Order Payment Milestone (`sale.order.payment.milestone`)

#### Analytic Fields

```python
# Analytic Integration
analytic_account_id = fields.Many2one(
    'account.analytic.account',
    string='Analytic Account',
    compute='_compute_analytic_account_id',
    store=True,
    help='Analytic account for project costing'
)
```

#### Analytic Computed Methods

```python
@api.depends('sale_order_id.project_id.analytic_account_id', 
             'sale_order_id.analytic_account_id', 
             'sale_order_id.order_line.project_id.analytic_account_id')
def _compute_analytic_account_id(self):
    """
    Compute analytic account from linked project or sale order
    
    Priority Order:
    1. Sale order linked project analytic account
    2. Sale order direct analytic account  
    3. Sale order line project analytic account (first found)
    
    Updates milestone analytic_account_id field for project costing integration
    """
```

### Extended Sale Order Payment Sub-milestone (`sale.order.payment.milestone.sub`)

#### Analytic Fields

```python
# Analytic Integration
analytic_account_id = fields.Many2one(
    related='parent_milestone_id.analytic_account_id',
    string='Analytic Account',
    store=True,
    help='Analytic account from parent milestone'
)
```

#### Enhanced Invoice Creation

```python
def action_create_invoice(self):
    """
    Create invoice for this sub-milestone with analytic distribution
    
    Enhanced Process:
    1. Create temporary milestone record
    2. Generate invoice using create_milestone_invoice()
    3. Ensure invoice lines have analytic distribution from parent milestone
    4. Link invoice to parent milestone
    5. Mark sub-milestone as invoiced
    6. Update parent milestone status
    
    Analytic Integration:
    - Automatically applies analytic distribution to invoice lines
    - Uses parent milestone's analytic account
    - Ensures proper project costing entries
    
    Returns:
        dict: Action dictionary for created invoice with analytic distribution
    """
```

## Integration Examples

### Project-Linked Milestone Creation

```python
# Create project with analytic account
analytic_account = env['account.analytic.account'].create({
    'name': 'Construction Project Analytics',
    'code': 'PROJ-001',
})

project = env['project.project'].create({
    'name': 'Office Building Construction',
    'analytic_account_id': analytic_account.id,
})

# Create sale order with project link
sale_order = env['sale.order'].create({
    'partner_id': customer.id,
    'project_id': project.id,  # Links to project
    'payment_term_id': progressive_payment_term.id,
    'order_line': [(0, 0, {
        'product_id': construction_service.id,
        'product_uom_qty': 1,
        'price_unit': 100000,
        'project_id': project.id,  # Line-level project link
    })]
})

# Confirm order - milestones inherit analytic account
sale_order.action_confirm()

# Check milestone analytic account
milestone = sale_order.payment_milestone_ids[0]
print(f"Milestone analytic account: {milestone.analytic_account_id.name}")
# Output: "Construction Project Analytics"
```

### Analytic Distribution in Invoice Creation

```python
# Set milestone ready and create invoice
milestone.action_set_ready()
invoice = milestone.action_invoice()

# Check invoice lines have analytic distribution
for line in invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'income'):
    print(f"Line: {line.name}")
    print(f"Analytic Distribution: {line.analytic_distribution}")
    # Output: {123: 100.0} - 100% to analytic account ID 123
```

### Sub-milestone Analytic Inheritance

```python
# Create sub-milestone
sub_milestone = env['sale.order.payment.milestone.sub'].create({
    'parent_milestone_id': milestone.id,
    'name': 'Foundation Work',
    'percentage': 50.0,
})

# Sub-milestone inherits parent analytic account
print(f"Sub-milestone analytic account: {sub_milestone.analytic_account_id.name}")
# Output: "Construction Project Analytics"

# Complete and invoice sub-milestone
sub_milestone.action_set_ready()
sub_milestone.action_complete()
sub_invoice = sub_milestone.action_create_invoice()

# Check sub-milestone invoice has analytic distribution
for line in sub_invoice['res_id'] and env['account.move'].browse(sub_invoice['res_id']).line_ids:
    if line.account_id.user_type_id.type == 'income':
        print(f"Sub-milestone analytic distribution: {line.analytic_distribution}")
```

## Testing Analytic Integration

### Unit Test Examples

```python
def test_milestone_analytic_account_computation(self):
    """Test analytic account computation from project"""
    # Create analytic account and project
    analytic_account = self.env['account.analytic.account'].create({
        'name': 'Test Project Analytics',
        'code': 'TEST-001',
    })
    
    project = self.env['project.project'].create({
        'name': 'Test Project',
        'analytic_account_id': analytic_account.id,
    })
    
    # Create sale order with project
    sale_order = self.env['sale.order'].create({
        'partner_id': self.partner.id,
        'project_id': project.id,
        'payment_term_id': self.progressive_payment_term.id,
        'order_line': [(0, 0, {
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 1000,
        })]
    })
    
    sale_order.action_confirm()
    milestone = sale_order.payment_milestone_ids[0]
    
    # Assert analytic account is computed correctly
    self.assertEqual(milestone.analytic_account_id, analytic_account)

def test_invoice_analytic_distribution(self):
    """Test invoice lines include analytic distribution"""
    milestone = self.create_milestone_with_project()
    milestone.action_set_ready()
    invoice = milestone.action_invoice()
    
    # Check invoice lines have analytic distribution
    income_lines = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'income')
    for line in income_lines:
        self.assertTrue(line.analytic_distribution)
        self.assertIn(str(milestone.analytic_account_id.id), line.analytic_distribution)
        self.assertEqual(line.analytic_distribution[str(milestone.analytic_account_id.id)], 100)
```

This enhanced API reference now includes complete documentation for the analytic distribution integration, ensuring proper project costing and financial tracking for construction milestone management.