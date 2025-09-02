from odoo import models, fields, api
from datetime import datetime, timedelta

class CityMaster(models.Model):
    _name = "city.mst"
    _description = "City Master"
    _inherit = ['mail.thread']

    name = fields.Char('Name',tracking=True)
    state_id = fields.Many2one('res.country.state',string="State",tracking=True)

class LatestStatusMaster(models.Model):
    _name = "latest.status.mst"
    _description = "Latest Status Master"
    _inherit = ['mail.thread']

    name = fields.Char('Name',tracking=True)

class CompanyMaster(models.Model):
    _name = "company.mst"
    _description = "Company Master"
    _inherit = ['mail.thread']

    name = fields.Char('Name',tracking=True)

class ProjectContactMaster(models.Model):
    _name = "project.contact.mst"
    _description = "Project Contact Master"
    _inherit = ['mail.thread']

    postion_type = fields.Selection([
        ('developer_owner', 'Developer/Owner'),
        ('mnc_company_hotel_brand', 'MNC Company/ Hotel Brand'),
        ('architect', 'Architect'),
        ('mep_consultant', 'MEP Consultant'),
        ('civil_contractor', 'Civil Contractor'),
        ('interior_contractor', 'Interior Contractor'),
        ('pmc', 'PMC'),
        ('facility_management', 'Facility Management'),],
        string="Type",tracking=True)
    company_id = fields.Many2one('company.mst',string="Company",tracking=True)
    name = fields.Char('Person Name',tracking=True)
    designation = fields.Char('Designation',tracking=True)
    email = fields.Char('Email',tracking=True)
    contact = fields.Char('Contact',tracking=True)
    source_id = fields.Many2one('utm.source',string="Source",tracking=True)
    project_ids = fields.One2many('project.project','mst_id',string="Project",tracking=True)
    project_count = fields.Integer(string="Count",compute='_compute_project_count')

    def _get_project_domain(self):
        return ['|', '|', '|', '|', '|', '|', '|',
            ('developer_line_ids', 'in', self.id),
            ('mnc_line_ids', 'in', self.id),
            ('architect_line_ids', 'in', self.id),
            ('mep_line_ids', 'in', self.id),
            ('civil_line_ids', 'in', self.id),
            ('interior_line_ids', 'in', self.id),
            ('pmc_line_ids', 'in', self.id),
            ('facility_line_ids', 'in', self.id),
        ]

    @api.depends('project_ids','project_count')
    def _compute_project_count(self):
        for rec in self:
            domain = rec._get_project_domain()
            projects = self.env['project.project'].search(domain)
            rec.project_count = len(projects)
            rec.project_ids = [(6, 0, projects.ids)]

    def action_view_project(self):
        self.ensure_one()
        domain = self._get_project_domain()
        project_rec = self.env['project.project'].search(domain)

        if len(project_rec) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project',
                'view_mode': 'form',
                'res_model': 'project.project',
                'res_id': project_rec.id,
                'context': {'create': False},
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Projects',
            'view_mode': 'tree,form',
            'res_model': 'project.project',
            'domain': [('id', 'in', project_rec.ids)],
            'context': {'create': False},
        }

