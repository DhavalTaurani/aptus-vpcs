/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * Progressive Payment Widget
 * Provides enhanced UI for progressive payment term management
 */
export class ProgressivePaymentWidget extends Component {
    static template = "construction_progressive_payment_terms.ProgressivePaymentWidget";
    
    setup() {
        super.setup();
        this.milestoneTypes = {
            'advance': 'Advance Payment',
            'material_delivery': 'Material Delivery',
            'installation': 'Installation Completion',
            'testing_commissioning': 'Testing & Commissioning',
            'retention': 'Retention',
            'custom': 'Custom Milestone'
        };
    }
    
    get milestoneTypeLabel() {
        return this.milestoneTypes[this.props.record.data.milestone_type] || 'Unknown';
    }
    
    get progressivePaymentClass() {
        const milestoneType = this.props.record.data.milestone_type;
        return `o_progressive_payment_milestone milestone_${milestoneType}`;
    }
}

registry.category("fields").add("progressive_payment_widget", {
    component: ProgressivePaymentWidget,
});