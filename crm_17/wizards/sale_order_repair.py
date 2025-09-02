from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError, UserError

class SaleOrderRepair(models.TransientModel):
    _name = 'sale.order.repair.wiz'
    _description = "Sale Quotations Create from Repair"

    date = fields.Datetime(string="Date",default=fields.Datetime.now)

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderRepair, self).default_get(fields)
        repair_order = self.env['repair.order'].sudo().search([('id', 'in', self.env.context['ids'])])
        if repair_order:

            # 1. Check if all repair orders have the same customer
            partner_ids = repair_order.mapped('partner_id.id')
            if len(set(partner_ids)) > 1:
                ref_str = "\n".join(f"{ro.name} → {ro.partner_id.name}" for ro in repair_order)
                raise UserError(_("All selected repair orders must have the same customer.\nConcerned repair orders:\n") + ref_str)
            
            # 2. Check for unconfirmed repair orders
            unconfirmed = repair_order.filtered(lambda ro: ro.state == 'draft')
            if unconfirmed:
                ref_str = "\n".join(ro.name for ro in unconfirmed)
                raise UserError(_("Draft Repair Orders are not allowed:\n%s") % ref_str)

            # 3. Check if any are already linked to sale orders
            already_linked = repair_order.filtered(lambda ro: ro.sale_order_id and ro.sale_order_id.state != 'cancel')
            if already_linked:
                ref_str = "\n".join(ro.name for ro in already_linked)
                raise UserError(_("You cannot create a quotation for a repair order that is already linked to an existing sale order.\nConcerned repair order(s):\n") + ref_str)

            # 4. Check for repair orders without customer
            no_customer = repair_order.filtered(lambda ro: not ro.partner_id)
            if no_customer:
                ref_str = "\n".join(ro.name for ro in no_customer)
                raise UserError(_("You need to define a customer for a repair order in order to create an associated quotation.\nConcerned repair order(s):\n") + ref_str)

        return res

    def action_create_quotations(self):
        repair_orders = self.env['repair.order'].sudo().search([('id', 'in', self.env.context.get('ids', []))])

        grouped_lines = {}
        for repair in repair_orders:
            for move in repair.move_ids:
                if move.sale_line_id or move.repair_line_type != 'add':
                    continue

                product_id = move.product_id.id
                product = move.product_id
                qty = move.product_uom_qty if repair.state != 'done' else move.quantity

                if product_id in grouped_lines:
                    grouped_lines[product_id]['product_uom_qty'] += qty
                    grouped_lines[product_id]['move_ids'].append(Command.link(move.id))
                else:
                    price_unit = 0.0 if repair.under_warranty else move.price_unit or 0.0
                    grouped_lines[product_id] = {
                        'product_id': product_id,
                        'product_uom_qty': qty,
                        'price_unit': product.list_price,
                        'move_ids': [Command.link(move.id)],
                    }

        if not grouped_lines:
            raise UserError("No valid move lines found to create sale order lines.")

        # Build sale order line commands
        order_lines = [Command.create(line_vals) for line_vals in grouped_lines.values()]

        # Create a single sale order
        first = repair_orders[0]
        sale_order_vals = {
            "date_order": self.date,
            "company_id": first.company_id.id,
            "partner_id": first.partner_id.id,
            "warehouse_id": first.picking_type_id.warehouse_id.id,
            "repair_order_ids": [Command.link(ro.id) for ro in repair_orders],
            "order_line": order_lines,
        }

        sale_order = self.env['sale.order'].create(sale_order_vals)
        if sale_order:
            for line in sale_order.order_line:
                line.onchange_sake_product_image()
            return self.action_view_sale_order(sale_order)
    
    def action_view_sale_order(self,sale_order):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": sale_order.id,
        }
    
class OldProductSerialWiz(models.TransientModel):
    _name = 'old.product.serial.wiz'
    _description = "Old Product Serial Wiz"

    serial_name = fields.Char(string="Serial")

    def action_genrate_searial(self):
        repair_order = self.env['repair.order'].sudo().search([('id', '=', self.env.context['active_id'])])

        picking_types = self.env['stock.picking.type'].sudo().search([('code', '=', 'incoming'),('company_id', '=', repair_order.company_id.id)],limit=1)
        location_id = self.env['stock.location'].sudo().search([('usage','=','supplier')],limit=1)
        location_dest_id = self.env['stock.location'].sudo().search([('name', '=', 'Repair Location'),('usage','=','internal')],limit=1)

        line_list = []
        move_line_list = []

        move_line_list.append((0, 0, {
                'product_id': repair_order.product_id.id,
                'lot_name': self.serial_name,
                'quantity': 1,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
            }))
        line_list.append((0,0,{
            'name': repair_order.product_id.name,
            'product_id': repair_order.product_id.id,
            'product_uom': repair_order.product_uom.id,
            'quantity': 1,
            'product_uom_qty': 1,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'company_id': repair_order.company_id.id,
            'picking_type_id': picking_types.id,
            'move_line_ids': move_line_list,
            'route_ids': 1 and [
                (6, 0, [x.id for x in self.env['stock.rule'].sudo().search(
                    [('id', 'in', (2, 3))])])] or [],
            'warehouse_id': picking_types.warehouse_id.id,
        }))
        if line_list:
            pick = {
                'picking_type_id': picking_types.id,
                'origin': repair_order.name,
                'location_dest_id': location_dest_id.id,
                'location_id': location_id.id,
                'move_type': 'direct',
                'move_ids_without_package': line_list,
                'company_id': repair_order.company_id.id,
                'picking_type_code': 'incoming',
                    }
            picking_rec = self.env['stock.picking'].sudo().create(pick)
            if picking_rec:
                self.env.context = dict(self.env.context, skip_backorder=True)
                picking_rec.sudo().action_confirm()
                picking_rec.sudo().button_validate()

                lot_id = self.env['stock.lot'].sudo().search([('name', '=', self.serial_name),('product_id', '=', repair_order.product_id.id)],limit=1)
                repair_order.sudo().write({'lot_id':lot_id.id,'is_serial_gen':True})