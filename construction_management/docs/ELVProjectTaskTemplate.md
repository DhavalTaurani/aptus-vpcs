# ELV Project Template - Odoo 17 Construction Management

## Overview
This document outlines the standardized **Extra Low Voltage (ELV) Project Template** structure implemented in Odoo 17 Construction Management module. The template provides a comprehensive framework for ELV projects including CCTV, access control, fire alarm systems, and network infrastructure.

**Template ID:** `template_elv`  
**Template Name:** Extra Low Voltage (ELV) Project  
**Category:** `elv`  
**Version:** 1.0  
**Status:** Approved

---

## Project Hierarchy Structure

The ELV template follows a three-level hierarchy:
1. **Project Level** - Overall project management
2. **Phase Level** - Major work phases (Design, Installation, Testing)
3. **Work Package Level** - BOQ items and detailed tasks

---

## Phase 1: Design and Engineering
**Task Template ID:** `elv_task_design`  
**Sequence:** 10  
**Hierarchy Level:** Phase Level  
**Initial Stage:** Draft  
**BOQ Item:** No

### Description
System design, drawings, and engineering calculations for ELV systems including:
- Site survey and assessment
- System architecture design
- Technical drawings and schematics
- Equipment specifications
- Installation methodology
- Testing procedures

### Deliverables
- Approved system design drawings
- Equipment specifications and BOQ
- Installation methodology document
- Testing and commissioning procedures

---

## Phase 2: CCTV System Installation
**Task Template ID:** `elv_task_cctv`  
**Parent Task:** `elv_task_design`  
**Sequence:** 20  
**Hierarchy Level:** Work Package (BOQ Level)  
**BOQ Code:** `ELV-CCTV-001`  
**Initial Stage:** Draft  
**BOQ Item:** Yes

### Cost Information
- **Estimated Quantity:** 1 system
- **Unit Cost:** $5,000.00
- **Cost Code:** Equipment (`TPL-EQP`)
- **Cost Type:** Equipment

### BOQ Template Details
**BOQ Template ID:** `boq_elv_cctv`
- **BOQ Item:** CCTV Camera System
- **Quantity:** 10 units
- **Unit Cost:** $500.00 per camera
- **Total Cost:** $5,000.00
- **Description:** IP cameras with night vision and motion detection

### Sub-Tasks and Work Packages

#### 2.1 Infrastructure Preparation
- **Task Code:** `CCTV-INFRA`
- **Duration:** 3-5 days
- **Cost Code:** Material (`TPL-MAT`)

**Sub-tasks:**
- Cable tray and conduit installation
- Power supply preparation
- Network infrastructure setup
- Mounting bracket installation

#### 2.2 Camera Installation and Mounting
- **Task Code:** `CCTV-MOUNT`
- **Duration:** 2-3 days
- **Cost Code:** Labour (`TPL-LAB`)

**Sub-tasks:**
- Camera mounting and positioning
- Cable termination and connection
- Power supply connection
- Initial camera configuration

#### 2.3 System Configuration and Testing
- **Task Code:** `CCTV-CONFIG`
- **Duration:** 2-3 days
- **Cost Code:** Labour (`TPL-LAB`)

**Sub-tasks:**
- DVR/NVR configuration
- Network setup and IP assignment
- Recording settings configuration
- Motion detection calibration
- System testing and validation

### Resource Allocation
**Resource Template ID:** `resource_elv_technician`
- **Resource Type:** Human
- **Allocated Quantity:** 2 technicians
- **Duration:** 5 days
- **Unit Cost:** $200.00 per day per technician
- **Total Resource Cost:** $2,000.00
- **Description:** Skilled ELV technicians for CCTV installation

---

## Phase 3: Access Control System
**Task Template ID:** `elv_task_access`  
**Parent Task:** `elv_task_design`  
**Sequence:** 30  
**Hierarchy Level:** Work Package (BOQ Level)  
**BOQ Code:** `ELV-ACC-001`  
**Initial Stage:** Draft  
**BOQ Item:** Yes

### Cost Information
- **Estimated Quantity:** 1 system
- **Unit Cost:** $3,000.00
- **Cost Code:** Equipment (`TPL-EQP`)
- **Cost Type:** Equipment

### Sub-Tasks and Work Packages

#### 3.1 Access Control Infrastructure
- **Task Code:** `ACS-INFRA`
- **Duration:** 2-3 days
- **Cost Code:** Material (`TPL-MAT`)

**Sub-tasks:**
- Door preparation and hardware installation
- Cable routing for card readers
- Controller mounting and connection
- Power supply installation

#### 3.2 Card Reader Installation
- **Task Code:** `ACS-READER`
- **Duration:** 1-2 days
- **Cost Code:** Equipment (`TPL-EQP`)

**Sub-tasks:**
- Card reader mounting
- Wiring and connection
- Communication setup
- Initial testing

#### 3.3 System Programming and Configuration
- **Task Code:** `ACS-CONFIG`
- **Duration:** 2-3 days
- **Cost Code:** Labour (`TPL-LAB`)

**Sub-tasks:**
- Access control software installation
- User database setup
- Access level configuration
- Integration with other systems
- System testing and validation

---

## Phase 4: Additional ELV Systems (Expandable)

### 4.1 Fire Alarm System
- **Task Code:** `ELV-FIRE`
- **BOQ Code:** `ELV-FIRE-001`
- **Cost Code:** Equipment (`TPL-EQP`)

### 4.2 Public Address System
- **Task Code:** `ELV-PA`
- **BOQ Code:** `ELV-PA-001`
- **Cost Code:** Equipment (`TPL-EQP`)

### 4.3 Network Infrastructure
- **Task Code:** `ELV-NET`
- **BOQ Code:** `ELV-NET-001`
- **Cost Code:** Equipment (`TPL-EQP`)

### 4.4 Intercom System
- **Task Code:** `ELV-INTERCOM`
- **BOQ Code:** `ELV-INTERCOM-001`
- **Cost Code:** Equipment (`TPL-EQP`)

---

## Cost Estimation Templates

### Material Costs
**Template ID:** `cost_est_elv_materials`
- **Category:** Material
- **Estimated Cost:** $10,000.00
- **Contingency:** 15%
- **Description:** Cables, conduits, and installation materials for ELV systems

### Labour Costs
**Template ID:** `cost_est_elv_labour`
- **Category:** Labour
- **Estimated Cost:** $8,000.00
- **Contingency:** 10%
- **Description:** Skilled technicians for ELV system installation and testing

---

## Milestone Templates

### Design Approval Milestone
**Template ID:** `milestone_elv_design_approval`
- **Milestone Type:** Approval
- **Days from Start:** 7 days
- **Payment Milestone:** No
- **Description:** Approval of ELV system design and drawings

### Installation Complete Milestone
**Template ID:** `milestone_elv_installation_complete`
- **Milestone Type:** Phase Completion
- **Days from Start:** 30 days
- **Payment Milestone:** Yes
- **Payment Percentage:** 50%
- **Description:** Completion of ELV system installation

---

## Cost Code Structure

| Cost Code | Type | Description | Usage |
|-----------|------|-------------|-------|
| `TPL-MAT` | Material | Construction materials | Cables, conduits, mounting hardware |
| `TPL-LAB` | Labour | Construction labour | Installation, configuration, testing |
| `TPL-EQP` | Equipment | Construction equipment | Cameras, controllers, software |
| `TPL-SUB` | Subcontractor | Subcontractor services | Specialized installation services |
| `TPL-MISC` | Miscellaneous | Miscellaneous costs | Permits, documentation, training |
| `TPL-OH` | Overhead | Overhead costs | Project management, supervision |

---

## Template Usage and Implementation

### Creating Projects from Template
1. Navigate to Construction → Templates → Project Templates
2. Select "Extra Low Voltage (ELV) Project" template
3. Click "Create Project from Template"
4. Customize project-specific details
5. Generate tasks and BOQ items automatically

### Template Customization
- Tasks can be added, modified, or removed per project
- BOQ quantities and costs can be adjusted
- Resource allocations can be customized
- Milestones can be modified based on project requirements

### Integration Points
- **Project Management:** Full integration with Odoo project tasks
- **Inventory:** BOQ items linked to product catalog
- **Purchasing:** Automatic purchase order generation
- **Accounting:** Cost tracking and financial reporting
- **HR:** Resource allocation and timesheet integration

---

## Version History

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| 1.0 | Current | Initial ELV template with CCTV and access control systems | Approved |

---

## Technical Implementation Details

### Database Structure
- **Project Template:** `construction.project.template`
- **Task Templates:** `construction.task.template`
- **BOQ Templates:** `construction.boq.template`
- **Cost Estimation:** `construction.cost.estimation.template`
- **Resource Allocation:** `construction.resource.allocation.template`
- **Milestones:** `construction.milestone.template`

### Template Data Location
- **File:** `construction_17/construction_management/data/construction_templates.xml`
- **Records:** `template_elv`, `elv_task_*`, `boq_elv_*`, `cost_est_elv_*`

### Extensibility
The template is designed to be easily extended with additional ELV systems and can be customized per project requirements while maintaining the standard structure and cost tracking capabilities.

---

# ELV Comprehensive Installation Template

## Overview
**Template ID:** `template_elv_comprehensive`  
**Template Name:** ELV Complete Installation Project  
**Category:** `elv`  
**Version:** 2.0  
**Status:** Approved

This comprehensive template covers the complete ELV installation workflow from infrastructure preparation to final system configuration and testing.

---

## Complete Installation Workflow

### Phase 1: Trunking and Conduiting
**Task ID:** `elv_comp_task_trunking`  
**Sequence:** 10  
**BOQ Code:** `ELV-TRUNK-001`  
**Hierarchy Level:** Phase Level

#### Description
Installation of cable trays, conduits, and cable management infrastructure

#### BOQ Details
- **Quantity:** 100 meters
- **Unit Cost:** $25.00 per meter
- **Total Cost:** $2,500.00
- **Cost Code:** Material (`TPL-MAT`)
- **Items:** Cable trays, conduits, brackets, and mounting hardware

---

### Phase 2: Cable Pulling/Laying
**Task ID:** `elv_comp_task_cabling`  
**Sequence:** 20  
**BOQ Code:** `ELV-CABLE-001`  
**Parent Task:** Trunking and Conduiting

#### Description
Installation and pulling of all ELV cables including data, power, and control cables

#### BOQ Details
- **Quantity:** 500 meters
- **Unit Cost:** $15.00 per meter
- **Total Cost:** $7,500.00
- **Cost Code:** Material (`TPL-MAT`)
- **Items:** Cat6 data cables, power cables, coaxial cables, and control cables

---

### Phase 3: User-Side Termination
**Task ID:** `elv_comp_task_user_termination`  
**Sequence:** 30  
**BOQ Code:** `ELV-USER-TERM-001`  
**Parent Task:** Cable Pulling/Laying

#### Description
Termination of cables at user end points including outlets, junction boxes, and device connections

#### BOQ Details
- **Quantity:** 50 termination points
- **Unit Cost:** $30.00 per point
- **Total Cost:** $1,500.00
- **Cost Code:** Labour (`TPL-LAB`)
- **Items:** RJ45 outlets, junction boxes, cable termination, and testing

---

### Phase 4: Rack Installation
**Task ID:** `elv_comp_task_rack_installation`  
**Sequence:** 40  
**BOQ Code:** `ELV-RACK-001`  
**Parent Task:** Cable Pulling/Laying

#### Description
Installation and setup of server racks, power distribution, and cooling systems

#### BOQ Details
- **Quantity:** 3 racks
- **Unit Cost:** $1,500.00 per rack
- **Total Cost:** $4,500.00
- **Cost Code:** Equipment (`TPL-EQP`)
- **Items:** 42U server racks with PDU, cooling, and cable management

---

### Phase 5: Rack Side Termination
**Task ID:** `elv_comp_task_rack_termination`  
**Sequence:** 50  
**BOQ Code:** `ELV-RACK-TERM-001`  
**Parent Task:** Rack Installation

#### Description
Termination of all cables at rack side including patch panels and distribution panels

#### BOQ Details
- **Quantity:** 3 rack terminations
- **Unit Cost:** $800.00 per rack
- **Total Cost:** $2,400.00
- **Cost Code:** Labour (`TPL-LAB`)
- **Items:** Patch panels, distribution panels, cable management, and testing

---

### Phase 6: Device Installation and Mounting
**Task ID:** `elv_comp_task_device_installation`  
**Sequence:** 60  
**Parent Task:** Rack Side Termination

#### 6a. Camera Installation and Fixing
**Task ID:** `elv_comp_task_camera_fixing`  
**BOQ Code:** `ELV-CAM-FIX-001`

- **Quantity:** 20 cameras
- **Unit Cost:** $350.00 per camera
- **Total Cost:** $7,000.00
- **Items:** IP cameras with mounting brackets, weatherproof housing, and connections

#### 6b. Access Control System Installation
**Task ID:** `elv_comp_task_acs_fixing`  
**BOQ Code:** `ELV-ACS-FIX-001`

- **Quantity:** 15 access points
- **Unit Cost:** $450.00 per point
- **Total Cost:** $6,750.00
- **Items:** Card readers, controllers, electric locks, and door sensors

#### 6c. WiFi Access Point Installation
**Task ID:** `elv_comp_task_wifi_fixing`  
**BOQ Code:** `ELV-WIFI-FIX-001`

- **Quantity:** 12 access points
- **Unit Cost:** $280.00 per point
- **Total Cost:** $3,360.00
- **Items:** Enterprise WiFi access points with ceiling/wall mounting and PoE

#### 6d. Network Access Point Installation
**Task ID:** `elv_comp_task_ap_fixing`  
**BOQ Code:** `ELV-AP-FIX-001`

- **Quantity:** 30 outlets
- **Unit Cost:** $120.00 per outlet
- **Total Cost:** $3,600.00
- **Items:** RJ45 outlets, face plates, and network connection points

#### 6e. Speaker Installation and Fixing
**Task ID:** `elv_comp_task_speaker_fixing`  
**BOQ Code:** `ELV-SPEAK-FIX-001`

- **Quantity:** 25 speakers
- **Unit Cost:** $180.00 per speaker
- **Total Cost:** $4,500.00
- **Items:** Ceiling and wall mounted speakers with brackets and connections

#### 6f. Amplifier Installation and Fixing
**Task ID:** `elv_comp_task_amplifier_fixing`  
**BOQ Code:** `ELV-AMP-FIX-001`

- **Quantity:** 5 amplifiers
- **Unit Cost:** $800.00 per amplifier
- **Total Cost:** $4,000.00
- **Items:** Rack-mounted amplifiers with control modules and connections

#### 6g. Network Switch Installation
**Task ID:** `elv_comp_task_switch_fixing`  
**BOQ Code:** `ELV-SWITCH-FIX-001`

- **Quantity:** 8 switches
- **Unit Cost:** $1,200.00 per switch
- **Total Cost:** $9,600.00
- **Items:** Managed PoE switches with rack mounting and redundancy

---

### Phase 7: System Configuration and Testing
**Task ID:** `elv_comp_task_configuration`  
**Sequence:** 70  
**BOQ Code:** `ELV-CONFIG-001`  
**Parent Task:** Device Installation and Mounting

#### Description
Complete system configuration, integration, testing, and commissioning

#### BOQ Details
- **Quantity:** 1 complete system
- **Unit Cost:** $5,000.00
- **Total Cost:** $5,000.00
- **Cost Code:** Labour (`TPL-LAB`)
- **Items:** Network configuration, system integration, testing, and documentation

#### Configuration Tasks Include:
- Network VLAN configuration
- IP address assignment and management
- CCTV system configuration and recording setup
- Access control database and user management
- WiFi network configuration and security
- Audio system calibration and zone setup
- System integration and testing
- Documentation and user training

---

## Comprehensive Cost Summary

### Cost Estimation Templates

#### Materials
**Template ID:** `cost_est_elv_comp_materials`
- **Estimated Cost:** $35,000.00
- **Contingency:** 15%
- **Total with Contingency:** $40,250.00

#### Labour
**Template ID:** `cost_est_elv_comp_labour`
- **Estimated Cost:** $25,000.00
- **Contingency:** 12%
- **Total with Contingency:** $28,000.00

#### Equipment
**Template ID:** `cost_est_elv_comp_equipment`
- **Estimated Cost:** $45,000.00
- **Contingency:** 10%
- **Total with Contingency:** $49,500.00

### **Total Project Cost:** $117,750.00

---

## Milestone Schedule

| Milestone | Days from Start | Payment % | Amount |
|-----------|----------------|-----------|---------|
| Infrastructure Complete | 15 days | 20% | $23,550.00 |
| Termination Complete | 30 days | 35% | $41,212.50 |
| Device Installation Complete | 50 days | 70% | $82,425.00 |
| System Configuration Complete | 65 days | 100% | $117,750.00 |

---

## Resource Allocation

### Infrastructure Installation Team
- **Team Size:** 4 technicians
- **Duration:** 15 days
- **Rate:** $250.00 per day per technician
- **Total Cost:** $15,000.00

### Device Installation Team
- **Team Size:** 6 technicians
- **Duration:** 20 days
- **Rate:** $300.00 per day per technician
- **Total Cost:** $36,000.00

### Configuration and Testing Team
- **Team Size:** 3 system engineers
- **Duration:** 15 days
- **Rate:** $400.00 per day per engineer
- **Total Cost:** $18,000.00

### **Total Resource Cost:** $69,000.00

---

## Template Comparison

| Feature | Basic ELV Template | Comprehensive ELV Template |
|---------|-------------------|---------------------------|
| **Template ID** | `template_elv` | `template_elv_comprehensive` |
| **Version** | 1.0 | 2.0 |
| **Task Count** | 3 main tasks | 15+ detailed tasks |
| **BOQ Items** | 2 items | 12+ items |
| **Cost Estimate** | ~$18,000 | ~$117,750 |
| **Duration** | 30 days | 65 days |
| **Workflow Coverage** | Basic CCTV + Access Control | Complete ELV Installation |
| **Device Types** | 2 types | 7+ device types |
| **Milestones** | 2 milestones | 4 milestones |

---

## Usage Recommendations

### Use Basic Template When:
- Simple CCTV and access control projects
- Budget constraints
- Quick deployment requirements
- Limited scope projects

### Use Comprehensive Template When:
- Complete building ELV systems
- Multiple integrated systems required
- Professional installation standards
- Long-term maintenance considerations
- Complex network infrastructure needs

Both templates can be customized and extended based on specific project requirements while maintaining the standard cost tracking and project management capabilities.
