from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby
import math
from odoo.tools.misc import xlwt
import base64 
import io
from datetime import date
from collections import defaultdict
from odoo.exceptions import ValidationError
from odoo.tools import OrderedSet, groupby

class InheritStockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_no = fields.Char(string="Invoice No",tracking=True)
    company_name = fields.Char(string="Company Name",tracking=True)
    inward_date = fields.Date(string="Inward Date",tracking=True)
    rpt_xls_file = fields.Binary()
    is_lot_name = fields.Boolean(string="Is Lot Name",compute='_compute_is_lot_name')
    is_gen_lot = fields.Boolean(string="Is Generate Serail")
    is_last_seq = fields.Boolean(string="Is Last Seq")
    remarks = fields.Char(string="Remarks")
    is_contener = fields.Boolean(string="is import",tracking=True)
    contener_no = fields.Char(string="Container No.")
    courier_id = fields.Many2one('courier.mst',string="Courier",tracking=True)
    pi_chr = fields.Char(string="PI Number")
    po_number = fields.Char(string='PO Number')
    is_stock = fields.Boolean(string="Stock",tracking=True)
    is_return = fields.Boolean(string="Is old Return",tracking=True)
    sample_type = fields.Selection([('spare_parts', 'Spare Parts'),('sample', 'Sample'), ('gift', 'Gift'), ('missing_product', 'Missing Product'), ('replacement', 'Replacement')], string='Sample/Gift/Spare Parts')
    spare_parts_id = fields.Many2one('spare.parts.production',string="Spare Parts")
    company_type = fields.Selection([('DOLPHY INDIA PVT LTD', 'DOLPHY INDIA PVT LTD'),('DOLPHIN E-COMMERCE', 'DOLPHIN E-COMMERCE')], string='Company Name')
    remark_text = fields.Text(string="Remarks")
    e_commerce_deliverie = fields.Boolean(string="E-Commerce Deliverie",tracking=True)

    @api.depends('move_ids.delay_alert_date')
    def _compute_delay_alert_date(self):
        res = super(InheritStockPicking,self)._compute_delay_alert_date()
        for pic in self:
            if pic.origin != '/':
                inv_rec = self.env['account.move'].search(['|',('invoice_picking_id', '=', pic.id),('name', '=', pic.origin)])
                if inv_rec:
                    pic.pi_chr = inv_rec.pi_chr
                    pic.po_number = inv_rec.po_number
        return res
    
    @api.onchange('company_type')
    def _onchange_company_type(self):
        self.company_name = self.company_type
    
    def print_pi_report(self):
        if self.origin != '/':
            inv_rec = self.env['account.move'].search(['|',('invoice_picking_id', '=', self.id),('name', '=', self.origin)])
            if inv_rec:
                return self.env.ref('crm_17.action_proforma_invoice_report').report_action(inv_rec)
    
    def action_picking_cancel(self):
        # picking_rec = self.env['stock.picking'].search([('id', 'in', self.ids)])
        picking_rec = self.env['stock.picking'].search([('date_deadline', '>=', '01/12/2024 00:00:00'),('date_deadline', '<=', '28/02/2025 23:59:59'),('state', '!=', 'cancel'),('picking_type_code', '=', 'outgoing')])
        if picking_rec:
            for pic in picking_rec:
                if pic.state != 'done':
                    pic.sudo().action_cancel()

    def get_account_move(self):
        return self.env['account.move'].search([("invoice_picking_id", "=", self.id)])
    
    def get_report_view(self):
        line_list = []
        sorted_move_ids = sorted(self.move_ids_without_package,key=lambda r: min(r.location_ids.mapped('sequence')) if r.location_ids else 0)
        for line in sorted_move_ids:
            loc_dict = {}
            sorted_res_lines = sorted(line.move_line_ids,key=lambda r: r.location_id.sequence)
            for res in sorted_res_lines:
                loc_id = res.location_id.id
                
                if loc_id not in loc_dict:
                    loc_dict[loc_id] = {
                        'location_name': res.location_id.complete_name,
                        'barcode': res.product_id.barcode,
                        'quantity': 0,
                        'lot_names': [],
                        'tracking': res.product_id.tracking  # Add tracking type
                    }

                related_moves = line.move_line_ids.filtered(lambda x: x.location_id.id == loc_id)
                loc_dict[loc_id]['quantity'] = sum(related_moves.mapped('quantity'))
                
                # Store lot names only if tracking type is 'serial'
                if res.product_id.tracking in ('serial','lot'):
                    lot_names = related_moves.mapped('lot_id.name')
                    if lot_names:
                        loc_dict[loc_id]['lot_names'] = lot_names
            sorted_locations = sorted(loc_dict.items(), key=lambda x: self.env['stock.location'].browse(x[0]).sequence)
            for loc_id, data in sorted_locations:
                lot_name = ""
                if data['tracking'] in ('serial','lot') and data['lot_names']:
                    lot_name = data['lot_names'][0]
                    if lot_name != data['lot_names'][-1]:
                        lot_name = f"{data['lot_names'][0]} to {data['lot_names'][-1]}"

                line_list.append({
                    'location_name': data['location_name'],
                    'barcode': data['barcode'],
                    'quantity': data['quantity'],
                    'lot_name': lot_name if data['tracking'] in ('serial','lot') else ""  # Ensure empty lot_name if not serial
                })

        return line_list
    
    @api.onchange('move_ids.move_line_ids.lot_name')
    @api.depends('move_ids.move_line_ids.lot_name')
    def _compute_is_lot_name(self):
        for record in self:
            record.is_gen_lot = True 
            is_gen_lot = True
            if record.picking_type_id.code == "incoming":

                for rec in record.move_ids:
                    for line in rec.move_line_ids:

                        if not line.lot_name:
                            is_gen_lot = False

                record.is_gen_lot = is_gen_lot
            record.is_lot_name = True


    def print_report_lot(self):   
        stock_lots = self.env['stock.lot'].sudo().search([('product_id', 'in', self.move_ids_without_package.mapped('product_id').ids),('id', 'in', self.move_ids_without_package.mapped('lot_ids').ids)])
        # return self.env.ref('crm_17.action_serial_lot_report').report_action(stock_lots)

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Barcode')

        center_style = xlwt.easyxf(
            "align: vert centre, horiz centre; font: bold 1; border: top thin, right thin, bottom thin, left thin;"
        )

        worksheet.col(0).width = 8000 
        worksheet.col(1).width = 8000 
        worksheet.col(2).width = 8000 
        row = 0
        for rec in self.move_ids:
            for line in rec.move_line_ids:
                lot_name = False
                if self.picking_type_code == 'outgoing':
                    lot_name = line.lot_id.name or ""
                else:
                    lot_name = line.lot_name or ""
        # for index, line in enumerate(stock_lots, start=1):

                worksheet.write(row, 0, line.product_id.barcode or "", center_style)

                worksheet.write(row, 1, lot_name, center_style)

                worksheet.write(row, 2, lot_name, center_style)

                row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        self.rpt_xls_file = base64.encodebytes(fp.getvalue())

        return {
            'type': 'ir.actions.act_url',
            'name': 'stock.picking',
            'url': '/web/content/stock.picking/%s/rpt_xls_file/barcode_report_excel.xls?download=true' %(self.id),
        }
    
    def button_validate(self):
        if self.picking_type_id.code == "incoming":
            for line in self.move_ids:
                for move_line in line.move_line_ids:
                    if not self.return_id:
                        existing_lot = self.env['stock.lot'].sudo().search([('name', '=', move_line.lot_name)], limit=1)
                        if existing_lot:
                            raise UserError(
                                f"The Serial Number '{move_line.lot_name}' for the Product '{move_line.product_id.name}' Already Exists. \n"
                                f"Please Regenerate the Serial Number."
                            )

        res = super(InheritStockPicking,self).button_validate()
        if self.picking_type_id.code == "incoming" and not self.is_contener and not self.is_return:
            product_max_seq = defaultdict(int)

            for line in self.move_ids:
                if line.lot_ids:
                    for lot_id in line.lot_ids:
                        match = re.search(r'\d+$', lot_id.name[-5:])
                        if match:
                            seq = int(match.group())
                            product_max_seq[lot_id.product_id.id] = max(product_max_seq[lot_id.product_id.id], seq)

            for product_id in product_max_seq.keys():
                highest_lot = self.env['stock.lot'].search([('product_id', '=', product_id),('name', '!=', False)], order='name desc', limit=1)

                if highest_lot and highest_lot.name:
                    match = re.search(r'\d+$', highest_lot.name[-5:])
                    if match:
                        product_max_seq[product_id] = max(product_max_seq[product_id], int(match.group()))

            for product_id, max_seq in product_max_seq.items():
                product = self.env['product.product'].browse(product_id)
                product.write({'last_seq': max_seq})

        if self.picking_type_id.code == "incoming":
            for line in self.move_ids:
                for move_line in line.move_line_ids:
                    if move_line.lot_id and move_line.lot_id.name:
                        if move_line.lot_id.name.startswith(('DECO-FSR', 'DECO-ASR')):
                            move_line.lot_id.sudo().write({'e_commerce_deliverie':True})

        return res
    
    def generate_serail_number(self):
        for rec in self:
            if rec.picking_type_id.code == "incoming":
                        
                for move in rec.move_ids_without_package:
                    if move.product_id.tracking == 'serial':
                        for line in move.move_line_ids:
                            line.lot_name =  False

                last_seq_list = []
                for move in rec.move_ids_without_package:
                    if move.product_id.tracking == 'serial':
                        product_rec = self.env['product.product'].search([('id', '=', move.product_id.id)])
                        last_seq = product_rec.last_seq or 0
                        lot_rec = self.env['stock.lot'].sudo().search([('product_id', '=', product_rec.id),('name', '!=', False)],order="name desc",limit=1)
                    
                        if lot_rec and lot_rec.name:
                            match = re.search(r'\d+$', lot_rec.name[-5:])
                            if match:
                                if product_rec.last_seq < int(match.group()):
                                    last_seq = int(match.group())
                        if not lot_rec:
                            last_seq = 0
                            
                        for record in last_seq_list:
                            if record['product_id'] == move.product_id.id:
                                last_seq = record['last_seq']
                        last_two_char = date.today().strftime('%Y')[-2:]
                        batch_prefix = f"{product_rec.barcode}Y{last_two_char}"

                        for line in move.move_line_ids:
                            if line.product_id:
                                last_seq += 1
                                batch_no = f"{batch_prefix}{str(last_seq).zfill(5)}"
                                line.write({'lot_name': batch_no})
                        last_seq_list.append({'product_id': line.product_id.id,
                                            'last_seq': last_seq})
                        
    def action_quantity_zero(self):
        for line in self.move_ids_without_package:
            line.write({'quantity': 0})


    def action_assign(self):
        res = super(InheritStockPicking,self).action_assign()
        if self.picking_type_id.code == 'incoming':
            for i in self.move_ids_without_package:
                if i.product_id.tracking == 'lot':
                    for line in i.move_line_ids:
                        company_type = ''
                        if self.company_type == 'DOLPHY INDIA PVT LTD' and self.is_contener:
                            company_type = 'DIPL-IM-'
                        if self.company_type == 'DOLPHY INDIA PVT LTD' and self.is_return:
                            company_type = 'DIPL-SR-'
                        if self.company_type == 'DOLPHIN E-COMMERCE' and self.is_contener:
                            company_type = 'DECO-IM-'
                        if self.company_type == 'DOLPHIN E-COMMERCE' and self.is_return:
                            company_type = 'DECO-SR-'
                            if self.partner_id:
                                company_type = f'DECO-{self.partner_id.name[0].upper()}SR-'
                        if not self.is_contener and not self.is_return:
                            if self.company_type == 'DOLPHY INDIA PVT LTD':
                                company_type = 'DIPL-'
                            if self.company_type == 'DOLPHIN E-COMMERCE':
                                company_type = 'DECO-'
                        line.lot_name = f"{company_type}{str(i.product_id.barcode)}{'-'+str(self.inward_date.strftime('%Y%m%d')) if self.inward_date else ''}"
        return res
    
class InheritStockLot(models.Model):
    _inherit = "stock.lot"

    inward_date = fields.Date(string="Inward Date",tracking=True)
    rate = fields.Float(string="Rate",tracking=True)
    rpt_xls_file = fields.Binary()
    contener_no = fields.Char(string="Container No.")
    e_commerce_deliverie = fields.Boolean(string="E-Commerce Deliverie",default=False)

    def print_report_lot(self):   
        # stock_lots = self.env['stock.lot'].search([('product_id', 'in', self.move_ids_without_package.mapped('product_id').ids),('id', 'in', self.move_ids_without_package.mapped('lot_ids').ids)])
        # return self.env.ref('crm_17.action_serial_lot_report').report_action(stock_lots)

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Barcode')

        center_style = xlwt.easyxf(
            "align: vert centre, horiz centre; font: bold 1; border: top thin, right thin, bottom thin, left thin;"
        )

        data_rec = self.sudo().search([('id','in',self._context.get('active_ids', []))])
        worksheet.col(0).width = 8000 
        worksheet.col(1).width = 8000 
        worksheet.col(2).width = 8000 
        row = 0
        for line in data_rec:

            worksheet.write(row, 0, line.product_id.barcode or "", center_style)

            worksheet.write(row, 1, line.name or "", center_style)

            worksheet.write(row, 2, line.name or "", center_style)

            row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        self.rpt_xls_file = base64.encodebytes(fp.getvalue())

        return {
            'type': 'ir.actions.act_url',
            'name': 'stock.picking',
            'url': '/web/content/stock.lot/%s/rpt_xls_file/barcode_report_excel.xls?download=true' %(self.id),
        }
    
    def action_delete_lot(self):
        pro_list = []
        for lot in self.sudo().search([('id','in',self._context.get('active_ids', []))]):
            if lot.location_id.usage == 'customer':
                raise ValidationError(_(f"You cannot delete this {lot.name} lot because it is used in a Delivery."))
            stock_quants = self.env['stock.quant'].sudo().search([('lot_id', '=', lot.id)])
            stock_quants.sudo().unlink()
            if lot.product_id not in pro_list:
                pro_list.append(lot.product_id)
            lot.unlink()
        if pro_list:
            for line in pro_list:
                lot_rec = self.env['stock.lot'].sudo().search([('product_id', '=', line.id),('name', '!=', False)], order='name desc', limit=1)
            
                if lot_rec and lot_rec.name:
                    match = re.search(r'\d+$', lot_rec.name[-5:])
                    line.product_tmpl_id.last_seq = int(match.group())
                else:
                    line.product_tmpl_id.last_seq = 0

class InheritStockMove(models.Model):
    _inherit = "stock.move"

    number_box = fields.Char(string="Number Of Box")
    box_qty = fields.Integer(string="Box Quantity")
    print_ok = fields.Boolean(related='product_id.print_ok')
    remarks = fields.Char(string='Remarks')
    location_ids = fields.Many2many('stock.location',string="Sources Location")
    purchase_id = fields.Many2one('purchase.order',string="PO")
    tracking = fields.Selection(related='product_id.tracking')
    image_128 = fields.Image(related='product_id.image_128',string="Image")

    def action_view_po_lot(self):
        if self.purchase_line_id.order_id:
            po_id = self.purchase_line_id.order_id
            lot_product_line = po_id.lot_line_ids.filtered(lambda x: x.product_id.id == self.product_id.id)
            
            if lot_product_line:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Lot Product Line',
                    'view_mode': 'form',
                    'res_model': 'lot.product.line',
                    'res_id': lot_product_line[0].id,
                    'context': {
                        'create': False,
                        'form_view_ref': 'crm_17.view_lot_product_line_form'
                    }
                }
        return False

    # def action_lot_number(self):
    #     for move in self:
    #         product = move.product_id

    #         quants = self.env['stock.quant'].search([
    #             ('product_id', '=', product.id),
    #             ('quantity', '>', 0),
    #             ('lot_id', '!=', False),
    #         ])
    #         for quant in quants:
    #             already_added = move.move_line_ids.filtered(lambda ml: ml.lot_id == quant.lot_id)
    #             if already_added:
    #                 continue

    #             self.env['stock.move.line'].create({
    #                 'move_id': move.id,
    #                 'product_id': product.id,
    #                 'product_uom_id': move.product_uom.id,
    #                 'location_id': move.location_id.id,
    #                 'location_dest_id': move.location_dest_id.id,
    #                 'lot_id': quant.lot_id.id,
    #                 'quantity': min(quant.quantity, move.product_uom_qty),
    #             })

    #         return True

    def action_lot_number(self):
        for move in self:
            product = move.product_id

            existing_serial_lines = move.move_line_ids.filtered(lambda ml: ml.lot_id and ml.quantity == 1.0)
            qty_needed = int(move.product_uom_qty) - len(existing_serial_lines)
            if qty_needed <= 0:
                continue

            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('quantity', '>=', 1),
                ('lot_id', '!=', False),
            ])

            used_lot_ids = existing_serial_lines.mapped('lot_id').ids

            for quant in quants:
                if qty_needed <= 0:
                    break

                if quant.lot_id.id in used_lot_ids:
                    continue

                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'product_id': product.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'lot_id': quant.lot_id.id,
                    'quantity': 1.0,
                })

                qty_needed -= 1

        return True

    @api.depends('move_line_ids')
    def _compute_move_lines_count(self):
        res = super(InheritStockMove,self)._compute_move_lines_count()
        for pic in self:
            pic.location_ids = pic.move_line_ids.mapped('location_id').ids
        return res
    
    def generate_serial_numbers_last_seq(self):
        for rec in self:
            product_rec = self.env['product.product'].search([('id', '=', rec.product_id.id)])
            last_seq = product_rec.last_seq or 0
            
            lot_rec = self.env['stock.lot'].sudo().search([('product_id', '=', product_rec.id),('name', '!=', False)],order="name desc",limit=1)
           
            if lot_rec and lot_rec.name:
                match = re.search(r'\d+$', lot_rec.name[-5:])
                if match:
                    if product_rec.last_seq < int(match.group()):
                        last_seq = int(match.group())
            if not lot_rec:
                last_seq = 0

            last_two_char = date.today().strftime('%Y')[-2:]
            batch_prefix = f"{product_rec.barcode}Y{last_two_char}"
            picking_rec = self.env['stock.picking'].search([('move_ids_without_package', '=', rec.id)])
            
            for line in rec.move_line_ids:
                line.lot_name =  False

            picking_rec = self.env['stock.picking'].search([('move_ids_without_package', '=', rec.id)])
            for pic in picking_rec.move_ids_without_package.filtered(lambda x: x.product_id.id == rec.product_id.id):
                for line in pic.move_line_ids:
                    if line.product_id:
                        last_seq += 1
                        batch_no = f"{batch_prefix}{str(last_seq).zfill(5)}"
                        line.write({'lot_name': batch_no})

class InheritStockMoveLine(models.Model):
    _inherit = "stock.move.line"

    pi_chr = fields.Char(related='move_id.picking_id.pi_chr')
    company_type = fields.Selection(related='move_id.picking_id.company_type')
    remarks = fields.Char(related='move_id.picking_id.remarks')
    barcode = fields.Char(related='product_id.barcode')
    contener_no = fields.Char(related='move_id.picking_id.contener_no')
    stock_type = fields.Selection([('sale', 'Sale'),('purchase', 'Purchase'), ('return', 'Return')],string="Type",compute='_compute_stock_type',store=True)

    @api.depends('picking_id', 'picking_id.is_return', 'picking_code')
    def _compute_stock_type(self):
        for line in self:
            line.stock_type = False 
            picking = line.picking_id
            code = line.picking_code

            if not code:
                continue 
            
            if code == 'incoming':
                if picking and (picking.is_return or picking.return_id):
                    line.stock_type = 'return'
                else:
                    line.stock_type = 'purchase'
            elif code == 'outgoing':
                line.stock_type = 'sale'

    def _prepare_new_lot_vals(self):
        self.ensure_one()
        picking_id = self.picking_id
        return {
            'name': self.lot_name,
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
            'inward_date': picking_id.inward_date,
            'ref': picking_id.invoice_no,
            'note': picking_id.company_name,
            'contener_no': picking_id.contener_no,
        }
    
    def _action_done(self):
        """ This method is called during a move's `action_done`. It'll actually move a quant from
        the source location to the destination location, and unreserve if needed in the source
        location.

        This method is intended to be called on all the move lines of a move. This method is not
        intended to be called when editing a `done` move (that's what the override of `write` here
        is done.
        """

        # First, we loop over all the move lines to do a preliminary check: `quantity` should not
        # be negative and, according to the presence of a picking type or a linked inventory
        # adjustment, enforce some rules on the `lot_id` field. If `quantity` is null, we unlink
        # the line. It is mandatory in order to free the reservation and correctly apply
        # `action_done` on the next move lines.
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_delete = OrderedSet()
        ml_ids_to_create_lot = OrderedSet()
        ml_ids_to_check = defaultdict(OrderedSet)

        for ml in self:
            # Check here if `ml.quantity` respects the rounding of `ml.product_uom_id`.
            uom_qty = float_round(ml.quantity, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            quantity = float_round(ml.quantity, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, quantity, precision_digits=precision_digits) != 0:
                raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision '
                                  'defined on the unit of measure "%s". Please change the quantity done or the '
                                  'rounding precision of your unit of measure.',
                                  ml.product_id.display_name, ml.product_uom_id.name))

            qty_done_float_compared = float_compare(ml.quantity, 0, precision_rounding=ml.product_uom_id.rounding)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking == 'none':
                    continue
                picking_type_id = ml.move_id.picking_type_id
                if not picking_type_id and not ml.is_inventory and not ml.lot_id:
                    ml_ids_tracked_without_lot.add(ml.id)
                    continue
                if not picking_type_id or ml.lot_id or (not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots):
                    # If the user disabled both `use_create_lots` and `use_existing_lots`
                    # checkboxes on the picking type, he's allowed to enter tracked
                    # products without a `lot_id`.
                    continue
                if picking_type_id.use_create_lots:
                    ml_ids_to_check[(ml.product_id, ml.company_id)].add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)

            elif qty_done_float_compared < 0:
                raise UserError(_('No negative quantities allowed'))
            elif not ml.is_inventory:
                ml_ids_to_delete.add(ml.id)

        for (product, company), mls in ml_ids_to_check.items():
            mls = self.env['stock.move.line'].browse(mls)
            lots = self.env['stock.lot'].search([
                ('company_id', '=', company.id),
                ('product_id', '=', product.id),
                ('name', 'in', mls.mapped('lot_name')),
            ])
            lots = {lot.name: lot for lot in lots}
            for ml in mls:
                lot = lots.get(ml.lot_name)
                if lot:
                    ml.lot_id = lot.id
                elif ml.lot_name:
                    ml_ids_to_create_lot.add(ml.id)
                else:
                    ml_ids_tracked_without_lot.add(ml.id)


        if ml_ids_tracked_without_lot:
            mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
            raise UserError(_('You need to supply a Lot/Serial Number for product: \n - ') +
                              '\n - '.join(mls_tracked_without_lot.mapped('product_id.display_name')))
        ml_to_create_lot = self.env['stock.move.line'].browse(ml_ids_to_create_lot)
        if ml_ids_to_create_lot:
            ml_to_create_lot.with_context(bypass_reservation_update=True)._create_and_assign_production_lot()

        mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
        mls_to_delete.unlink()

        mls_todo = (self - mls_to_delete)
        mls_todo._check_company()

        # Now, we can actually move the quant.
        ml_ids_to_ignore = OrderedSet()

        quants_cache = self.env['stock.quant']._get_quants_cache_by_products_locations(mls_todo.product_id, mls_todo.location_id | mls_todo.location_dest_id, extra_domain=['|', ('lot_id', 'in', mls_todo.lot_id.ids), ('lot_id', '=', False)])

        for ml in mls_todo.with_context(quants_cache=quants_cache):
            # if this move line is force assigned, unreserve elsewhere if needed
            ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id, action="reserved")
            available_qty, in_date = ml._synchronize_quant(-ml.quantity_product_uom, ml.location_id)
            ml._synchronize_quant(ml.quantity_product_uom, ml.location_dest_id, package=ml.result_package_id, in_date=in_date)
            
            # if available_qty < 0:
                # print("*******available_qty****",available_qty,ml.product_id.name, ml.location_id.name,ml.lot_id.name)
                # ml._free_reservation(
                #     ml.product_id, ml.location_id,
                #     abs(available_qty), lot_id=ml.lot_id, package_id=ml.package_id,
                #     owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
            ml_ids_to_ignore.add(ml.id)
        # Reset the reserved quantity as we just moved it to the destination location.
        mls_todo.write({
            'date': fields.Datetime.now(),
        })


class InheritStockLocation(models.Model):
    _inherit = "stock.location"
        
    sequence = fields.Integer(string="Sequence")

class InheritStockQuant(models.Model):
    _inherit = "stock.quant"

    lot_name = fields.Char(related="lot_id.name", store=True)
            
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        order = 'lot_name asc'
        return super()._search(domain, offset, limit, order, access_rights_uid)
        