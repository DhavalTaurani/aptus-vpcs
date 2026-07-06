/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class OmanFormatSelection extends SelectionField {
    static template = "account_report_template.OmanFormatSelection";
    setup() {
        super.setup();

        const bsAssetKeys = [
            'PPE', 'CWIP', 'IP', 'ROU', 'IA', 'GW', 'LTI', 'DTA', 'LTA', 'DI_BS', 
            'ONCA', 'INV', 'WIP', 'TR', 'CONTR_ASSET', 'RET_REC', 'OTH_REC', 'STI', 
            'CASH_HAND', 'BANK_ACC', 'FD', 'PREP', 'ACCR_INC', 'VAT_REC', 'STA', 'OCA'
        ];

        const bsLiabilityKeys = [
            'SHARE_CAP', 'MCA', 'STR', 'GR', 'FVR', 'ACC_PROFIT_LOSS', 'LTB', 'LL', 
            'ETB', 'DTL', 'LTP', 'ONCL', 'TP', 'CONTR_LIAB', 'RET_PAY', 'ACCR_EXP', 
            'STB', 'CPLTD', 'VAT_PAY', 'WHT_PAY', 'PAYROLL_PAY', 'DIV_PAY', 'OCL'
        ];

        const pnlIncomeKeys = [
            'PS', 'SR', 'CR', 'RI', 'CI', 'II', 'FEG', 'GAD', 'ONI', 'DI_PL', 'MI'
        ];

        const pnlExpenseKeys = [
            'OS', 'PURCHASE', 'DE', 'CS', 'SW', 'SB', 'AE', 'TE', 'RE', 'RM', 
            'VRM', 'OAE', 'PRR', 'AF', 'LPF', 'INS', 'ITSE', 'MSE', 'TC', 'IME', 
            'O_E', 'IL', 'BC', 'UTL', 'CGST', 'DEP', 'ITE', 'IMPV'
        ];

        this.sections = [
            {
                label: _t('Balance Sheet'),
                name: "balance_sheet"
            },
            {
                label: _t('Profit & Loss'),
                name: "profit_and_loss"
            },
        ];

        this.groups = [
            {
                label: _t('Assets'),
                choices: this.choices.filter(x => bsAssetKeys.includes(x.value)),
                section: "balance_sheet",
            },
            {
                label: _t('Liabilities & Equity'),
                choices: this.choices.filter(x => bsLiabilityKeys.includes(x.value)),
                section: "balance_sheet",
            },
            {
                label: _t('Income'),
                choices: this.choices.filter(x => pnlIncomeKeys.includes(x.value)),
                section: "profit_and_loss",
            },
            {
                label: _t('Expenses'),
                choices: this.choices.filter(x => pnlExpenseKeys.includes(x.value)),
                section: "profit_and_loss",
            },
        ];
    }
}

export const omanFormatSelection = {
    ...selectionField,
    component: OmanFormatSelection,
};

registry.category("fields").add("oman_format_selection", omanFormatSelection);
