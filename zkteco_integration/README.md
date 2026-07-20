# ZKTeco BioTime Attendance Integration for Odoo 19

This module seamlessly integrates Odoo 19 HR Attendance with ZKTeco BioTime biometric devices. It synchronizes employee check-ins and check-outs securely via the ZKTeco BioTime API.

## Features

*   **API Configuration:** Securely connect your Odoo instance to your ZKTeco BioTime API via the Settings menu.
*   **Granular Security:** 
    *   **ZKTeco Manager:** Has full access to configure API credentials, test connections, and view the automated Cron job.
    *   **ZKTeco User:** Can only execute employee mapping tools (has no access to sensitive API settings).
*   **Safe Employee Mapping:** Includes a secure Server Action (`Fetch ZKTeco Punch ID`) that strictly maps ZKTeco IDs to existing Odoo employees based on Email or Name. It **prevents auto-creation** of random employees, ensuring your Odoo database remains perfectly clean.
*   **Selected-Record Execution:** The mapping tool only processes the exact Odoo employees you select in the list view, giving you total control.
*   **Automated Attendance Sync:** Includes an automated Scheduled Action (Cron) that pulls check-in and check-out logs and writes them securely into Odoo's native HR Attendance app.

## Setup & Configuration

1. Log in to Odoo as an Administrator.
2. Ensure you have the **ZKTeco Manager** access right assigned to your user account.
3. Go to **Settings -> ZKTeco Attendance**.
4. Enter your **API Base URL**, **Username**, and **Password**.
5. Click **Test Connection** to automatically fetch your secure authentication token.
6. To configure the automatic sync schedule, go to **Settings -> Technical -> Scheduled Actions** and search for `ZKTeco`. 

## How to Map Employees

Before attendance can be synced, Odoo employees must be linked to ZKTeco via their `Punch ID`.

1. Go to the **Employees** app.
2. Switch to the **List View**.
3. Select the checkboxes next to the employees you want to link.
4. Click the **Action** gear icon at the top of the list.
5. Click **Fetch ZKTeco Punch ID**.

The system will connect to ZKTeco, find matches based on Email or Name, and update the Punch ID securely.

## Technical Notes

*   **Odoo Version:** 19.0
*   **Dependencies:** `hr`, `hr_attendance`
*   **External Python Libraries:** `requests`, `python-dateutil`
