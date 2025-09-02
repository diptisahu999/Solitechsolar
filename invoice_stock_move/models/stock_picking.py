from odoo import models
from odoo import models, fields, api
from odoo.tools import float_is_zero, float_compare

class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    invoices_count = fields.Integer(string="invoices Count", copy=False,help="Count of the created picking for invoices")

    @api.depends('return_ids')
    def _compute_return_count(self):
        res = super(InheritStockPicking, self)._compute_return_count()
        for line in self:
            line.invoices_count = len(self.env['account.move'].search(['|',('invoice_picking_id', '=', line.id),('name', '=', line.origin)]))
        return res
        
    def action_view_invoices(self):
        action = self.sudo().env.ref('account.action_move_out_invoice_type')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        result['domain'] = ['|',('invoice_picking_id', '=', self.id),('name', '=', self.origin)]

        account_move = self.env['account.move'].sudo().search(['|',('invoice_picking_id', '=', self.id),('name', '=', self.origin)])

        if len(account_move) == 1:
            res = self.sudo().env.ref('account.view_move_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = account_move.id or False
        else:
            return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', account_move.ids)],
            'context': {'create': False}
            }

        return result