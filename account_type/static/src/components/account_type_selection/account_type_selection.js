/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

export class AccountTypeSelection extends SelectionField {
    get hierarchyOptions() {
        const opts = this.options;
        return [
            { name: _t('Balance Sheet') },
            { name: _t('Assets'), children: opts.filter(x => x[0] && x[0].startsWith('asset')) },
            { name: _t('Total of Assets'), children: opts.filter(x => x[0] && x[0].startsWith('totalasset')) },
            { name: _t('Liabilities'), children: opts.filter(x => x[0] && x[0].startsWith('liability')) },
            { name: _t('Total of Liabilities'), children: opts.filter(x => x[0] && x[0].startsWith('totalliability')) },
            { name: _t('Equity'), children: opts.filter(x => x[0] && x[0].startsWith('equity')) },
            { name: _t('Profit & Loss') },
            { name: _t('Incomes (Trading)'), children: opts.filter(x => x[0] && x[0].startsWith('income')) },
            { name: _t('Total of Incomes (Trading)'), children: opts.filter(x => x[0] && x[0].startsWith('totalincomestrading')) },
            { name: _t('Incomes (P/L))'), children: opts.filter(x => x[0] && x[0].startsWith('plincome')) },
            { name: _t('Total of Incomes (P/L)'), children: opts.filter(x => x[0] && x[0].startsWith('totalplincomes')) },

            { name: _t('Expense'), children: opts.filter(x => x[0] && x[0].startsWith('expense')) },

            { name: _t('Expenditures (Trading)'), children: opts.filter(x => x[0] && x[0].startsWith('expenditures_trading')) },
            { name: _t('Total of Expenditures (Trading)'), children: opts.filter(x => x[0] && x[0].startsWith('totalexpenditures_trading')) },
            { name: _t('Expenditures (P/L)'), children: opts.filter(x => x[0] && x[0].startsWith('plexpenditures')) },
            { name: _t('Total of Expenditures (P/L)'), children: opts.filter(x => x[0] && x[0].startsWith('totalplexpenditures')) },
            { name: _t('Other'), children: opts.filter(x => x[0] && x[0] === 'off_balance') },
        ];
    }
}
AccountTypeSelection.template = "account.AccountTypeSelection";

export const accountTypeSelection = {
    ...selectionField,
    component: AccountTypeSelection,
};

registry.category("fields").add("custonm_account_type_selection", accountTypeSelection);
