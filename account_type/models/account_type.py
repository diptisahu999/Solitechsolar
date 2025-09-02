from odoo import api, fields, models, _


class AccountAccount(models.Model):
    _inherit = 'account.account'
    _description = 'Account Type'


    internal_group = fields.Selection(
        selection_add=[
            ('plincome', 'Incomes (P/L Account)'),
            ('plexpenditures', 'P/L Expenditures'),
            ('totalplexpenditures', 'Total of Expenditures (P/L)'),
            ('expenditures', 'Expenditures'),
            ('totalasset', 'Total of Assets'),
            ('totalliability', 'Total of Liabilities'),
            ('totalincomestrading', 'Total of Incomes (Trading)'),
            ('totalplincomes', 'Total of Incomes (P/L)'),
            ('totalexpenditures', 'Total of Expenditures (Trading)'),
        ],
    )

    account_type = fields.Selection(
        selection_add=[
            ("asset_investments", "Investments"),
            ("asset_deposits_loans_advances", "Deposits,Loans & Advances"),
             ("asset_misc_expenditures_assets", " Misc.Expenditures (Assets)"),
             ("asset_inter_branch_accounts_assets", "Inter-Branch Accounts (Assets)"),

            ("liability_capital_accounts", "Capital Accounts"),
            ("liability_reserves_surplus", "Reserves & Surplus"),
            ("liability_secured_loans", "Secured Loans"),
            ("liability_unsecured_loans", "Unsecured Loans"),
            ("liability_current_liabilities", "Current Liabilities"),
            ("liability_duties_taxes", "Duties & Taxes"),
            ("liability_provisions", "Provisions"),
            ("liability_bank_overdraft", "Bank OverDraft (Cash Credit A/Cs)"),
            ("liability_advances_customers", "Advances from Customers"),
            ("liability_salary_payable", "Salary Payable"),
            ("liability_profit_loss_liabilities", "Profit & Loss Account (Liabilities)"),
            ("liability_inter_branch_accounts_liabilities", "Inter-Branch Accounts (Liabilities)"),
            ("liability_suspense_account", "Suspense Account"),

            ("income_sales", "Sales"),
            ("income_closing_stock_trading", "Closing Stock (Trading)"),
            ("income_trading_account", "Incomes (Trading Account)"),


            ("plincome_pl_account", "Incomes (P/L Account)"),
            ("plincome_net_loss_transferred_to_bs", "Net Loss transferred to BS"),

            ("expenditures_trading_opening_stock", "Opening Stock (Trading A/C)"),
            ("expenditures_trading_purchase", "Purchase"),
            ("expenditures_trading_direct_expenses_mfg", "Direct Expenses (Mfg/Trading Exp)"),


            ("plexpenditures_indirect_expenses_p_l_account", "Indirect Expenses (P/L Account)"),
            ("plexpenditures_net_profit_transferred_to_bs", "Net Profit transferred to BS"),
        ],
        ondelete={
            "asset_investments": "cascade",
            "asset_deposits_loans_advances": "cascade",
            "asset_misc_expenditures_assets": "cascade",
            "asset_inter_branch_accounts_assets"   : "cascade",
            "liability_capital_accounts": "cascade",
            "liability_reserves_surplus": "cascade",
            "liability_secured_loans": "cascade",
            "liability_unsecured_loans": "cascade",
            "liability_current_liabilities": "cascade",
            "liability_duties_taxes": "cascade",
            "liability_provisions": "cascade",
            "liability_bank_overdraft": "cascade",
            "liability_advances_customers": "cascade",
            "liability_salary_payable": "cascade",
            "liability_profit_loss_liabilities": "cascade",
            "liability_inter_branch_accounts_liabilities": "cascade",
            "liability_suspense_account": "cascade",
            "income_sales": "cascade",
            "income_closing_stock_trading": "cascade",
            "income_trading_account": "cascade",
            "plincome_pl_account": "cascade",
            "plincome_net_loss_transferred_to_bs": "cascade",
            "expenditures_trading_opening_stock": "cascade",
            "expenditures_trading_purchase": "cascade",
            "expenditures_trading_direct_expenses_mfg": "cascade",
            "plexpenditures_indirect_expenses_p_l_account": "cascade",
            "plexpenditures_net_profit_transferred_to_bs": "cascade",
            }
    )