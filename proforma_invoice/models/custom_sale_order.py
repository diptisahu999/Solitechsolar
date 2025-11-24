from odoo import models, fields, api, _

class CustomSaleOrder(models.Model):
    _name = "custom.sale.order"
    _description = "Confirmed Sales Order (Separate Doc)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='SO Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    origin_quotation_id = fields.Many2one('sale.order', string='Source Quotation', readonly=True)
    
    # --- Contact Info ---
    partner_id = fields.Many2one('res.partner', string='Customer')
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address')
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address')
    
    date_order = fields.Datetime(string='Order Date')
    validity_date = fields.Date(string='Expiration')
    user_id = fields.Many2one('res.users', string='Salesperson')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    # --- Business Terms (Stored as Text now) ---
    client_order_ref = fields.Char(string='Customer Reference')
    payment_term_name = fields.Char(string='Payment Terms')      # Changed from ID to Name
    fiscal_position_name = fields.Char(string='Fiscal Position') # Changed from ID to Name
    incoterm_name = fields.Char(string='Incoterm')               # Changed from ID to Name
    incoterm_location = fields.Char(string='Incoterm Location')
    
    # --- Lines & Totals ---
    line_ids = fields.One2many('custom.sale.order.line', 'order_id', string='Order Lines')
    note = fields.Html(string='Terms and Conditions')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount')
    amount_tax = fields.Monetary(string='Taxes')
    amount_total = fields.Monetary(string='Total')

    # --- Smart Buttons ---
    proforma_ids = fields.One2many('proforma.invoice', 'custom_so_id', string='Proforma Invoices')
    proforma_count = fields.Integer(compute='_compute_proforma_count')

    @api.depends('proforma_ids')
    def _compute_proforma_count(self):
        for rec in self:
            rec.proforma_count = len(rec.proforma_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.sale.order') or _('New')
        return super(CustomSaleOrder, self).create(vals_list)

    def action_view_source_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source Quotation'),
            'res_model': 'sale.order',
            'res_id': self.origin_quotation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_proformas(self):
        self.ensure_one()
        return {
            'name': _('Proforma Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'proforma.invoice',
            'domain': [('custom_so_id', '=', self.id)],
            'context': {'default_custom_so_id': self.id},
            'view_mode': 'tree,form',
        }
        
    def action_create_proforma_from_custom_so(self):
        """ Launches the Wizard to ask for PO Number before creating PI """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Proforma Invoice'),
            'res_model': 'proforma.invoice.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_custom_sale_order_id': self.id,
                'default_sale_order_id': self.origin_quotation_id.id 
            }
        }

class CustomSaleOrderLine(models.Model):
    _name = "custom.sale.order.line"
    _description = "Custom SO Line"

    order_id = fields.Many2one('custom.sale.order', string='Order Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Text(string='Description')
    product_uom_qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    
    # Tax stored as simple text (e.g. "GST 18%, Cess 1%")
    tax_names = fields.Char(string='Taxes') 
    
    price_subtotal = fields.Monetary(string='Subtotal')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    
    wattage = fields.Float(string="Wattage (Wp)")
    unit_price_per_nos = fields.Monetary(string="Unit Price (₹/Nos)")