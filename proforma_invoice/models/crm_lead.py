# In proforma_invoice/models/crm_lead.py

from odoo import fields, models

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    proforma_invoice_count = fields.Integer(
        compute='_compute_proforma_invoice_count',
        string='Proforma Invoices'
    )

    def _compute_proforma_invoice_count(self):
        for lead in self:
            lead.proforma_invoice_count = self.env['proforma.invoice'].search_count([
                ('opportunity_id', '=', lead.id)
            ])

    def action_view_proforma_invoices(self):
        self.ensure_one()
        return {
            'name': 'Proforma Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'proforma.invoice',
            'view_mode': 'tree,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {
                'default_opportunity_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }