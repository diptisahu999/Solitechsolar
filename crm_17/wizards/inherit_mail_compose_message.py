from odoo import api, fields, models

class inheritMailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    email_cc = fields.Char("Cc")

    # @api.depends('composition_mode', 'model', 'parent_id', 'res_domain','res_ids', 'template_id')
    # def _compute_partner_ids(self):
    #     res = super(inheritMailComposeMessage, self)._compute_partner_ids()
    #     for wizard in self:
    #         if self.env.context.get('active_model') == 'sale.order':
    #             sale_partner = self.env.ref('crm_17.sale_quotation_email_partner')
    #             wizard.partner_ids = [(4, sale_partner.id)] 

    #     return res

    def action_send_mail(self):
        res = super(inheritMailComposeMessage, self).action_send_mail()
        sale_ids = self._context.get('active_ids', [])
        sale_rec = self.env['sale.order'].search([('id', 'in', sale_ids)])
        mail_rec = self.env['mail.mail'].search([('model', '=', 'sale.order'),('res_id', 'in', sale_ids)],order='id desc',limit=1)
        if mail_rec:
            combined_cc = self.email_cc or ""
            if sale_rec and sale_rec.user_id and sale_rec.user_id.login:
                if combined_cc:
                    combined_cc += ',' + sale_rec.user_id.login
                else:
                    combined_cc = sale_rec.user_id.login
            mail_rec.sudo().write({'email_cc': combined_cc})
        return res