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
    cgst_amount = fields.Monetary(string='CGST', compute='_compute_amounts')
    sgst_amount = fields.Monetary(string='SGST', compute='_compute_amounts')
    igst_amount = fields.Monetary(string='IGST', compute='_compute_amounts')

    is_manager = fields.Boolean(string='Manager', default=False)
    project_id = fields.Many2one('project.project', string="Project", tracking=True)
    sample_type = fields.Selection([('spare_parts', 'Spare Parts'), ('sample', 'Sample'), ('gift', 'Gift')], string='Sample/Gift/Spare Parts')
    source_id = fields.Many2one('utm.source', string='Source') # NEW FIELD

    narration = fields.Html(string="Terms and Conditions")
    sale_order_id = fields.Many2one('sale.order', string='Source Sale Order', readonly=True, copy=False)
    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        help="The CRM opportunity related to this proforma invoice.",
        domain="[('type', '=', 'opportunity')]",
        copy=False
    )
    custom_so_id = fields.Many2one('custom.sale.order', string="Related Custom SO", readonly=True)

    def get_company_header_image(self):
        """
        1. Switches to Superuser (sudo) to bypass the 'account.move' Access Error.
        2. Tries to get the custom Quotation Image (Document Layout header).
        3. If that is empty, falls back to the standard Company Logo.
        """
        self.ensure_one()
        # Use sudo() to ignore permissions and get the record
        company = self.company_id.sudo()
        
        # return the custom header if it exists, otherwise return the standard logo
        return company.quotation_image or company.logo
        
    def amount_to_text(self, amount, currency='INR'):
        """
        Converts a numeric amount to its text representation in words.
        e.g., 1234.56 -> "ONE THOUSAND TWO HUNDRED THIRTY-FOUR AND 56/100"
        """
        # Ensure num2words is installed: pip install num2words
        try:
            word = self.currency_id.amount_to_text(amount)
        except (AttributeError, TypeError):
             # Fallback for currencies without a specific to_text method
             word = num2words(int(amount), lang='en_IN').upper()
             decimals = int(round((amount - int(amount)) * 100))
             if decimals > 0:
                 word += f" AND {decimals}/100"
        return word
    
    @api.depends('line_ids.price_subtotal', 'line_ids.price_total')
    def _compute_amounts(self):
        for pi in self:
            untaxed = sum(pi.line_ids.mapped('price_subtotal'))
            tax_total = sum(pi.line_ids.mapped('price_tax'))
            total = untaxed + tax_total

            # Compute tax breakdown by iterating lines and recomputing their tax entries
            cgst = 0.0
            sgst = 0.0
            igst = 0.0
            for line in pi.line_ids:
                # price used for tax calculation should be consistent with line logic
                price_for_taxes = getattr(line, '_get_price_for_totals', lambda: line.price_unit)()
                price_after_discount = price_for_taxes * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_ids.compute_all(price_after_discount, pi.currency_id, line.quantity, product=line.product_id, partner=pi.partner_id)
                for t in taxes.get('taxes', []):
                    tname = (t.get('name') or '').upper()
                    amt = t.get('amount', 0.0)
                    if 'CGST' in tname:
                        cgst += amt
                    elif 'SGST' in tname:
                        sgst += amt
                    elif 'IGST' in tname:
                        igst += amt

            pi.amount_untaxed = untaxed
            pi.amount_tax = tax_total
            pi.amount_total = total
            pi.cgst_amount = cgst
            pi.sgst_amount = sgst
            pi.igst_amount = igst
    
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
        """
        Confirms the Proforma Invoice (moves state to 'posted').

        Adds validation to prevent confirming PIs that would exceed the SO line's
        quantity if that quantity is already fully confirmed on other PIs.
        """

        # 1. Get all *posted* PIs (excluding the current one) for the same SO.
        if self.sale_order_id:
            posted_pis = self.search([
                ('sale_order_id', '=', self.sale_order_id.id),
                ('state', '=', 'posted'),
                ('id', '!=', self.id),
            ])

            # Map product ID to total confirmed qty from other PIs
            confirmed_qty_map = {}
            for pi in posted_pis:
                for line in pi.line_ids:
                    product_id = line.product_id.id
                    confirmed_qty_map[product_id] = confirmed_qty_map.get(product_id, 0.0) + line.quantity

            # 2. Validate current PI lines
            for pi_line in self.line_ids:
                so_line = pi_line.sale_line_id
                if not so_line:
                    continue  # Not linked to SO line → skip

                so_qty = so_line.product_uom_qty
                product_id = pi_line.product_id.id

                already_confirmed_qty = confirmed_qty_map.get(product_id, 0.0)
                total_confirmed = already_confirmed_qty + pi_line.quantity

                if total_confirmed > so_qty:
                    raise UserError(_(
                        "You cannot confirm this Proforma Invoice.\n"
                        "The total confirmed quantity for product '%s' would become %.2f units, "
                        "which exceeds the Source Quotation quantity of %.2f units.\n"
                        "%.2f units are already confirmed on other Proforma Invoices."
                    ) % (
                        pi_line.product_id.name,
                        total_confirmed,
                        so_qty,
                        already_confirmed_qty
                    ))

        # Final: mark as posted
        self.write({'state': 'posted'})

        
    # --- NEW: Navigation Actions for Smart Buttons ---
    def action_view_source_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source Quotation'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_custom_so(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirmed Sale Order'),
            'res_model': 'custom.sale.order',
            'res_id': self.custom_so_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def create_from_sale_order(self, sale_order):
        """Create a Proforma Invoice by copying a Sale Order's header and lines.

        `sale_order` can be a `sale.order` record or an id.
        Returns the created `proforma.invoice` record.
        """
        if not sale_order:
            raise ValidationError(_('No Sale Order provided to create Proforma Invoice.'))

        so_model = self.env['sale.order']
        if isinstance(sale_order, int):
            so = so_model.browse(sale_order)
        else:
            so = sale_order

        if not so or not so.exists():
            raise ValidationError(_('Sale Order not found.'))

        pi_vals = {
            'partner_id': so.partner_id.id,
            'partner_shipping_id': so.partner_shipping_id.id if so.partner_shipping_id else so.partner_id.id,
            'invoice_payment_term_id': so.payment_term_id.id if hasattr(so, 'payment_term_id') else False,
            'sale_order_id': so.id,
            'company_id': so.company_id.id,
            'user_id': so.user_id.id,
            'narration': so.note or False,
        }

        pi = self.create(pi_vals)

        line_vals = []
        for sol in so.order_line:
            lv = {
                'proforma_id': pi.id,
                'product_id': sol.product_id.id or False,
                'name': sol.name or (sol.product_id.get_product_multiline_description_sale() if sol.product_id else ''),
                'quantity': sol.product_uom_qty,
                # Keep `price_unit` as the sale order's unit price (₹/Wp)
                'price_unit': sol.price_unit,
                'discount': sol.discount,
                'tax_ids': [(6, 0, sol.tax_id.ids)],
                # Store the per-sellable-unit price as `actual_price` (₹ per Nos)
                'actual_price': sol._get_price_for_totals() if hasattr(sol, '_get_price_for_totals') else (sol.actual_price or (sol.product_id.list_price if sol.product_id else 0.0)),
                'remarks': sol.remarks,
                'sale_line_id': sol.id,
                'wattage': sol.wattage,
            }
            line_vals.append((0, 0, lv))

        if line_vals:
            pi.write({'line_ids': line_vals})

        # Recompute amounts after writing lines
        pi._compute_amounts()
        return pi
    def get_remaining_qty(self, so_id, product_id):
        # FIX: Ensure 'custom.sale.order' model exists
        order = self.env['custom.sale.order'].browse(so_id)
        
        # FIX: Check if 'line_ids' is the correct field name on custom.sale.order
        so_line = order.line_ids.filtered(lambda l: l.product_id.id == product_id)
        total_qty = so_line.product_uom_qty if so_line else 0

        # FIX: 'proformaids' likely needs to be 'proforma_ids' (check your custom.sale.order model)
        # FIX: Changed state 'confirmed' to 'posted' to match your selection field
        confirmed_pis = order.proforma_ids.filtered(lambda pi: pi.state == 'posted')
        
        used_qty = sum(
            line.quantity for pi in confirmed_pis for line in pi.line_ids if line.product_id.id == product_id
        )
        return total_qty - used_qty

    def action_confirm(self):
        for pi in self:
            if not pi.custom_so_id:
                continue # Skip if no custom SO is linked
                
            so = pi.custom_so_id
            for line in pi.line_ids:
                remaining = self.get_remaining_qty(so.id, line.product_id.id)
                if line.quantity > remaining:
                    raise ValidationError(
                        f"You have only {remaining} quantity left for product '{line.product_id.name}'."
                    )
        # Assuming you want to change state to posted after validation
        self.write({'state': 'posted'})


class ProformaInvoiceLine(models.Model):
    _name = "proforma.invoice.line"
    _description = "Proforma Invoice Line (Non-Accounting)"

    proforma_id = fields.Many2one('proforma.invoice', string='Proforma', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description', required=True)
    product_type = fields.Selection(related='product_id.detailed_type', string="Product Type")
    quantity = fields.Float(string='Quantity', default=1.0)
    
    # Base Price (e.g. 13.00)
    price_unit = fields.Float(string='Price')
    
    tax_ids = fields.Many2many('account.tax', string='Taxes') 
    price_subtotal = fields.Monetary(string='Tax excl.', compute='_compute_amounts', store=True)
    price_total = fields.Monetary(string='Total', compute='_compute_amounts', store=True)
    currency_id = fields.Many2one('res.currency', related='proforma_id.currency_id')
    
    inch_feet_type = fields.Selection([('inch', 'Inch'), ('feet', 'Feet'), ('mm', 'MM'), ('tile', 'Tile'), ('basic', 'Basic')], 'Inch/Feet', default="basic")
    discount = fields.Float(string='Discount (%)')
    actual_price = fields.Float(string="Actual Price")

    remarks = fields.Char(string='Remarks')
    sale_line_id = fields.Many2one('sale.order.line', string='Source SO Line', readonly=True, copy=False)

    # --- FIX: Removed "related" attribute to prevent KeyError ---
    wattage = fields.Float(string="Wattage (Wp)")
    
    # Calculated Price (Wattage * Price)
    unit_price_per_nos = fields.Monetary(string="Unit Price (₹ per Nos)", compute='_compute_unit_price_per_nos', store=True)
    
    up_after_disc_amt = fields.Float(string="Unit Price After Discount")
    diff_amount = fields.Float(string="Difference Amount")
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_amounts', store=True)

    @api.onchange('quantity')
    def onchangequantity(self):
        # --- FIX 2: Corrected Field Names (proformaid -> proforma_id, etc.) ---
        if self.proforma_id and self.proforma_id.custom_so_id and self.product_id:
            # Note: This calls get_remaining_qty on the PARENT (Invoice), ensure it exists there
            remaining = self.proforma_id.get_remaining_qty(self.proforma_id.custom_so_id.id, self.product_id.id)
            if self.quantity > remaining:
                self.quantity = remaining
                return {
                    'warning': {
                        'title': "Quantity Exceeded",
                        'message': f"You have only {remaining} quantity left for this product."
                    }
                }

    @api.depends('quantity', 'price_unit', 'tax_ids', 'discount', 'wattage', 'unit_price_per_nos')
    def _compute_amounts(self):
        for line in self:
            price_for_taxes = line._get_price_for_totals()
            price_after_discount = price_for_taxes * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_ids.compute_all(price_after_discount, line.currency_id, line.quantity, product=line.product_id, partner=line.proforma_id.partner_id)
            line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            line.price_total = taxes.get('total_included', 0.0)
            line.price_subtotal = taxes.get('total_excluded', 0.0)

            if line.actual_price:
                line.diff_amount = line.price_unit - line.actual_price
                line.up_after_disc_amt = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            else:
                line.diff_amount = 0.0
                line.up_after_disc_amt = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

    def _get_price_for_totals(self):
        self.ensure_one()
        if self.wattage and self.wattage > 0:
            return self.unit_price_per_nos or 0.0
        return self.price_unit or 0.0

    @api.depends('wattage', 'price_unit')
    def _compute_unit_price_per_nos(self):
        for line in self:
            if line.wattage:
                line.unit_price_per_nos = (line.wattage or 0.0) * (line.price_unit or 0.0)
            else:
                line.unit_price_per_nos = line.price_unit or 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name = self.product_id.get_product_multiline_description_sale()
        self.price_unit = self.product_id.list_price
        self.actual_price = self.product_id.list_price
        
        # --- FIX: Safely try to get wattage from product, default to 0 if not found ---
        if hasattr(self.product_id, 'wattage'):
            self.wattage = self.product_id.wattage
        else:
            self.wattage = 0.0
