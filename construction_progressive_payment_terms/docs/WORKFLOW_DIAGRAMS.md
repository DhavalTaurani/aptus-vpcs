# Workflow Diagrams - Progressive Payment Terms

## Overview

This document provides comprehensive workflow diagrams for the Progressive Payment Terms system, illustrating all implemented processes, state transitions, and integration points.

## Main System Workflow

### Complete Progressive Payment Lifecycle

```mermaid
graph TD
    A[Sale Order Created] --> B{Progressive Payment Term?}
    B -->|No| C[Standard Invoicing Process]
    B -->|Yes| D[Order Confirmation]
    
    D --> E[Auto-Generate Milestones]
    E --> F[Milestone: Draft State]
    
    F --> G{Has Sub-milestones?}
    G -->|No| H[Manual Set Ready]
    G -->|Yes| I[Create Sub-milestones]
    
    I --> J[Sub-milestone: Draft]
    J --> K[Sub-milestone: Ready]
    K --> L[Sub-milestone: Completed]
    L --> M[Sub-milestone: Invoiced]
    
    M --> N{All Sub-milestones Invoiced?}
    N -->|No| O[Parent: Ready State]
    N -->|Yes| P[Parent: Invoiced State]
    
    H --> Q[Milestone: Ready]
    Q --> R[Create Milestone Invoice]
    R --> S[Milestone: Invoiced]
    
    P --> T[Invoice Posted]
    S --> T
    T --> U[Payment Received]
    U --> V[Milestone: Paid]
    
    V --> W{All Milestones Paid?}
    W -->|No| X[Continue Workflow]
    W -->|Yes| Y[Project Payment Complete]
    
    style A fill:#e3f2fd
    style E fill:#f1f8e9
    style P fill:#fff8e1
    style V fill:#e8f5e8
    style Y fill:#ffebee
```

## Milestone State Management

### Parent Milestone States

```mermaid
stateDiagram-v2
    [*] --> Draft: Auto-generated from Payment Terms
    
    Draft --> Ready: Manual Action OR All Sub-milestones Completed
    Ready --> Invoiced: Invoice Created & Posted
    Invoiced --> Paid: Payment Received & Reconciled
    Paid --> [*]: Milestone Complete
    
    Draft --> Cancelled: Project Cancelled
    Ready --> Cancelled: Project Cancelled
    Invoiced --> Cancelled: Project Cancelled
    
    Ready --> Draft: Reset Action
    Invoiced --> Draft: Reset with Invoice Cleanup
    Paid --> Draft: Reset with Payment Removal
    
    note right of Draft
        Initial state: 0% progress
        Can have sub-milestones created
        Automatic generation on order confirm
    end note
    
    note right of Ready
        Ready for invoicing: 50% progress
        All sub-milestones completed (if any)
        Can create invoice
    end note
    
    note right of Invoiced
        Invoice posted: 100% progress
        Dedicated sale order lines created
        Original lines proportionally reduced
    end note
    
    note right of Paid
        Payment received: 100% progress
        Invoice fully reconciled
        Milestone workflow complete
    end note
```

### Sub-milestone States

```mermaid
stateDiagram-v2
    [*] --> Draft: Created with Parent Milestone
    
    Draft --> Ready: Manual Action
    Ready --> Completed: Work Finished
    Completed --> Invoiced: Individual Invoice Created
    
    Invoiced --> [*]: Sub-milestone Complete
    
    Draft --> Cancelled: Project Cancelled
    Ready --> Cancelled: Project Cancelled
    Completed --> Cancelled: Project Cancelled
    
    Ready --> Draft: Reset Action
    Completed --> Draft: Reset Action
    Invoiced --> Draft: Reset with Cleanup
    
    note right of Draft
        Initial state
        Awaiting work start
        Can be set ready manually
    end note
    
    note right of Ready
        Work can begin
        Resources allocated
        Progress tracking starts
    end note
    
    note right of Completed
        Work finished
        Ready for invoicing
        Triggers parent status check
    end note
    
    note right of Invoiced
        Individual invoice created
        Updates parent milestone
        Can trigger parent to invoiced
    end note
```

## Invoice Creation Workflows

### Milestone Invoice Creation Process

```mermaid
sequenceDiagram
    participant User
    participant SaleOrder
    participant Milestone
    participant AccountMove
    participant SaleOrderLine
    participant Invoice
    
    User->>SaleOrder: Click "Create Milestone Invoice"
    SaleOrder->>Milestone: Get Ready Milestones
    Milestone-->>SaleOrder: Return Ready Milestones List
    
    SaleOrder->>AccountMove: create_milestone_invoice(milestone_ids)
    AccountMove->>AccountMove: Validate Milestones Ready
    
    loop For Each Milestone
        AccountMove->>SaleOrderLine: _create_milestone_sale_line()
        SaleOrderLine-->>AccountMove: Return New Sale Line (seq 9999+)
        AccountMove->>AccountMove: _update_original_sale_lines()
        AccountMove->>Invoice: Create Invoice Line
        Invoice-->>AccountMove: Invoice Line Created
    end
    
    AccountMove->>Milestone: Update State to 'Invoiced'
    AccountMove-->>User: Return Created Invoice
    
    User->>Invoice: Post Invoice
    Invoice->>Milestone: Update Payment Status
```

### Sub-milestone Individual Invoicing

```mermaid
sequenceDiagram
    participant User
    participant SubMilestone
    participant TempMilestone
    participant AccountMove
    participant ParentMilestone
    participant Invoice
    
    User->>SubMilestone: action_create_invoice()
    SubMilestone->>SubMilestone: Validate State = 'completed'
    
    SubMilestone->>TempMilestone: Create Temporary Milestone
    TempMilestone-->>SubMilestone: Temp Milestone Created
    
    SubMilestone->>AccountMove: create_milestone_invoice([temp_milestone.id])
    AccountMove->>Invoice: Create Invoice with Dedicated Lines
    Invoice-->>AccountMove: Invoice Created
    
    AccountMove->>ParentMilestone: Link Invoice to Parent
    SubMilestone->>SubMilestone: Set State to 'invoiced'
    SubMilestone->>ParentMilestone: _check_parent_milestone_status()
    
    ParentMilestone->>ParentMilestone: Update Status if All Subs Invoiced
    
    SubMilestone->>TempMilestone: Clean Up Temporary Record
    SubMilestone-->>User: Return Invoice Action
```

## Sale Order Line Management

### Dedicated Line Creation and Management

```mermaid
flowchart TD
    A[Milestone Ready for Invoice] --> B[Create Milestone Invoice]
    B --> C{Has Sub-milestones?}
    
    C -->|No| D[Create Single Milestone Line]
    C -->|Yes| E[Create Lines for Completed Subs]
    
    D --> F[Set Line Sequence = 9999+]
    E --> F
    
    F --> G[Copy Product Info from Original]
    G --> H[Set Price Unit = Milestone Amount]
    H --> I[Link to Invoice Line]
    
    I --> J[Calculate Total Milestone Amount]
    J --> K["Get Original Lines (seq < 9999)"]
    K --> L[Calculate Current Total]
    
    L --> M[Deduct Proportionally]
    M --> N{New Amount > 0?}
    N -->|Yes| O[Update Price Unit]
    N -->|No| P[Set Minimum 0.01]
    
    O --> Q[Maintain Line Visibility]
    P --> Q
    Q --> R[Invoice Creation Complete]
    
    style A fill:#e3f2fd
    style F fill:#f1f8e9
    style M fill:#fff3e0
    style R fill:#e8f5e8
```

### Sale Order Line Restoration Process

```mermaid
flowchart TD
    A[Reset Milestone Action] --> B[Find Milestone Lines]
    B --> C[Filter Lines with seq >= 9999]
    C --> D[Match Milestone/Sub-milestone Names]
    
    D --> E[Calculate Restore Amount]
    E --> F[Sum: price_unit * qty for Milestone Lines]
    
    F --> G[Set Milestone Lines Qty = 0]
    G --> H{Restore Amount > 0?}
    
    H -->|No| I[Reset Complete]
    H -->|Yes| J["Get Original Lines (seq < 9999)"]
    
    J --> K[Calculate Current Total]
    K --> L[Calculate Line Proportions]
    
    L --> M[For Each Original Line]
    M --> N[Calculate Additional Amount]
    N --> O[New Total = Current + Additional]
    O --> P[New Price Unit = Total / Qty]
    P --> Q[Update Line Price Unit]
    
    Q --> R{More Lines?}
    R -->|Yes| M
    R -->|No| S[All Lines Restored]
    
    S --> I
    
    style A fill:#ffebee
    style G fill:#fff3e0
    style Q fill:#e8f5e8
    style I fill:#f1f8e9
```

## Reset and Cleanup Workflows

### Complete Invoice Reset Process

```mermaid
flowchart TD
    A[Reset to Draft Action] --> B{Invoice Exists?}
    B -->|No| C[Reset Milestone State]
    B -->|Yes| D[Restore Sale Order Lines]
    
    D --> E{Invoice State?}
    E -->|Draft| F[Unlink Invoice]
    E -->|Posted| G{Payment State?}
    
    G -->|Not Paid| H[Cancel Invoice]
    G -->|Partial/Paid| I[Remove Payment Entries]
    
    I --> J[Find Payment Moves]
    J --> K[Search Matched Debit/Credit IDs]
    K --> L[Remove Reconciliation]
    L --> M[Cancel Payment Moves]
    M --> N[Unlink Payment Moves]
    N --> H
    
    F --> O[Clear Invoice Reference]
    H --> P[Reset Invoice to Draft]
    P --> O
    
    O --> C
    C --> Q[Reset Milestone Fields]
    Q --> R[Clear Dates and Approvals]
    R --> S[Set State = 'draft']
    S --> T[Reset Complete]
    
    style A fill:#ffebee
    style I fill:#ffcdd2
    style L fill:#ffcdd2
    style T fill:#e8f5e8
```

### Sub-milestone Reset with Parent Updates

```mermaid
sequenceDiagram
    participant User
    participant SubMilestone
    participant SaleOrderLines
    participant ParentInvoice
    participant ParentMilestone
    
    User->>SubMilestone: action_reset_to_draft()
    
    SubMilestone->>SaleOrderLines: _restore_sub_milestone_sale_lines()
    SaleOrderLines->>SaleOrderLines: Find Sub-milestone Lines
    SaleOrderLines->>SaleOrderLines: Set Qty = 0, Restore Original
    SaleOrderLines-->>SubMilestone: Lines Restored
    
    SubMilestone->>ParentInvoice: Check Parent Invoice
    alt Invoice Exists and Posted
        SubMilestone->>ParentInvoice: Handle Payment Cleanup
        ParentInvoice->>ParentInvoice: Remove Payments if Paid
        ParentInvoice->>ParentInvoice: Cancel and Reset to Draft
    end
    
    SubMilestone->>SubMilestone: Reset State to Draft
    SubMilestone->>ParentMilestone: _check_parent_milestone_status()
    
    ParentMilestone->>ParentMilestone: Check All Sub-milestone States
    alt Not All Invoiced
        ParentMilestone->>ParentMilestone: Set Parent to Ready
    end
    
    ParentMilestone->>ParentMilestone: _compute_progress_percentage()
    ParentMilestone-->>User: Reset Complete
```

## Progress Calculation Workflows

### Smart Progress Calculation Logic

```mermaid
flowchart TD
    A[Calculate Progress] --> B{Has Sub-milestones?}
    
    B -->|No| C[State-based Calculation]
    B -->|Yes| D[Sub-milestone Based Calculation]
    
    C --> E{Milestone State}
    E -->|Draft| F[Progress = 0%]
    E -->|Ready| G[Progress = 50%]
    E -->|Invoiced| H[Progress = 100%]
    E -->|Paid| I[Progress = 100%]
    
    D --> J[Count Total Sub-milestones]
    J --> K[Count Completed + Invoiced Subs]
    K --> L[Progress = Completed/Total * 100]
    
    F --> M[Update Progress Field]
    G --> M
    H --> M
    I --> M
    L --> M
    
    M --> N[Trigger Parent Update]
    N --> O[Recalculate Sale Order Progress]
    O --> P[Update Dashboard Indicators]
    
    style A fill:#e3f2fd
    style D fill:#f1f8e9
    style L fill:#fff8e1
    style P fill:#e8f5e8
```

### Sale Order Progress Aggregation

```mermaid
flowchart TD
    A[Sale Order Progress Calculation] --> B[Get All Milestones]
    B --> C[Calculate Total Amount]
    C --> D[Initialize Weighted Progress = 0]
    
    D --> E[For Each Milestone]
    E --> F{Has Sub-milestones?}
    
    F -->|No| G[Use Milestone Progress %]
    F -->|Yes| H[Calculate Sub-milestone Progress]
    
    H --> I[Count Completed + Invoiced Subs]
    I --> J[Sub Progress = Count/Total * 100]
    J --> K[Weight by Milestone Amount]
    
    G --> L[Weight by Milestone Amount]
    K --> M[Add to Weighted Progress]
    L --> M
    
    M --> N{More Milestones?}
    N -->|Yes| E
    N -->|No| O[Final Progress = Weighted/Total]
    
    O --> P[Update Sale Order Progress]
    P --> Q[Update UI Indicators]
    
    style A fill:#e3f2fd
    style H fill:#f1f8e9
    style O fill:#fff8e1
    style Q fill:#e8f5e8
```

## Payment Amount Tracking

### Real-time Payment Calculation

```mermaid
flowchart TD
    A[Payment Amount Calculation] --> B[Get All Milestones]
    B --> C[Initialize Amounts]
    C --> D[Total = 0, Invoiced = 0, Paid = 0]
    
    D --> E[For Each Milestone]
    E --> F[Add to Total Amount]
    F --> G{Has Sub-milestones?}
    
    G -->|Yes| H[Get Invoiced Sub-milestones]
    G -->|No| I{Milestone State?}
    
    H --> J[Add Sub-milestone Amounts to Invoiced]
    I -->|Invoiced/Paid| K[Add Milestone Amount to Invoiced]
    I -->|Other| L[Skip Invoiced Calculation]
    
    J --> M[Check Milestone Invoice]
    K --> M
    L --> N[Next Milestone]
    
    M --> O{Invoice Exists & Posted?}
    O -->|No| N
    O -->|Yes| P[Calculate Paid Amount]
    
    P --> Q[Paid = Invoice Total - Residual]
    Q --> R{Paid > 0?}
    R -->|Yes| S[Add to Total Paid]
    R -->|No| N
    
    S --> N
    N --> T{More Milestones?}
    T -->|Yes| E
    T -->|No| U[Update Sale Order Fields]
    
    U --> V[Set Total/Invoiced/Paid Amounts]
    V --> W[Trigger UI Updates]
    
    style A fill:#e3f2fd
    style P fill:#f1f8e9
    style V fill:#e8f5e8
```

## Integration Workflows

### Accounting Integration Flow

```mermaid
sequenceDiagram
    participant Milestone
    participant Invoice
    participant JournalEntry
    participant AnalyticAccount
    participant Payment
    participant Reconciliation
    
    Milestone->>Invoice: Create Milestone Invoice
    Invoice->>JournalEntry: Generate Journal Entry
    JournalEntry->>AnalyticAccount: Allocate to Project Analytics
    
    Invoice->>Invoice: Post Invoice
    Invoice->>Milestone: Update State to 'invoiced'
    
    Payment->>Invoice: Register Payment
    Payment->>JournalEntry: Create Payment Entry
    JournalEntry->>Reconciliation: Reconcile with Invoice
    
    Reconciliation->>Invoice: Update Payment State
    Invoice->>Milestone: Update State to 'paid'
    Milestone->>Milestone: Set Progress = 100%
```

### Project Management Integration

```mermaid
flowchart TD
    A[Project Task Completion] --> B[Update Milestone Progress]
    B --> C[Check Milestone Criteria]
    C --> D{Criteria Met?}
    
    D -->|No| E[Continue Work]
    D -->|Yes| F[Set Milestone Ready]
    
    F --> G[Create Invoice]
    G --> H[Update Project Financials]
    H --> I[Update Resource Allocation]
    I --> J[Trigger Next Phase]
    
    E --> K[Update Progress Tracking]
    K --> L[Generate Progress Reports]
    
    style A fill:#e3f2fd
    style F fill:#f1f8e9
    style G fill:#fff8e1
    style J fill:#e8f5e8
```

## Error Handling Workflows

### Validation and Error Recovery

```mermaid
flowchart TD
    A[User Action] --> B[Validate Prerequisites]
    B --> C{Validation Passed?}
    
    C -->|No| D[Generate Error Message]
    C -->|Yes| E[Execute Action]
    
    D --> F[Display User-Friendly Error]
    F --> G[Provide Corrective Actions]
    G --> H[Log Error Details]
    H --> I[Return to Previous State]
    
    E --> J{Action Successful?}
    J -->|No| K[Rollback Changes]
    J -->|Yes| L[Update State]
    
    K --> M[Log Failure Details]
    M --> N[Notify User of Failure]
    N --> O[Provide Recovery Options]
    
    L --> P[Trigger Dependent Updates]
    P --> Q[Notify Success]
    Q --> R[Update UI]
    
    style D fill:#ffebee
    style K fill:#ffcdd2
    style L fill:#e8f5e8
    style R fill:#f1f8e9
```

## Performance Optimization Workflows

### Efficient Data Processing

```mermaid
flowchart TD
    A[Large Dataset Operation] --> B[Batch Processing]
    B --> C[Process in Chunks]
    C --> D[Use Efficient Queries]
    
    D --> E[Minimize Database Calls]
    E --> F[Use Computed Fields Wisely]
    F --> G[Cache Frequently Used Data]
    
    G --> H[Monitor Performance]
    H --> I{Performance OK?}
    
    I -->|No| J[Optimize Queries]
    I -->|Yes| K[Continue Processing]
    
    J --> L[Add Database Indexes]
    L --> M[Refactor Slow Operations]
    M --> H
    
    K --> N[Complete Operation]
    N --> O[Update Progress Indicators]
    
    style A fill:#e3f2fd
    style D fill:#f1f8e9
    style J fill:#fff3e0
    style N fill:#e8f5e8
```

These workflow diagrams provide comprehensive visual documentation of all implemented processes in the Progressive Payment Terms system, covering normal operations, error handling, and optimization strategies.