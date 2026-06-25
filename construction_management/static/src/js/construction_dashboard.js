/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ConstructionDashboard extends Component {
    static template = "construction_management.ConstructionDashboard";
    
    setup() {
        // Dashboard setup logic will be implemented in later tasks
    }
}

registry.category("actions").add("construction_dashboard", ConstructionDashboard);