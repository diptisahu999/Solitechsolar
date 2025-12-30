from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    proforma_invoice_ids = fields.One2many('proforma.invoice', 'sale_order_id', string='Proforma Invoices')
    proforma_invoice_count = fields.Integer(string='Proforma Count', compute='_compute_proforma_invoice_count')
    custom_so_id = fields.Many2one('custom.sale.order', string="Confirmed SO Doc", readonly=True, copy=False)

    def action_confirm_custom_so(self):
        for order in self:
            partner = order.partner_id
            
            # Check if customer is a Company (not Individual)
            if partner.company_type != 'company':
                raise UserError(_(
                    "Invalid Customer Type\n"
                    "Only Company customers can confirm Sale Orders.\n\n"
                    "Please go to Contact page and change the customer type from 'Individual' to 'Company' before confirming."
                ))
            
            if partner.is_company:
                if not partner.vat:
                    raise UserError(_(
                        "Invalid Operation\n"
                        "GST Number is required.\n\n"
                        "Please update the customer's GST No before confirming the quotation."
                    ))

            if not order.client_order_ref:
                raise UserError(_(
                    "Missing PO Number\n"
                    "Please enter the Customer Reference (PO Number) on the Quotation "
                    "before confirming the Sale Order."
                ))

            # --- NEW: Calculate Tax Breakdown for Snapshot ---
            cgst = 0.0
            sgst = 0.0
            igst = 0.0
            
            for line in order.order_line:
                if line.display_type: continue
                
                # Compute taxes for this line
                base_price = line.unit_price_per_nos if line.wattage else line.price_unit
                price = base_price * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, order.currency_id, line.product_uom_qty, product=line.product_id, partner=order.partner_id)
                
                for t in taxes.get('taxes', []):
                    tname = (t.get('name') or '').upper()
                    amt = t.get('amount', 0.0)
                    if 'CGST' in tname:
                        cgst += amt
                    elif 'SGST' in tname:
                        sgst += amt
                    elif 'IGST' in tname:
                        igst += amt

            so_vals = {
                'origin_quotation_id': order.id,
                'partner_id': order.partner_id.id,
                'partner_invoice_id': order.partner_invoice_id.id,
                'partner_shipping_id': order.partner_shipping_id.id,
                'date_order': fields.Datetime.now(),
                'validity_date': order.validity_date,
                'user_id': order.user_id.id,
                'company_id': order.company_id.id,
                'client_order_ref': order.client_order_ref,
                
                # FIX: Safety check. If ID is False, return '' instead of crashing on .name
                'payment_term_name': order.payment_term_id.name if order.payment_term_id else '',
                'fiscal_position_name': order.fiscal_position_id.name if order.fiscal_position_id else '',
                'incoterm_name': order.incoterm.name if order.incoterm else '',
                'incoterm_location': order.incoterm_location,
                
                'note': order.note,
                'amount_untaxed': order.amount_untaxed,
                'amount_tax': order.amount_tax,
                'amount_total': order.amount_total,
                
                # --- Store the breakdown ---
                'cgst_amount': cgst,
                'sgst_amount': sgst,
                'igst_amount': igst,

                # --- NEW: GST & Supply ---
                'l10n_in_gst_treatment': order.l10n_in_gst_treatment,
                'place_of_supply': order.place_of_supply.id if order.place_of_supply else False,
            }

            custom_so = self.env['custom.sale.order'].create(so_vals)

            line_vals_list = []
            for line in order.order_line:
                if line.display_type: continue 
                
                # Join tax names into a string "GST 18%, Tax 5%"
                tax_str = ", ".join(line.tax_id.mapped('name'))
                
                line_vals_list.append({
                    'order_id': custom_so.id,
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'tax_names': tax_str, # Store text
                    'price_subtotal': line.price_subtotal,
                    'wattage': line.wattage,
                    'unit_price_per_nos': line.unit_price_per_nos,
                })
            
            self.env['custom.sale.order.line'].create(line_vals_list)
            order.custom_so_id = custom_so.id
            order.state = 'sale'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirmed Sale Order'),
            'res_model': 'custom.sale.order',
            'res_id': self.custom_so_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.depends('proforma_invoice_ids')
    def _compute_proforma_invoice_count(self):
        for order in self:
            order.proforma_invoice_count = len(order.proforma_invoice_ids)

    def action_view_custom_so(self):
        """ Open the specific Confirmed SO record in Form View """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirmed Sale Order'),
            'res_model': 'custom.sale.order',
            'res_id': self.custom_so_id.id,  # <--- The specific ID to open
            'view_mode': 'form',             # <--- Force Form View
            'target': 'current',
        }

    def action_view_proforma_invoices(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('proforma_invoice.action_proforma_invoice')
        action['domain'] = [('id', 'in', self.proforma_invoice_ids.ids)]
        return action

    def action_create_proforma_invoice(self):
        self.ensure_one()
        proforma_lines = []
        for line in self.order_line:
            if line.display_type:
                continue
            proforma_lines.append((0, 0, {
                'sale_line_id': line.id,  
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'discount': line.discount,
            }))

        proforma = self.env['proforma.invoice'].create({
            'sale_order_id': self.id,  
            'opportunity_id': self.opportunity_id.id,
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