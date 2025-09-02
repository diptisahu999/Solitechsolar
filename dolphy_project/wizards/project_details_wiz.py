from odoo import api, models, fields
from datetime import date,datetime

class ProjectDetailsWizard(models.TransientModel):
    _name = 'project.details.wiz'
    _description= "Project Details Wizard"

    type_field = fields.Selection([('city', 'City'), ('source', 'Source'), ('project_type', 'Project Type'),('stage', 'Stage'),('boq_status', 'BOQ Status')],string='Select Field')
    city_id = fields.Many2one('city.mst',string="City")
    source_id = fields.Many2one('utm.source',string="Source")
    project_type_id = fields.Many2one('res.partner.category',string="Project Type")
    stage_type = fields.Selection([
        ('planning', 'Planning'),
        ('design', 'Design'),
        ('tendering', 'Tendering'),
        ('civil', 'Civil'),
        ('mock_up', 'Mock up'),
        ('finishing', 'Finishing'),
        ('negotiation', 'Negotiation'),
        ('closed_won', 'Closed Won'),
        ('closed_lost', 'Closed Lost')],
        string="Stage")
    boq_type = fields.Selection([('received', 'Received'),('pending', 'Pending')], string="BOQ Status")

    def action_confirm(self):
        if self.env.context.get('model', False) == 'project.project':
            record = self.env['project.project'].sudo().search([('id', 'in', self.env.context['id'])])
            for line in record:
                if self.type_field == 'city':
                    line.sudo().write({'city_id': self.city_id.id})
                    line.sudo().write({'state_id': self.city_id.state_id.id})
                if self.type_field == 'source':
                    line.sudo().write({'source_id': self.source_id.id})
                if self.type_field == 'project_type':
                    line.sudo().write({'project_type_id': self.project_type_id.id})
                if self.type_field == 'stage':
                    line.sudo().write({'stage_type': self.stage_type})
                if self.type_field == 'boq_status':
                    line.sudo().write({'boq_type': self.boq_type})


