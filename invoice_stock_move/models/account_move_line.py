from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _create_stock_moves(self, picking):
        """Function to create stock move"""
        done = self.env['stock.move'].browse()
        for line in self:
            price_unit = line.price_unit
            stock_quant_rec = self.env['stock.quant'].search([('product_id', '=',line.product_id.id),('location_id.usage', '!=', 'customer')])  
            stock_quant = False
            for stock in stock_quant_rec:
                if stock and stock.available_quantity > 0:
                    stock_quant = stock
            if picking.picking_type_id.code == 'outgoing':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    # 'location_id': stock_quant.location_id.id if stock_quant else picking.picking_type_id.default_location_src_id.id,
                    'location_id':  picking.picking_type_id.default_location_src_id.id,
                    'location_dest_id': line.move_id.partner_id.
                    property_stock_customer.id,
                    'picking_id': picking.id,
                    'state': 'draft',
                    'company_id': line.move_id.company_id.id,
                    'price_unit': price_unit,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.rule'].search
                        ([('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                    'remarks':line.remarks
                }

            if picking.picking_type_id.code == 'incoming':
                template = {
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'location_id': line.move_id.partner_id.
                    property_stock_supplier.id,
                    'location_dest_id': picking.picking_type_id.
                    default_location_dest_id.id,
                    'picking_id': picking.id,
                    'state': 'draft',
                    'company_id': line.move_id.company_id.id,
                    'price_unit': price_unit,
                    'picking_type_id': picking.picking_type_id.id,
                    'route_ids': 1 and [
                        (6, 0, [x.id for x in self.env['stock.rule'].search(
                            [('id', 'in', (2, 3))])])] or [],
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                    'remarks':line.remarks
                }
            diff_quantity = line.quantity
            tmp = template.copy()
            tmp.update({
                'product_uom_qty': diff_quantity,
            })
            template['product_uom_qty'] = diff_quantity
            done += self.env['stock.move'].create(template)
        return done
