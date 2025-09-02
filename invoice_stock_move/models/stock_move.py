from odoo import models
from odoo import models, fields, api
from odoo.tools import float_is_zero, float_compare
import re

class InheritStockMove(models.Model):
    _inherit = 'stock.move'


    def _action_assign(self, force_qty=False):
        """Reserve stock moves without repeatedly updating the quantity of stock move lines."""
        for rec in self:
            if rec.picking_id.picking_type_code == 'outgoing':

                account_move = self.env['account.move'].sudo().search(['|',('invoice_picking_id', '=', rec.picking_id.id),('name', '=', rec.picking_id.origin)])
                reserved_stock = self.env['reserved.stock'].search([('account_id', '=', account_move.id)])
                if reserved_stock:
                    reserved_stock.sudo().write({'reserved_type':'unreserved'})

                StockMove = self.env['stock.move']
                assigned_moves_ids = set()
                partially_available_moves_ids = set()
                move_line_vals_list = []

                roundings = {move: move.product_id.uom_id.rounding for move in self}
                moves_to_redirect = set()
                moves_to_assign = self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available'])

                for move in moves_to_assign:
                    rounding = roundings[move]
                    existing_reserved_qty = sum(move.move_line_ids.mapped('quantity'))  # Already reserved quantity
                    missing_qty = move.product_uom_qty - existing_reserved_qty

                    if float_compare(missing_qty, 0, precision_rounding=rounding) <= 0:
                        assigned_moves_ids.add(move.id)
                        continue  # Skip if already reserved

                    missing_qty_uom = move.product_uom._compute_quantity(missing_qty, move.product_id.uom_id, rounding_method='HALF-UP')

                    available_quants = self.env['stock.quant'].search([
                        ('product_id', '=', move.product_id.id),
                        ('location_id.usage', '=', 'internal'),
                        ('quantity', '>', 0)
                    ]).filtered(lambda q: q.location_id.location_id)  # Fetch from largest available stock first
                    # , order="id asc"
                    def extract_number_before_y(lot_name):
                        match = re.search(r'(\d+)Y', lot_name or '')
                        return int(match.group(1)) if match else float('inf')  # 'inf' so unmatched go last

                    # available_quants = available_quants.sorted(lambda q: (q.lot_id.name or ''), reverse=False)

                    available_quants = available_quants.sorted(
                        key=lambda q: (
                            not ((q.lot_id.name or '').startswith('DIPL-') or (q.lot_id.name or '').startswith('DECO-')),
                            q.lot_id.name or ''
                        )
                    )
                                        
                    # available_quants = available_quants.sorted(key=lambda q: extract_number_before_y(q.lot_id.name))

                    need = missing_qty_uom
                    used_lots = set()  # ✅ Track used serial numbers

                    for quant in available_quants:
                        if float_is_zero(need, precision_rounding=rounding):
                            break
                        
                        # reserved_stock = self.env['reserved.stock'].search([('product_id', '=', move.product_id.id),('reserved_type', '=', 'reserved')])
                        # if reserved_stock:
                        #     take_qty = min(need, (quant.quantity - sum(reserved_stock.mapped('reserved_qty'))))
                        # else:
                        take_qty = min(need, quant.quantity)

                        # ✅ Ensure serial numbers are unique
                        if move.product_id.tracking == 'serial' and quant.lot_id:
                            if quant.lot_id.id in used_lots:
                                continue  # Skip if lot already used
                            used_lots.add(quant.lot_id.id)  # Mark this serial number as used

                        # ✅ Check if a move line already exists for the same move, location & lot
                        existing_move_line = move.move_line_ids.filtered(
                            lambda ml: ml.location_id == quant.location_id
                            and ml.location_dest_id == move.location_dest_id
                            and ml.lot_id == quant.lot_id
                        )

                        if existing_move_line:
                            # ✅ Update quantity ONLY IF it's lower than required, not every time
                            if float_compare(existing_move_line.quantity, take_qty, precision_rounding=rounding) < 0:
                                existing_move_line.quantity = take_qty  # Ensure it does not over-update
                        else:
                            # ✅ Create new move line only if it does NOT exist
                            move_line_vals = {
                                'move_id': move.id,
                                'product_id': move.product_id.id,
                                'location_id': quant.location_id.id,  # ✅ Any location, not just move.location_id
                                'location_dest_id': move.location_dest_id.id,
                                'product_uom_id': move.product_uom.id,
                                'quantity': 1 if move.product_id.tracking == 'serial' else take_qty,  # ✅ 1 per serial number
                                'lot_id': quant.lot_id.id if quant.lot_id else False,
                            }
                            move_line_vals_list.append(move_line_vals)

                        need -= take_qty

                    if float_is_zero(need, precision_rounding=rounding):
                        assigned_moves_ids.add(move.id)
                    else:
                        partially_available_moves_ids.add(move.id)

                if move_line_vals_list:
                    self.env['stock.move.line'].create(move_line_vals_list)  # ✅ Create only new move lines (not update)

                StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
                StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

                if not self.env.context.get('bypass_entire_pack'):
                    self.picking_id._check_entire_pack()

                StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()
            
        return super(InheritStockMove, self)._action_assign(force_qty=force_qty)

class InheritStockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model
    def create(self, vals):
        move_id = vals.get('move_id')
        lot_id = vals.get('lot_id')

        if move_id and lot_id:
            move = self.env['stock.move'].browse(move_id)
            picking = move.picking_id

            if picking.picking_type_code == 'outgoing':
                lot = self.env['stock.lot'].browse(lot_id)

                if not picking.e_commerce_deliverie and lot.e_commerce_deliverie:
                    return self.env['stock.move.line']

        res = super(InheritStockMoveLine, self).create(vals)
        return res