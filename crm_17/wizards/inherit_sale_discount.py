from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class inheritDiscountWizard(models.TransientModel):
    _inherit = 'sale.order.discount'
    _description = 'Discount Wizard'

    def action_apply_discount(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        if self.discount_type == 'sol_discount':
            self.sale_order_id.order_line.filtered(lambda x: x.product_id.type != 'service' and x.product_id.no_discount_ok != True).write({'discount': self.discount_percentage*100})
        else:
            self._create_discount_lines()

    @api.onchange('discount_type','discount_percentage')
    def _onchange_discount_type(self):
        sale_per = self.env['ir.config_parameter'].sudo().get_param('saleperson_per')
        sale_per = float(sale_per)
        if self.discount_type == 'sol_discount':
            if self.env.user.has_group('sales_team.group_sale_salesman') and not self.user_has_groups('sales_team.group_sale_salesman_all_leads') and not self.user_has_groups('sales_team.group_sale_manager'):
                if sale_per and self.discount_percentage:
                    if self.discount_percentage * 100 > sale_per:
                        raise UserError("Not Allowed: Discount exceeds %s%%" % sale_per)