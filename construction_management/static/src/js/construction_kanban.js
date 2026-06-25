/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";

export class ConstructionKanbanController extends KanbanController {
    // Construction-specific kanban controller logic will be implemented in later tasks
}

export class ConstructionKanbanRenderer extends KanbanRenderer {
    // Construction-specific kanban renderer logic will be implemented in later tasks
}

export const constructionKanbanView = {
    ...kanbanView,
    Controller: ConstructionKanbanController,
    Renderer: ConstructionKanbanRenderer,
};

registry.category("views").add("construction_kanban", constructionKanbanView);