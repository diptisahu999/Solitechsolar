from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from num2words import num2words
import re
from odoo.exceptions import UserError, ValidationError
import math

class InheritAccount(models.Model):
    _inherit = "account.move"

    pi_no = fields.Integer(string='PI No.',store=True)
    pi_chr = fields.Char(string='PI Number',store=True)
    pi_date = fields.Date(string='PI Date',store=True)
    po_number = fields.Char(string='PO Number')
    po_date = fields.Date(string='Order Date')
    state = fields.Selection(selection_add=[('draft','PI Draft'),('discount_approval','Discount Approval'),('posted','PI Confirm')],required=False)
    is_manager = fields.Boolean(string='Manager',default=False)
    irn_no = fields.Char(string="IRN No.")
    ank_no = fields.Char(string="Ank No.")
    einv_date = fields.Date(string="Einvoice Ack Date")
    project_name = fields.Char(string="Project Name")
    sample_type = fields.Selection([('spare_parts', 'Spare Parts'),('sample', 'Sample'), ('gift', 'Gift')], string='Sample/Gift/Spare Parts')
    tag_ids = fields.Many2many('crm.tag',string="Tags")
    shortly_dis_text = fields.Char('Shortly Discontinue Text')
    minimum_stock_text = fields.Char('Minimum Stock Text')
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    is_group_admin = fields.Boolean(string='Is Group Access Right',compute='compute_is_group_admin')
    invoice_date = fields.Date(
        string='Invoice/Bill Date',
        index=True,
        copy=False,default=fields.Datetime.now)
    is_button_approval = fields.Boolean(string='Soo Inventory Approval',default=False)
    inventory_approval = fields.Boolean(string='Send for Inventory Approval',default=False)
    inventory_approval_type = fields.Selection([('approve_pending', 'Send'),('approve', 'Approve'),('reject', 'Reject')], string='Approval Status', tracking=True)
    booking_type = fields.Selection([('send_for_book', 'Send for Booking'),('confirm_book', 'Confirm Booking')], string='Booking Status', tracking=True)
    project_id = fields.Many2one('project.project',string="Project",tracking=True)

    def button_inventory_approval(self):
        for line in self.invoice_line_ids:
            if line.inventory_approval and not line.inventory_approval_type:
                line.sudo().write({'inventory_approval_type':'approve_pending'})
        self.inventory_approval_type = 'approve_pending'
        self.booking_type = 'send_for_book'

    def inventory_approval_confirm(self):
        if all(line.inventory_approval_type == 'approve' or not line.inventory_approval_type for line in self.invoice_line_ids):
            self.action_post()

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('account.menu_action_move_out_invoice_type').id
        for record in self:
            url = f'/web#id={record.id}&model=account.move&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'

    @api.depends('date', 'auto_post')
    def _compute_hide_post_button(self):
        res = super(InheritAccount, self)._compute_hide_post_button()
        for line in self.invoice_line_ids:
            line.compute_is_group_price()
        return res
    
    @api.onchange('is_group_admin')
    def compute_is_group_admin(self):
        for rec in self:
            rec.is_group_admin = True if self.env.user.has_group('base.group_erp_manager') else False

            # if len(rec.invoice_line_ids.filtered(lambda r: r.inventory_approval)) > 0:
            #     if all(line.inventory_approval_type == 'approve' for line in rec.invoice_line_ids.filtered(lambda r: r.inventory_approval)):
            #         self.inventory_approval_type = 'approve'
            #         self.inventory_approval = True
            #         self.booking_type = 'confirm_book'
    
    @api.model
    def default_get(self, fields):
        res = super(InheritAccount, self).default_get(fields)
        res['invoice_cash_rounding_id'] = self.env.ref('crm_17.round_off_account_cash_round_off').id if self.env.ref('crm_17.round_off_account_cash_round_off') else False
        return res 

    def amount_to_text(self, amount, currency='INR'):
        word = num2words(amount, lang='en_IN').upper()
        word = word.replace(",", " ")
        return word
    
    def _check_note(self):
        check_note = False
        for rec in self:
            if rec.narration:
                if rec.narration == False:
                    check_note = True
                if rec.narration == '<p><br></p>':
                    check_note = True
            else:
                check_note = True
        return check_note
    
    @api.model
    def create(self, vals):
        if vals.get('pi_no') == None or vals.get('pi_no') == 0:
            vals['pi_no'] = self.bill_chr_vld()

        if not vals.get('pi_chr') or vals.get('pi_chr') == False:
            vals['pi_chr'] = self.genrate_pi_number(vals.get('pi_no'),date.today().year)
            vals['pi_date'] = date.today()
        res = super(InheritAccount, self).create(vals)

        return res
    
    def genrate_pi_number(self,max_pi_no=False,year=False):
        pi_no = 0
        if max_pi_no > 0:
            pi_no = max_pi_no
        else:
            pi_no = 1
        pi_chr = ''
        year = date.today().year
        if pi_no > 0:
            pi_chr = 'PI/' + str(year) + '/' + str(pi_no)
        return pi_chr
    
    def bill_chr_vld(self):
        company_id = str(self.env.company.id) if self.env.company.id else str(self.company.id)
        query = ''' Select max(pi_no) From account_move Where company_id = ''' + str(company_id)

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0]['max'] == None :
            serial = 1
        else:
            serial = 1 + query_result[0]['max']
        return serial
    
    @api.onchange('l10n_in_gst_treatment','invoice_line_ids','partner_id')
    def _onchange_l10n_in_gst_treatment(self):
        if self.l10n_in_gst_treatment in ['overseas','special_economic_zone']:
            for line in self.invoice_line_ids:
                line.tax_ids = False
        else:
            for line_inv in self.invoice_line_ids:
                line_inv.onchange_gst_product()

        for line in self.invoice_line_ids:
            if line.product_id:
                self.inventory_approval = False
                self.inventory_approval_type = False
                self.is_button_approval = False

    def button_draft(self):
        res = super(InheritAccount, self).button_draft()
        self.is_manager = False
        reserved_stock = self.env['reserved.stock'].search([('account_id', '=', self.id)])
        if reserved_stock:
            reserved_stock.sudo().write({'reserved_type':'unreserved'})
        self.inventory_approval = False
        self.inventory_approval_type = False
        self.is_button_approval = False
        return res

    def action_button_cancel_all(self):
        for rec in self:
            if rec.ref_id > 0 and rec.is_post_entry:
                raise ValidationError(f"{rec.name} has already been posted. You cannot cancel it.")
            else:
                rec.button_cancel()
                rec.is_manager = False
                reserved_stock = self.env['reserved.stock'].search([('account_id', '=', rec.id)])
                if reserved_stock:
                    reserved_stock.sudo().write({'reserved_type': 'unreserved'})
                rec.inventory_approval = False
                rec.inventory_approval_type = False
                rec.is_button_approval = False

    def action_discount_user(self):
        self.state = 'discount_approval'

    def action_discount_manager(self):
        self.is_manager = True
        self.state = 'draft'

    def action_open_hike_wizard(self):
        self.ensure_one()
        return {
            'name': _("Hike"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.hike',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_hike_type': 'hike'}
        }
    
    def action_open_qty_wizard(self):
        self.ensure_one()
        return {
            'name': _("Qty Update"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.hike',
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
    
    def action_post(self):
        data_list = []
        if self.move_type == 'out_invoice':
            # if not self.po_number:
            #     raise ValidationError("Please enter the PO Number.")
            if not self.po_date:
                raise ValidationError("Please enter the Order Date.")
            error_messages = []
            minimum_stock_barcodes = []
            for line in self.invoice_line_ids.filtered(lambda x: x.product_id.is_not_check_stock != True):
                product = line.product_id
                if product.type == 'product':
                    available_qty = product.free_qty
                    required_qty = line.quantity
                    total_available_qty = available_qty
                    
                    reserved_stock = self.env['reserved.stock'].search([('reserved_type', '=', 'reserved'),('product_id', '=', line.product_id.id)])
                    if reserved_stock:
                        total_available_qty = (available_qty - sum(reserved_stock.mapped('reserved_qty')))

                    if line.inventory_approval_type != 'approve':
                        line.sudo().write({'inventory_approval':False})

                    if required_qty > total_available_qty and line.inventory_approval_type != 'approve':
                        line.sudo().write({'inventory_approval':True})
                        error_messages.append(
                            f"Product: {product.display_name} - Available: {total_available_qty}, Required: {required_qty}"
                        )

                    if line.product_id.minimum_stock > 0:
                        if available_qty <= line.product_id.minimum_stock:
                            minimum_stock_barcodes.append(line.product_id.barcode)

                    data_list.append({
                                    'account_id': self.id,
                                    'pi_chr': self.pi_chr,
                                    'user_id': self.user_id.id,
                                    'product_id': line.product_id.id,
                                    'reserved_qty': required_qty,
                                    'reserved_type': 'reserved'                       
                        })
                    
            if error_messages and not self.inventory_approval:
                if not self.inventory_approval_type:
                    query = """
                        UPDATE account_move
                        SET is_button_approval = %s
                        WHERE id = %s
                    """
                    self.env.cr.execute(query, (True, self.id))
                    self.env.cr.commit()
                # raise UserError("Not enough stock for the following products:\n" + "\n".join(error_messages))
                return {
                    'name': _("Invalid Operation"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move.validation',
                    'view_mode': 'form',
                    'view_id': self.env.ref('crm_17.account_move_validation_wizard_form').id,
                    'target': 'new',
                    'context': {
                        'default_name': "<b>Not enough stock</b> for the following products:<br/>" + "<br/>".join(error_messages)
                    }
                }
            
            if minimum_stock_barcodes:
                self.minimum_stock_text = ', '.join(set(minimum_stock_barcodes))
            
            barcodes = [
                line.product_id.barcode for line in self.invoice_line_ids if line.product_id.shortly_discontinue
            ]
            if barcodes:
                self.shortly_dis_text = ', '.join(barcodes)
        
        res = super(InheritAccount, self).action_post()
        if self.move_type == 'out_invoice':
            if data_list:
                for rec in data_list:
                    reserved_stock = self.env['reserved.stock'].search([('account_id', '=', self.id),('product_id', '=', rec.get('product_id'))])
                    if reserved_stock:
                        reserved_stock.sudo().write({'reserved_qty':rec.get('reserved_qty'),
                                                     'reserved_type':rec.get('reserved_type')})
                    else:
                        self.env['reserved.stock'].create({
                                            'account_id':rec.get('account_id'),
                                            'pi_chr':rec.get('pi_chr'),
                                            'user_id':rec.get('user_id'),
                                            'product_id':rec.get('product_id'),
                                            'reserved_qty':rec.get('reserved_qty'),
                                            'reserved_type':rec.get('reserved_type'),
                        })
        return res
        
class InheritAccountLine(models.Model):
    _inherit = "account.move.line"

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
    is_group_price = fields.Boolean(string='Group price change',default=False,compute='compute_is_group_price',store=True)
    actual_price = fields.Float(string="Actual Price")
    diff_amount = fields.Float(string="Difference Amount")
    diff_per = fields.Float(string="Difference Per(%)")
    remarks = fields.Char(string='Remarks')

    inventory_approval = fields.Boolean(string='Send for Inventory Approval',default=False)
    inventory_approval_type = fields.Selection([('approve_pending', 'Send'),('approve', 'Approve'),('reject', 'Reject')], string='Approval Status', tracking=True)
    pi_chr = fields.Char(related='move_id.pi_chr')
    free_qty = fields.Float(related='product_id.free_qty')
    barcode = fields.Char(related='product_id.barcode')
    invoice_user_id = fields.Many2one(related='move_id.invoice_user_id')
    book_qty = fields.Float(string="Book Quantity",compute='compute_is_group_price')
    upcoming_date = fields.Date(string='Approx Upcoming Date')
    remark_inv = fields.Char(string='Remark')

    def button_inventory_approve(self):
        self.inventory_approval_type = 'approve'
        self.move_id.inventory_approval_confirm()

    def button_inventory_reject(self):
        self.inventory_approval_type = 'reject'

    @api.depends('is_group_price', 'product_id')
    @api.onchange('is_group_price','product_id')
    def compute_is_group_price(self):
        for service in self:
            service.is_group_price = self.env.user.has_group('crm_17.group_so_inv_price')
            service.actual_price = service.product_id.list_price

            service.book_qty = service.product_id.free_qty - service.quantity

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        res = super(InheritAccountLine, self)._compute_totals()
        for line in self:
            if line.actual_price:
                line.diff_amount = line.price_unit - line.actual_price
                if line.actual_price != 0:
                    line.diff_per = (line.diff_amount / line.actual_price) * 100
                else:
                    line.diff_per = 0
            else:
                line.diff_amount = 0
                line.diff_per = 0
        return res
    
    @api.onchange('discount')
    def _onchange_discount(self):
        invperson_per = self.env['ir.config_parameter'].sudo().get_param('invperson_per')
        # invperson_per = self.env.user.dis_per
        invperson_per = float(invperson_per)
        if self.env.user.has_group('account.group_account_invoice') and not self.user_has_groups('account.group_account_user') and not self.user_has_groups('account.group_account_manager'):
            if invperson_per and self.discount:
                if self.discount > invperson_per:
                    raise UserError("Not Allowed: Discount exceeds %s%%" % invperson_per)
            # if not invperson_per:
            #     raise UserError("You are not allowed to give any discount. Please contact your manager.")

    @api.onchange('inch_feet_type','height_length','width','quantity','sqft')
    def onchange_inch_feet_type(self):
        for rec in self:
            if rec.inch_feet_type != 'basic':
                rec.sqft_rate = rec.product_id.list_price
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
                rec.price_unit = rec.sqft_rate * rec.sqft

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
            self.width = 0
            self.price_unit = self.product_id.list_price

    def get_gst_percentages(self):
        for record in self:
            gst_percentages = []
            for tax in record.tax_ids:
                match = re.search(r'\d*\.\d+%|\d+%', tax.name)
                if match:
                    gst_percentages.append(match.group())
            record.gst_tax = ' , '.join(gst_percentages)
