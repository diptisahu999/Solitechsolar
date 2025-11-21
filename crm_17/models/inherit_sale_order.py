from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby
import math
from odoo.tools import (
    formatLang
)
import base64
import io
import zipfile
from odoo.exceptions import ValidationError

class InheritSaleOrder(models.Model):
    _inherit = "sale.order"

     
    state = fields.Selection(selection_add=[('sale','Quotation Confirm'),
                                            ('draft','Quotation Draft'),
                                            ('discount_approval','Discount Approval'),
                                            ('pi','Create PI')])
    is_manager = fields.Boolean(string='Manager',default=False)
    price_list_id = fields.Many2one('techv.product.pricelist',string="Combo Product")
    partner_vat = fields.Char(string='Partner Vat')
    is_partner_vat = fields.Boolean(string='Is Partner Vat',compute='compute_partner_vat')
    sample_type = fields.Selection([('spare_parts', 'Spare Parts'),('sample', 'Sample'), ('gift', 'Gift')], string='Sample/Gift/Spare Parts')
    # rounding_amount = fields.Float(string="Rounding Amount",copy=False,compute="_compute_amounts",store=True)
    # sale_amount_total = fields.Monetary(string='Total ', store=True, readonly=True)
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    final_quotation = fields.Boolean(string='Final Quotation',default=False)
    is_group_admin = fields.Boolean(string='Is Group Access Right')
    special_instruction_dcr = fields.Selection([
        ('dcr', 'DCR'),
        ('non_dcr', 'NON DCR')
    ], string='DCR Instruction', index=True)

    special_instruction_mess = fields.Selection([
        ('with_mess', 'WITH MESH'),
        ('without_mess', 'WITHOUT MESH')
    ], string='Mesh Instruction', index=True)

    advance_percentage = fields.Float(string='Advance %')
    before_dp_percentage = fields.Float(string='Before DP %')
    lc_days = fields.Integer(string='LC Days')

    delivery_type = fields.Selection([
        ('for', 'FOR'),
        ('ex_works', 'Ex. Works')
    ], string='Delivery Type', index=True)

    advance_display = fields.Char(
        string="Advance %",
        compute="_compute_advance_display",
        inverse="_inverse_advance_display",
        store=False
    )
    before_dp_display = fields.Char(
        string="Before DP Amount",
        compute="_compute_before_dp_display",
        inverse="_inverse_before_dp_display",
        store=False
    )

    salesperson_phone = fields.Char(
        string="Salesperson Contact",
        compute='_compute_salesperson_phone',
        store=True,
        readonly=False # Keep editable if needed, but the computed value is stored
    )


    offer_validity = fields.Datetime(string='Offer Validity') 
    jurisdiction_state = fields.Char(
        string="Jurisdiction (State/City)",
        default="Surat, Gujarat",
        help="Select the applicable state or region."
    )
    start_date = fields.Date(string='Start Date')

    def action_print_so_custom_report(self):
        # This ID (crm_17.action_report_so_custom) MUST match the record id in the XML file below
        return self.env.ref('crm_17.action_report_so_custom').report_action(self)
        
    @api.depends('user_id')
    def _compute_salesperson_phone(self):
        for rec in self:
            phone = False
            # Check if user_id and its linked partner_id exist
            if rec.user_id and rec.user_id.partner_id:
                # Use phone first, then mobile
                phone = rec.user_id.partner_id.phone or rec.user_id.partner_id.mobile
            rec.salesperson_phone = phone


    @api.depends('advance_percentage', 'amount_total')
    def _compute_advance_display(self):
        for rec in self:
            if rec.amount_total and rec.advance_percentage:
                amt = rec.amount_total * rec.advance_percentage / 100
                rec.advance_display = f"₹ {amt:.2f} ({rec.advance_percentage:.2f}%)"
            else:
                rec.advance_display = "₹ 0.00 (0%)"

    def _inverse_advance_display(self):
        for rec in self:
            if not rec.advance_display:
                continue
            
            text = rec.advance_display.replace("₹", "").replace(",", "").strip()

            amount = 0.0
            percentage = 0.0

            # Extract entered amount
            if "(" in text:
                amount_text = text.split("(")[0].strip()
                try:
                    amount = float(amount_text)
                except:
                    amount = 0.0

            # ✅ VALIDATION — BLOCK IF AMOUNT > TOTAL
            if amount > rec.amount_total:
                raise ValidationError(
                    f"Advance amount (₹{amount:.2f}) cannot be greater than total amount (₹{rec.amount_total:.2f})."
                )

            # Extract percentage
            if "%" in text:
                percent_text = text.split("(")[1].replace(")", "").replace("%", "")
                try:
                    percentage = float(percent_text)
                except:
                    percentage = 0.0

            # Recalculate % if amount entered
            if amount > 0 and rec.amount_total > 0:
                percentage = (amount / rec.amount_total) * 100

            rec.advance_percentage = percentage
            rec._compute_advance_display()


    @api.depends('before_dp_percentage', 'amount_total')
    def _compute_before_dp_display(self):
        for rec in self:
            if rec.amount_total and rec.before_dp_percentage:
                amt = rec.amount_total * rec.before_dp_percentage / 100
                rec.before_dp_display = f"₹ {amt:.2f} ({rec.before_dp_percentage:.2f}%)"
            else:
                rec.before_dp_display = "₹ 0.00 (0%)"

    def _inverse_before_dp_display(self):
        for rec in self:
            txt = rec.before_dp_display or ""

            # Extract amount
            amount = 0.0
            try:
                amount_str = txt.split("(")[0].replace("₹", "").replace(",", "").strip()
                amount = float(amount_str)
            except:
                amount = 0.0

            # Validate
            if amount > rec.amount_total:
                raise ValidationError(
                    f"Before DP amount (₹{amount:.2f}) cannot exceed total amount (₹{rec.amount_total:.2f})."
                )

            # Calculate %
            percentage = 0.0
            if rec.amount_total:
                percentage = (amount / rec.amount_total) * 100

            rec.before_dp_percentage = percentage
            rec._compute_before_dp_display()



    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id_update_taxes(self):
        """
        When the Fiscal Position changes, manually loop through the order lines
        and re-apply the tax mapping. This automates the "update tax" button.
        """
        if not self.order_line or not self.fiscal_position_id:
            return

        for line in self.order_line:
            if line.product_id:
                # Get the default taxes from the product
                product_taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == self.company_id)
                
                # Apply the fiscal position's mapping to find the correct new tax
                line.tax_id = self.fiscal_position_id.map_tax(product_taxes)

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('sale.sale_order_menu').id
        for record in self:
            url = f'/web#id={record.id}&model=sale.order&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'
            
    def action_download_product_doc(self):
        attachment_ids = self.order_line.mapped('product_template_id.product_document_ids.ir_attachment_id')
        
        if not attachment_ids:
            return

        # Create an in-memory zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for attachment in attachment_ids:
                filename = attachment.name or f"{attachment.id}.bin"
                file_data = base64.b64decode(attachment.datas)
                zip_file.writestr(filename, file_data)

        zip_buffer.seek(0)
        old_attachments = self.env['ir.attachment'].search([('name', '=', 'product_documents.zip')])
        if old_attachments:
            old_attachments.unlink()
        # Create a new ir.attachment for the zip
        zip_attachment = self.env['ir.attachment'].create({
            'name': 'product_documents.zip',
            'type': 'binary',
            'datas': base64.b64encode(zip_buffer.read()),
            'mimetype': 'application/zip',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{zip_attachment.id}?download=true',
            'target': 'self',
        }
    
    def action_final_quotation(self):
        self.final_quotation = True
 
    @api.model
    def default_get(self, fields):
        res = super(InheritSaleOrder, self).default_get(fields)
        res['user_id'] = self.env.user.id
        return res 

    # @api.onchange('partner_id')
    # def _onchange_partner_id_user_id(self):
    #     self.user_id = self.env.user.id
    #     if not self.partner_id:
    #         self.user_id = False

    @api.onchange('partner_id')
    def compute_partner_vat(self):
        for rec in self:
            if rec.partner_id.vat:
                rec.is_partner_vat = True
                rec.partner_vat =  rec.partner_id.vat
            else:
                rec.is_partner_vat = False
                rec.partner_vat = ""
            for line in rec.order_line:
                line.compute_is_service()

            rec.is_group_admin = True if self.env.user.has_group('base.group_erp_manager') else False


    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """ Override of `sale` to recompute the delivery prices.

        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        price_unit = super()._update_order_line_info(product_id, quantity, **kwargs)
        if self:
            for line in self.order_line:
                line.onchange_sake_product_image()
                line.with_context(is_catlog_product=True)._compute_price_unit()
                line.onchange_gst_product()
        return price_unit

    def create_invoice_direct(self):
        inv_wizard = self.env['sale.advance.payment.inv'].create({
                'sale_order_ids':self.ids,
                'consolidated_billing': True,
                'advance_payment_method': 'delivered'
            })
        if inv_wizard:
            invoices = inv_wizard._create_invoices(inv_wizard.sale_order_ids)
            # inv_wizard.create_invoices()
            self.state = 'pi'
            return self.action_view_invoice(invoices=invoices)
        
    def _prepare_invoice(self):
        res = super(InheritSaleOrder, self)._prepare_invoice()
        res.update({'sample_type':self.sample_type,
                    'tag_ids':self.tag_ids.ids,
                    'project_id':self.project_id.id})
        return res
    
    @api.onchange('price_list_id')
    def _onchange_price_list_id(self):
        line_list = []
        self.order_line = False
        if self.price_list_id:
            for price in self.price_list_id.line_ids:
                if price.product_id.active:
                    line_list.append((0,0,{
                                    'product_id':price.product_id.id,
                                    'inch_feet_type':price.inch_feet_type,
                                    'height_length':price.height_length,
                                    'width':price.width,
                                    'sqft':price.sqft,
                                    'sqft_rate':price.sqft_rate,
                                    'product_uom_qty':price.qty if price.qty > 0 else 1,
                                    'width':price.width,
                                    'discount':price.disc_per,
                                    # 'price_unit':price.price_unit,
                                    # 'tax_id':[(6,0,price.tax_ids.ids)],
                                }))
            if line_list:
                self.order_line = line_list
                self.order_line.onchange_sake_product_image()
                self.order_line.onchange_gst_product()
                self.order_line._onchange_product_id()

    def sale_quotation_report(self):
        return self.env.ref('crm_17.action_sale_quotation').report_action(self)

    def amount_to_text(self, amount, currency='INR'):
        word = num2words(amount, lang='en_IN').upper()
        word = word.replace(",", " ")
        return word
    
    def _send_payment_succeeded_for_order_mail(self):
        """ Send a mail to the SO customer to inform them that a payment has been initiated.

        :return: None
        """
        mail_template = self.env.ref(
            'sale.mail_template_sale_payment_executed', raise_if_not_found=False
        )
        # for order in self:
        #     order._send_order_notification_mail(mail_template)
    
    def action_draft(self):
        res = super(InheritSaleOrder, self).action_draft()
        self.is_manager = False
        return res
    
    def action_discount_user(self):
        self.state = 'discount_approval'

    def action_discount_manager(self):
        self.is_manager = True
        self.state = 'draft'

    def send_whatsapp_message(self):
        return {
            'type': 'ir.actions.act_url',
            'url': "https://api.whatsapp.com/send?phone=" +
                    self.partner_id.phone + "&text=" + "Hii",
            'target': 'new',
            'res_id': self.id,
        }
    
    def _check_note(self):
        check_note = False
        for rec in self:
            if rec.note:
                if rec.note is False:
                    check_note = True
                if rec.note == '<p><br></p>':
                    check_note = True
            else:
                check_note = True
        return check_note
    
    @api.onchange('l10n_in_gst_treatment','order_line','partner_id')
    def _onchange_l10n_in_gst_treatment(self):
        if self.l10n_in_gst_treatment in ['overseas','special_economic_zone']:
            for line in self.order_line:
                line.tax_id = [(5, 0, 0)]
        else:
            pass
    # def _update_order_line_info(self, product_id, quantity, **kwargs):
    #     res = super(InheritSaleOrder, self)._update_order_line_info(product_id, quantity, **kwargs)
    #     self.order_line.onchange_gst_product()
    #     self.order_line.onchange_sake_product_image()
    #     return res
    
    def action_open_hike_wizard(self):
        self.ensure_one()
        return {
            'name': _("Hike"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.hike',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_hike_type': 'hike'}
        }
    
    def action_open_qty_wizard(self):
        self.ensure_one()
        return {
            'name': _("Qty Update"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.hike',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_hike_type': 'qty'}
        }
    
    def action_open_partner_view(self):
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
    
    @api.depends(
        'order_line.price_subtotal',
        'order_line.price_tax',
        'order_line.price_total',
        'order_line.product_uom_qty',
        'order_line.price_unit',
        'order_line.unit_price_per_nos',
        'order_line.wattage',
        'currency_id', 'company_id'
    )
    def _amount_all(self):
        """Compute totals using each line's computed subtotal/tax (which we fix on the line)."""
        for order in self:
            untaxed = 0.0
            tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
            amount_tax += line.price_tax
            order.update({
            'amount_untaxed': amount_untaxed,
            'amount_tax': amount_tax,
            'amount_total': amount_untaxed + amount_tax,
        })

    def update_product_price(self):
        for line in self.order_line:
            if line.price_unit == 0:
                line.sudo().write({'price_unit':line.product_id.list_price})

class InheritSaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _order = "id"

    image_128 = fields.Image(string="Image")
    inch_feet_type = fields.Selection([
        ('inch', 'Inch'),
        ('feet', 'Feet'),
        ('mm', 'MM'),
        ('tile', 'Tile'),
        ('basic', 'Basic'),
        ], 'Inch/Feet',default="basic")
    height_length = fields.Float(string="Height/Length")
    width = fields.Float(string="Width")
    tile_width = fields.Float(string="Tile Width (mm)")
    tile_length = fields.Float(string="Tile Length (mm)")
    layout = fields.Selection([
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
        ('horizontal_vertical', 'Horizontal/ Vertical')
        ], string="Layout")
    tiles_per_box = fields.Integer(string="Tile per Box")
    tile_final = fields.Float(string="Total Tiles")
    sqft = fields.Float(string="Sqft")
    sqft_rate = fields.Float(string="Sqft Rate")
    gst_tax = fields.Char(string='GST Tax',compute='get_gst_percentages')
    is_service = fields.Boolean(string='Service',default=False,compute='compute_is_service')
    no_discount_ok = fields.Boolean(string='No Discount',default=False,compute='compute_is_service')
    is_group_price = fields.Boolean(string='Group price change',default=False,store=True)
    is_categ_widht = fields.Boolean(string='Is Category Widht',default=False,store=True)
    is_tile = fields.Boolean(string='Is Tile',default=False,store=True)
    actual_price = fields.Float(string="Actual Price")
    diff_amount = fields.Float(string="Difference Amount")
    remarks = fields.Char(string='Remarks')
    diff_per = fields.Float(string="Difference Per(%)")
    up_after_disc_amt = fields.Float(string="Unit Price After Discount")
    wattage = fields.Float(
        string="Wattage (Wp)",
        related='product_id.wattage',
        store=True,
        readonly=True
    )

    unit_price_per_nos = fields.Monetary(
        string="Unit Price (₹ per Nos)",
        compute='_compute_unit_price_per_nos',
        store=True,
        readonly=True
    )

    @api.depends('wattage', 'price_unit')
    def _compute_unit_price_per_nos(self):
        """Calculates the price per unit number based on wattage."""
        for line in self:
            if line.wattage:
                line.unit_price_per_nos = (line.wattage or 0.0) * (line.price_unit or 0.0)
            else:
                line.unit_price_per_nos = line.price_unit or 0.0

    def _get_price_for_totals(self):
        """Return the price per sellable unit that should feed totals/taxes."""
        self.ensure_one()
        if self.wattage and self.wattage > 0:
            return self.unit_price_per_nos or 0.0
        return self.price_unit or 0.0

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'wattage', 'actual_price', 'unit_price_per_nos')
    def _compute_amount(self):
        """Make totals use the per-panel price if wattage is set."""
        for line in self:
            price_for_taxes = line._get_price_for_totals()
            price_after_discount = price_for_taxes * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(
                price_after_discount,
                line.order_id.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id,
            )

            # IMPORTANT: store the computed totals so order uses them
            line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            line.price_total = taxes.get('total_included', 0.0)
            line.price_subtotal = taxes.get('total_excluded', 0.0)

            # diff/disc logic unchanged
            if line.actual_price:
                line.diff_amount = line.price_unit - line.actual_price
                line.diff_per = (line.diff_amount / line.actual_price) * 100 if line.actual_price else 0.0
            else:
                line.diff_amount = 0.0
                line.diff_per = 0.0

            line.up_after_disc_amt = line.price_unit * (1 - (line.discount or 0.0) / 100.0) if line.discount else 0.0

    # Make tax totals use the per-panel price instead of ₹/Wp
    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        res = super()._convert_to_tax_base_line_dict()
        res.update({
            'price_unit': self._get_price_for_totals(),  # pass undiscounted per-panel price
            'quantity': self.product_uom_qty,
            'discount': self.discount or 0.0,
            'currency_id': self.order_id.currency_id,
            'product': self.product_id,
            'partner': self.order_id.partner_shipping_id,
            'taxes': self.tax_id,
        })
        return res

    # Ensure invoice uses the per-panel price
    def _prepare_invoice_line(self, **optional_values):
        res = super(InheritSaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res.update({
            'inch_feet_type': self.inch_feet_type,
            'height_length': self.height_length,
            'width': self.width,
            'sqft': self.sqft,
            'sqft_rate': self.sqft_rate,
            'tile_width': self.tile_width,
            'tile_length': self.tile_length,
            'layout': self.layout,
            'tiles_per_box': self.tiles_per_box,
            'tile_final': self.tile_final,
            'remarks': self.remarks,
            'actual_price': self.actual_price,
            'diff_amount': self.diff_amount,
            'diff_per': self.diff_per,
            # Critical: invoice unit price should be per nos, not ₹/Wp
            'price_unit': self._get_price_for_totals(),
        })
        return res

    @api.constrains('product_uom_qty')
    def _check_quantity_integer(self):
        for line in self:
            if line.product_uom_qty != int(line.product_uom_qty):
                raise ValidationError(_("Quantity must be an integer value."))

    @api.onchange('is_service','product_id')
    def compute_is_service(self):
        flg = False
        for service in self:
            service.no_discount_ok = False
            if service.product_id.type == 'service':
                flg =  True
            service.is_service = flg
            if service.product_id.no_discount_ok:
                service.no_discount_ok =  True

            service.is_group_price = self.env.user.has_group('crm_17.group_so_inv_price')
            service.is_categ_widht = True if service.product_id.width > 0 else False
            service.is_tile = service.product_id.is_tile

    @api.onchange('discount')
    def _onchange_discount(self):
        sale_per = self.env['ir.config_parameter'].sudo().get_param('saleperson_per')
        sale_per = float(sale_per or 0.0)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.user_has_groups('sales_team.group_sale_salesman_all_leads') and not self.user_has_groups('sales_team.group_sale_manager'):
            if sale_per and self.discount:
                if self.discount > sale_per:
                    raise UserError("Not Allowed: Discount exceeds %s%%" % sale_per)
            # if not sale_per:
            #     raise UserError("You are not allowed to give any discount. Please contact your manager.")
            
    @api.onchange('inch_feet_type','height_length','width','product_uom_qty','sqft')
    def onchange_inch_feet_type(self):
        for rec in self:
            if rec.inch_feet_type != 'basic':
                if rec.inch_feet_type == 'feet':
                    rec.sqft = math.ceil(rec.height_length * rec.width)

                if rec.inch_feet_type == 'inch':
                    length_feet = rec.height_length / 12.0
                    width_feet = rec.width / 12.0
                    rec.sqft = math.ceil(length_feet * width_feet)

                if rec.inch_feet_type == 'mm':
                    length_feet = rec.height_length / 305.0
                    width_feet = rec.width / 305.0
                    rec.sqft = math.ceil(length_feet * width_feet)
                if rec.sqft_rate == 0:
                    rec.sqft_rate = rec.product_id.list_price
                rec.price_unit = rec.sqft_rate * rec.sqft
            else:
                if self.inch_feet_type != 'tile':
                    rec.sqft_rate = 0
                    rec.sqft = 0
                rec.height_length = 0
                # rec.width = 0
                # self.price_unit = self.product_id.list_price

    @api.onchange('height_length', 'width', 'tile_width', 'tile_length', 'layout','tiles_per_box')
    def _onchange_calculate_tiles(self):
        for rec in self:
            if rec.height_length and rec.width and rec.tile_width and rec.tile_length and rec.layout and rec.tiles_per_box:
                # Setup
                room_length = rec.height_length
                room_width = rec.width
                tile_width = rec.tile_width
                tile_length = rec.tile_length
                layout = rec.layout
                tiles_per_box = rec.tiles_per_box

                # Layout-wise calculation
                if layout == 'horizontal':
                    tiles_along_length = math.ceil(room_length / tile_width)
                    tiles_along_width = math.ceil(room_width / tile_length)

                    val1 = math.ceil(room_length / tile_width)
                    val2 = math.ceil(room_width / tile_length)
                elif layout == 'vertical':
                    tiles_along_length = math.ceil(room_length / tile_length)
                    tiles_along_width = math.ceil(room_width / tile_width)

                    val1 = math.ceil(room_length / tile_length)
                    val2 = math.ceil(room_width / tile_width)
                else:  # horizontal_vertical
                    tiles_along_length = math.ceil(room_length / tile_width)
                    tiles_along_width = math.ceil(room_width / tile_width)

                    val1 = math.ceil(room_length / tile_width)
                    val2 = math.ceil(room_width / tile_length)
                # Total Tiles
                total_tiles = tiles_along_length * tiles_along_width

                # Boxes Needed
                boxes_needed = math.ceil(total_tiles / tiles_per_box)

                # Total Tiles to Give
                total_tiles_to_give = boxes_needed * tiles_per_box

                # Area Calculation
                tile_width_m = tile_width / 1000
                tile_length_m = tile_length / 1000
                area_sqft = tile_width_m * tile_length_m * 10.7639 * total_tiles_to_give

                # Assign results
                rec.sqft = round(area_sqft, 2)

                product = val1 * val2
                divided = product / tiles_per_box
                rounded = math.ceil(divided)    
                rec.tile_final = rounded * tiles_per_box

    @api.onchange('sqft_rate','inch_feet_type')
    def _onchange_sqft_rate(self):
        if self.inch_feet_type != 'basic':
            if self.sqft_rate:
                self.price_unit = self.sqft_rate * self.sqft
        else:
            if self.inch_feet_type != 'tile':
                self.sqft_rate = 0
                self.sqft = 0
            self.height_length = 0
            # self.width = 0
            self.price_unit = self.product_id.list_price

    def get_gst_percentages(self):
        for record in self:
            gst_percentages = []
            for tax in record.tax_id:
                match = re.search(r'\d*\.\d+%|\d+%', tax.name)
                if match:
                    gst_percentages.append(match.group())
            record.gst_tax = ' , '.join(gst_percentages)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.inch_feet_type != 'basic':
                rec.price_unit = rec.sqft_rate * rec.sqft
            else:
                rec.price_unit = rec.product_id.list_price
            rec.actual_price = rec.product_id.list_price
            
            rec.width = rec.product_id.width
            rec.tile_width = rec.product_id.tile_width
            rec.tile_length = rec.product_id.tile_length
            rec.tiles_per_box = rec.product_id.tiles_per_box
    
    @api.depends('product_id','product_uom','inch_feet_type')
    def _compute_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
                continue
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                line = line.with_company(line.company_id)
                price = line._get_display_price()
                price_list = line.product_id._get_tax_included_unit_price(
                    line.company_id or line.env.company,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                    )
                if self.env.context.get('is_catlog_product',False):
                    line.price_unit = price_list
                    line.actual_price = price_list
                # if line.price_unit != price_list:
                #     # if line.price_unit == 0:
                #     line.price_unit = price_list
            # if line.inch_feet_type != 'basic':
            #     line.sqft_rate = line.product_id.list_price

    @api.onchange('product_id')
    def onchange_sake_product_image(self):
    	for product in self:
    		product.image_128 = product.product_id.image_128


class InheritSaleOrderReport(models.Model):
    _inherit = "sale.report"
            
    final_quotation = fields.Boolean(string='Final Quotation',default=False)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['final_quotation'] = "s.final_quotation"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.final_quotation"""
        return res