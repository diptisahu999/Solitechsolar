from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    proforma_invoice_ids = fields.One2many('proforma.invoice', 'sale_order_id', string='Proforma Invoices')
    proforma_invoice_count = fields.Integer(string='Proforma Count', compute='_compute_proforma_invoice_count')

    @api.depends('proforma_invoice_ids')
    def _compute_proforma_invoice_count(self):
        for order in self:
            order.proforma_invoice_count = len(order.proforma_invoice_ids)

    def action_view_proforma_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('proforma_invoice.action_proforma_invoice')
        action['domain'] = [('id', 'in', self.proforma_invoice_ids.ids)]
        return action

    def action_create_proforma_invoice(self):
        self.ensure_one()
        proforma_lines = []
        for line in self.order_line:
            # Skip sections and notes
            if line.display_type:
                continue
            proforma_lines.append((0, 0, {
                'sale_line_id': line.id,  # <-- ADD THIS
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'discount': line.discount,
            }))

        proforma = self.env['proforma.invoice'].create({
            'sale_order_id': self.id,  # <-- ADD THIS
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'user_id': self.user_id.id,
            'po_number': self.client_order_ref,
            'invoice_payment_term_id': self.payment_term_id.id,
            'line_ids': proforma_lines,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Proforma Invoice'),
            'res_model': 'proforma.invoice',
            'res_id': proforma.id,
            'view_mode': 'form',
        }