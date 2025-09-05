from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_proforma_invoice(self):
        self.ensure_one()
        proforma_lines = []
        for line in self.order_line:
            proforma_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'discount': line.discount,
                # Copy other custom fields from SO line to PI line here
            }))

        proforma = self.env['proforma.invoice'].create({
            'partner_id': self.partner_invoice_id.id,
            'user_id': self.user_id.id,
            'po_number': self.client_order_ref,
            'line_ids': proforma_lines,
            # Copy other custom fields from SO to PI here
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Proforma Invoice'),
            'res_model': 'proforma.invoice',
            'res_id': proforma.id,
            'view_mode': 'form',
        }