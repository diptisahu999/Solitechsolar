from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class inheritLead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    _description = 'Convert Lead to Opportunity (not in mass)'

    referred = fields.Char(string="Referred By")

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            self.referred = self.lead_id.user_id.name

    def action_apply(self):
        res = super(inheritLead2OpportunityPartner, self).action_apply()
        self.lead_id.referred = self.referred
        return res
    
    @api.depends('duplicated_lead_ids')
    def _compute_name(self):
        for convert in self:
            if not convert.name:
                # convert.name = 'merge' if convert.duplicated_lead_ids and len(convert.duplicated_lead_ids) >= 2 else 'convert'
                convert.name = 'convert'

    @api.depends('lead_id')
    def _compute_action(self):
        for convert in self:
            # if not convert.lead_id:
            #     convert.action = 'nothing'
            # else:
            #     partner = convert.lead_id._find_matching_partner()
            #     if partner:
            #         convert.action = 'exist'
            #     elif convert.lead_id.contact_name:
            #         convert.action = 'create'
            #     else:
            #         convert.action = 'nothing'
            convert.action = 'create'