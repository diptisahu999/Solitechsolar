from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProformaInvoicePOWizard(models.TransientModel):
    _name = "proforma.invoice.po.wizard"
    _description = "PO Number Wizard for Proforma Invoice Creation"

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    po_number = fields.Char(string='PO Number', required=True, help='Enter the Purchase Order Number')

    def action_create_proforma(self):
        """Create Proforma Invoice with the entered PO Number and open it."""
        self.ensure_one()
        
        if not self.po_number or not self.po_number.strip():
            raise ValidationError(_('PO Number is required.'))

        so = self.sale_order_id
        if not so or not so.exists():
            raise ValidationError(_('Sale Order not found.'))

        pi_model = self.env['proforma.invoice']
        pi = pi_model.create_from_sale_order(so)
        
        # Set PO Number on the created PI
        pi.po_number = self.po_number.strip()

        # Open the created PI in form view
        action = self.env.ref('proforma_invoice.action_proforma_invoice_form', False)
        if not action:
            # Fallback to a generic window action
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'proforma.invoice',
                'view_mode': 'form',
                'res_id': pi.id,
                'target': 'current',
            }
        
        # If action exists, update it to open the new record
        result = action.read()[0]
        result.update({'res_id': pi.id, 'views': [(self.env.ref('proforma_invoice.view_proforma_invoice_form').id, 'form')]})
        return result
