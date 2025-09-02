from odoo import api, fields, models

class inheritStockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        new_picking_id, pick_type_id = super()._create_returns()

        picking = self.env['stock.picking'].browse(self.picking_id.id)
        if picking.picking_type_id.code == 'incoming':
            new_picking = self.env['stock.picking'].browse(new_picking_id)
            new_picking.write({
                'invoice_no': picking.invoice_no,
                'company_type': picking.company_type,
                'inward_date': picking.inward_date,
                'contener_no': picking.contener_no,
            })

        return new_picking_id, pick_type_id