from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProformaInvoicePOWizard(models.TransientModel):
    _name = "proforma.invoice.po.wizard"
    _description = "PO Number Wizard for Proforma Invoice Creation"

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    custom_sale_order_id = fields.Many2one('custom.sale.order', string='Confirmed SO') 
    
    po_number = fields.Char(string='PO Number', required=True, help='Enter the Purchase Order Number')

    @api.model
    def default_get(self, fields):
        res = super(ProformaInvoicePOWizard, self).default_get(fields)
        # Auto-fill PO Number if available in the source document
        if res.get('sale_order_id'):
            so = self.env['sale.order'].browse(res['sale_order_id'])
            if so.client_order_ref:
                res['po_number'] = so.client_order_ref
        
        if res.get('custom_sale_order_id'):
            cso = self.env['custom.sale.order'].browse(res['custom_sale_order_id'])
            if cso.client_order_ref:
                res['po_number'] = cso.client_order_ref
        return res

    def action_create_proforma(self):
        self.ensure_one()
        if not self.po_number or not self.po_number.strip():
            raise ValidationError(_('PO Number is required.'))

        # CASE A: From Confirmed SO (Custom SO)
        if self.custom_sale_order_id:
            # 1. Create PI using source quotation ID logic (reuses existing copy logic)
            # We use the ID of the original quotation to copy product lines correctly
            pi = self.env['proforma.invoice'].create_from_sale_order(self.custom_sale_order_id.origin_quotation_id.id)
            
            # 2. Link PI to the Custom SO (The Contract) and set PO
            pi.write({
                'custom_so_id': self.custom_sale_order_id.id,
                'po_number': self.po_number.strip()
            })
            
            # 3. Open the PI
            return {
                'type': 'ir.actions.act_window',
                'name': _('Proforma Invoice'),
                'res_model': 'proforma.invoice',
                'res_id': pi.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # CASE B: From Draft Quotation (Standard Sale Order)
        elif self.sale_order_id:
            pi_model = self.env['proforma.invoice']
            pi = pi_model.create_from_sale_order(self.sale_order_id)
            pi.po_number = self.po_number.strip()
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Proforma Invoice'),
                'res_model': 'proforma.invoice',
                'res_id': pi.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        return {'type': 'ir.actions.act_window_close'}