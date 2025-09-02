from odoo import api, fields, models,_
from odoo.exceptions import UserError

class SparePartsProduction(models.Model):
    _name = "spare.parts.production"
    _inherit = ['mail.thread']
    _description= "Spare Parts Production"

    name = fields.Char('Reference', default='New',copy=False, index='trigram', readonly=True)
    stage = fields.Selection([('draft', 'Draft'), ('done', 'Done')],string='Stage',default="draft",tracking=True)
    date = fields.Datetime(string='Date',tracking=True)
    product_id = fields.Many2one('product.product',string="Product",tracking=True)
    qty = fields.Float(string="Quantity",tracking=True)
    product_uom = fields.Many2one('uom.uom',string="Unit",tracking=True)
    lot_ids = fields.Many2many('stock.lot','spare_lot_ids',string="Lots",tracking=True)
    available_lot_ids = fields.Many2many('stock.lot','available_spare_lot_ids',string="Lots")
    pro_des_location_id = fields.Many2one('stock.location',string="Temp Location",tracking=True)
    spa_des_location_id = fields.Many2one('stock.location',string="Spare Location",tracking=True)
    company_id = fields.Many2one("res.company", string="Company",required=True, default=lambda self: self.env.company.id)

    line_ids = fields.One2many('spare.parts.production.line','mst_id',string="Line")
    
    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('spare.parts.production') or _('New')
        res = super(SparePartsProduction, self).create(vals)
        
        return res
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom = self.product_id.uom_id.id
        self.lot_ids = False
        quants = self.env['stock.quant'].sudo().search([('product_id', '=', self.product_id.id),('quantity', '>', 0),('lot_id', '!=', False),('location_id.usage', '=', 'internal')])
        lot_ids = quants.mapped('lot_id')
        self.available_lot_ids = lot_ids

    def action_done_spare(self):
        if self.qty <= 0:
            raise UserError("Quantity must be greater than 0.")
        self._create_stock_picking_receipts()
        self._create_stock_picking_deliveries()
        self.stage = 'done'

    def _create_stock_picking_receipts(self):
        picking_types = self.env['stock.picking.type'].sudo().search([('code', '=', 'incoming'),('company_id', '=', self.company_id.id)],limit=1)
        location_id = self.env['stock.location'].sudo().search([('usage','=','supplier')],limit=1)
        # location_dest_id = picking_types.default_location_dest_id.id

        line_list = []
        for line in self.line_ids:
            line_list.append((0,0,{
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'quantity': line.qty,
                'product_uom_qty': line.qty,
                'location_id': location_id.id,
                'location_dest_id': self.spa_des_location_id.id,
                'company_id': line.company_id.id,
                'picking_type_id': picking_types.id,
                'route_ids': 1 and [
                    (6, 0, [x.id for x in self.env['stock.rule'].sudo().search(
                        [('id', 'in', (2, 3))])])] or [],
                'warehouse_id': picking_types.warehouse_id.id,
            }))

        if line_list:
            pick = {
                'picking_type_id': picking_types.id,
                'origin': self.name,
                'location_dest_id': self.spa_des_location_id.id,
                'location_id': location_id.id,
                'move_type': 'direct',
                'move_ids_without_package': line_list,
                'company_id': self.company_id.id,
                'picking_type_code': 'incoming',
                'spare_parts_id': self.id
                    }
            picking_rec = self.env['stock.picking'].sudo().create(pick)
            if picking_rec:
                self.env.context = dict(self.env.context, skip_backorder=True)
                picking_rec.sudo().action_confirm()
                picking_rec.sudo().button_validate()

    def _create_stock_picking_deliveries(self):
        picking_types = self.env['stock.picking.type'].sudo().search([('code', '=', 'outgoing'),('company_id', '=', self.company_id.id)],limit=1)

        # location_dest_id = self.env['stock.location'].sudo().search([('usage','=','customer')],limit=1)
        location_dest_id = self.env['stock.location'].sudo().search([('usage','=','view'),('name', '=', 'Virtual Locations')],limit=1)

        # location_id = self.env['stock.location'].sudo().search([('usage','=','inventory')],limit=1)
        location_id = self.lot_ids.mapped('location_id')
        
        move_line_list = []
        total_qty = 0.0
        for lot in self.lot_ids:
            quant_rec = self.env['stock.quant'].search([('location_id', '=', lot.location_id.id),('lot_id', '=', lot.id),('product_id', '=', lot.product_id.id)], limit=1)
            move_line_list.append((0, 0, {
                'product_id': lot.product_id.id,
                'lot_id': lot.id,
                'quantity': quant_rec.quantity,
                'location_id': quant_rec.location_id.id,
                'location_dest_id': self.pro_des_location_id.id,
            }))

            total_qty += quant_rec.quantity

        line_list = [(0, 0, {
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'quantity': total_qty,
            'product_uom_qty': total_qty,
            'location_id': move_line_list[0][2]['location_id'], 
            'location_dest_id': self.pro_des_location_id.id,
            'company_id': self.company_id.id,
            'picking_type_id': picking_types.id,
            'lot_ids': [(6, 0, self.lot_ids.ids)],
            'move_line_ids': move_line_list,
            'warehouse_id': picking_types.warehouse_id.id,
        })]
        if line_list:
            pick = {
                'picking_type_id': picking_types.id,
                'origin': self.name,
                'location_dest_id': self.pro_des_location_id.id,
                'location_id': location_id[0].id,
                'move_type': 'direct',
                'move_ids_without_package': line_list,
                'company_id': self.company_id.id,
                'picking_type_code': 'outgoing',
                'spare_parts_id': self.id
                    }
            picking_rec = self.env['stock.picking'].sudo().create(pick)
            if picking_rec:
                self.env.context = dict(self.env.context, skip_backorder=True)
                picking_rec.sudo().action_confirm()
                picking_rec.sudo().button_validate()

class SparePartsProductionLine(models.Model):
    _name = "spare.parts.production.line"
    _description= "Spare Parts Production Line"

    mst_id = fields.Many2one('spare.parts.production', string="Mst")

    product_id = fields.Many2one('product.product',string="Product")
    qty = fields.Float(string="Quantity")
    product_uom = fields.Many2one('uom.uom',string="Unit")
    company_id = fields.Many2one("res.company", string="Company",required=True, default=lambda self: self.env.company.id)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_uom = self.product_id.uom_id.id