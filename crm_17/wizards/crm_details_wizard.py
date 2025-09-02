from odoo import api, models, fields
from datetime import date,datetime
class CRMDetailsWizard(models.TransientModel):
    _name = 'crm.details.wiz'
    _description= "Crm Details Wizard"

    type_details = fields.Selection([('Label', 'Label'), ('Source', 'Source'),('Stage', 'Stage'), ('Tags', 'Tags'), ('Sales_Team', 'Sales Team'), ('City', 'City'), ('Interest', 'Interest'), ('State', 'State')],string='Select Field')
    label_ids = fields.Many2many('label.mst',string="Labels")
    source_id = fields.Many2one('utm.source',string="Source")
    stage_id = fields.Many2one('crm.stage',string="Stage")
    team_id = fields.Many2one('crm.team',string="Sales Team")
    tag_ids = fields.Many2many('crm.tag',string="Tags")
    city = fields.Char(string="City")
    city_id = fields.Many2one('city.mst',string="City ")
    state_id = fields.Many2one('res.country.state',string="State")
    interest_id = fields.Many2one('interest.mst',string='Interest')

    def action_confirm(self):
        if self.env.context.get('model', False) == 'crm.lead':
            record = self.env['crm.lead'].sudo().search([('id', 'in', self.env.context['id'])])
            for line in record:
                if self.type_details == 'Label':
                    line.sudo().write({'label_ids': [(4, id_) for id_ in self.label_ids.ids]})
                if self.type_details == 'Source':
                    line.sudo().write({'source_id': self.source_id.id})
                if self.type_details == 'Stage':
                    line.sudo().write({'stage_id': self.stage_id.id})
                if self.type_details == 'Tags':
                    line.sudo().write({'tag_ids': [(4, id_) for id_ in self.tag_ids.ids]})
                if self.type_details == 'Sales_Team':
                    line.sudo().write({'team_id': self.team_id.id})
                if self.type_details == 'City':
                    line.sudo().write({'city': self.city_id.name if self.city_id else ""})
                if self.type_details == 'Interest':
                    line.sudo().write({'interest_id': self.interest_id.id})
                if self.type_details == 'State':
                    line.sudo().write({'state_id': self.state_id.id})

class CrmLeadLostStage(models.TransientModel):
    _name = 'crm.lead.lost.stage'
    _description = 'Get Lost Reason Stage'

    lost_reason_id = fields.Many2one('crm.lost.reason', 'Lost Reason')

    def action_lost_reason_apply(self):
        if self.env.context.get('active_model', False) == 'crm.lead':
            record = self.env['crm.lead'].sudo().search([('id', '=', self.env.context.get('active_id'))])
            lost_stage = self.env['crm.stage'].sudo().search([('is_lost', '=', True)],limit=1)
            if record:
                record.sudo().write({'stage_id':lost_stage.id,'lost_reason_id':self.lost_reason_id.id})

class PartnerDetailsWizard(models.TransientModel):
    _name = 'partner.details.wiz'
    _description= "Partner Details Wizard"

    city_id = fields.Many2one('city.mst',string="City")

    def action_confirm(self):
        if self.env.context.get('model', False) == 'res.partner':
            record = self.env['res.partner'].sudo().search([('id', 'in', self.env.context['id'])])
            for line in record:
                line.sudo().write({'city_id':self.city_id.id,'city':self.city_id.name})
                if line.opportunity_ids:
                    for lead in line.opportunity_ids:
                        lead.sudo().write({'city':self.city_id.name})
