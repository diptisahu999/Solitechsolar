from odoo import models, fields, api, _
from datetime import date
from num2words import num2words
import re
from odoo.exceptions import UserError, ValidationError
import math

class ProformaInvoice(models.Model):
    _name = "proforma.invoice"
    _description = "Proforma Invoice (Non-Accounting)"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # --- Replicating the structure of account.move ---
    name = fields.Char(string='Number', readonly=True, copy=False, default='/', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Place of Supply (Delivery Address)') # NEW FIELD
    l10n_in_gst_treatment = fields.Selection([
        ('registered', 'Registered Business'),
        ('unregistered', 'Unregistered Business'),
        ('consumer', 'Consumer'),
        ('overseas', 'Overseas'),
        ('special_economic_zone', 'Special Economic Zone'),
        ('deemed_export', 'Deemed Export'),
    ], string="GST Treatment") # NEW FIELD

    invoice_date = fields.Date(string='Invoice Date', index=True, copy=False, default=fields.Date.context_today)
    invoice_date_due = fields.Date(string='Due Date') # NEW FIELD
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms') # NEW FIELD
    
    pi_chr = fields.Char(string='PI Number', store=True, readonly=True)
    pi_date = fields.Date(string='PI Date', store=True, readonly=True)
    po_number = fields.Char(string='PO Number')
    po_date = fields.Date(string='Order Date')

    state = fields.Selection([
        ('draft', 'PI Draft'),
        ('discount_approval', 'Discount Approval'),
        ('posted', 'PI Confirm'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    line_ids = fields.One2many('proforma.invoice.line', 'proforma_id', string='Invoice Lines')

    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amounts')
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amounts')
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts')

    is_manager = fields.Boolean(string='Manager', default=False)
    project_id = fields.Many2one('project.project', string="Project", tracking=True)
    sample_type = fields.Selection([('spare_parts', 'Spare Parts'), ('sample', 'Sample'), ('gift', 'Gift')], string='Sample/Gift/Spare Parts')
    source_id = fields.Many2one('utm.source', string='Source') # NEW FIELD

    narration = fields.Html(string="Terms and Conditions")

    @api.depends('line_ids.price_subtotal', 'line_ids.price_total')
    def _compute_amounts(self):
        for pi in self:
            pi.amount_untaxed = sum(pi.line_ids.mapped('price_subtotal'))
            pi.amount_total = sum(pi.line_ids.mapped('price_total'))
            pi.amount_tax = pi.amount_total - pi.amount_untaxed
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_shipping_id = self.partner_id.search([('parent_id', '=', self.partner_id.id), ('type', '=', 'delivery')], limit=1) or self.partner_id
            self.invoice_payment_term_id = self.partner_id.property_payment_term_id

    # NEW METHOD: For the "View Customer" button
    def action_open_partner_view(self):
        self.ensure_one()
        partner = self.partner_id
        if partner.parent_id:
            partner = partner.parent_id
        return {
            'name': _("Customer"),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': partner.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                # Using Odoo sequence is better, but replicating your logic
                last_pi = self.search([], order='id desc', limit=1)
                new_id = (last_pi.id or 0) + 1
                vals['name'] = f'PI/{date.today().year}/{new_id:05d}'
                vals['pi_chr'] = vals['name']
                vals['pi_date'] = date.today()
        return super().create(vals_list)

    def button_draft(self):
        self.write({'state': 'draft', 'is_manager': False})

    def button_cancel(self):
        self.write({'state': 'cancel'})

    def action_discount_user(self):
        self.state = 'discount_approval'

    def action_discount_manager(self):
        self.write({'is_manager': True, 'state': 'draft'})

    def action_post(self):
        self.write({'state': 'posted'})


class ProformaInvoiceLine(models.Model):
    _name = "proforma.invoice.line"
    _description = "Proforma Invoice Line (Non-Accounting)"

    proforma_id = fields.Many2one('proforma.invoice', string='Proforma', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description', required=True)
    product_type = fields.Selection(related='product_id.detailed_type', string="Product Type") # NEW FIELD
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes') 
    price_subtotal = fields.Monetary(string='Tax excl.', compute='_compute_amounts', store=True)
    price_total = fields.Monetary(string='Total', compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', related='proforma_id.currency_id')
    
    inch_feet_type = fields.Selection([('inch', 'Inch'), ('feet', 'Feet'), ('mm', 'MM'), ('tile', 'Tile'), ('basic', 'Basic')], 'Inch/Feet', default="basic")
    discount = fields.Float(string='Discount (%)')
    actual_price = fields.Float(string="Actual Price")
    diff_per = fields.Float(string="Difference (%)", compute="_compute_diff")
    remarks = fields.Char(string='Remarks')

    @api.depends('price_unit', 'actual_price')
    def _compute_diff(self):
        for line in self:
            if line.actual_price:
                diff_amount = line.price_unit - line.actual_price
                line.diff_per = (diff_amount / line.actual_price) * 100 if line.actual_price != 0 else 0
            else:
                line.diff_per = 0

    @api.depends('quantity', 'price_unit', 'tax_ids', 'discount')
    def _compute_amounts(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(price, line.currency_id, line.quantity, product=line.product_id, partner=line.proforma_id.partner_id)
            line.price_total = taxes['total_included']
            line.price_subtotal = taxes['total_excluded']

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name = self.product_id.get_product_multiline_description_sale()
        self.price_unit = self.product_id.list_price
        self.actual_price = self.product_id.list_price