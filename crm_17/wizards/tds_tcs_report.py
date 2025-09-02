from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta,date
from ...crm_17 import common_file

class TdsTcsReport(models.TransientModel):
    _name = 'tds.tcs.report'
    _description = "Tds/Tcs Report"

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    partner_ids = fields.Many2many('res.partner',string="Vendors")
    company_id = fields.Many2one("res.company", string="Company",required=True, default=lambda self: self.env.company.id)    

    @api.model
    def default_get(self, fields):
        res = super(TdsTcsReport, self).default_get(fields)
        fy_start_date,fy_end_date = common_file.get_fy_year(str(date.today()))
        res['from_date'] = fy_start_date
        res['to_date'] = fy_end_date
        return res 

    def generate_pdf_vals(self):
        domain = [('move_type', '=', 'in_invoice'),('state', '=', 'posted'),('tds_amt', '>', 0)]
        if self.from_date:
            domain.append(('date', '>=', self.from_date))
        if self.to_date:
            domain.append(('date', '<=', self.to_date))
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids)) 

        invoice_rec = self.env['account.move'].sudo().search(domain)
        tds_data = {}
        for res in invoice_rec:
            tds_account_name = res.partner_id.tds_sec.name if res.partner_id.tds_sec else 'Unknown'
            if tds_account_name not in tds_data:
                tds_data[tds_account_name] = []
            
            tds_data[tds_account_name].append({
                'partner': res.partner_id.name,
                'pan_no': res.partner_id.l10n_in_pan if res.partner_id.l10n_in_pan else '',
                'bill_no': res.name,
                'amount': res.amount_total,
                'date': res.date.strftime('%d-%m-%Y') if res.date else '',
                'pur_amount': res.purchase_id.amount_total if res.purchase_id else res.amount_total,
                'tds_amt': res.tds_amt,
            })

        main = {
            'from_date': self.from_date.strftime('%d-%m-%Y'),
            'to_date': self.to_date.strftime('%d-%m-%Y'),
            'company_name': self.company_id.name,
            'tds_data': tds_data,
        }
        return [main]
    
    def generate_pdf(self):
        return self.env.ref('crm_17.action_tds_tcs_pdf_report').report_action(self)
