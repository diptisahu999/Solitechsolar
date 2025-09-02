from odoo import models, fields, api
from datetime import datetime, timedelta

class InheritprojectProject(models.Model):
    _inherit = "project.project"

    city_id = fields.Many2one('city.mst',string="City",tracking=True)
    state_id = fields.Many2one('res.country.state',string="State",tracking=True)
    source_id = fields.Many2one('utm.source',string="Source",tracking=True)
    project_type_id = fields.Many2one('res.partner.category',string="Project Type",tracking=True)
    approval_type = fields.Selection([
        ('approved', 'Approved'),
        ('pending', 'Pending')],
        string="Approval",tracking=True,default='pending')
    boq_type = fields.Selection([
        ('received', 'Received'),
        ('pending', 'Pending')],
        string="BOQ Status",tracking=True,default='pending')
    recevied_date = fields.Date(string="BOQ Recevied Date",tracking=True)
    boq_file = fields.Binary(string="BOQ File")
    washroom_num = fields.Integer(string="Number of Washrooms",tracking=True)
    project_value = fields.Float(string="Project Value",tracking=True)
    site_add = fields.Text(string="Site Address",tracking=True)
    interior_start_date = fields.Date(string="Interior Start Date",tracking=True)
    pincode = fields.Integer(string="Pincode",tracking=True)
    discount = fields.Float(string="Discount",tracking=True)
    rating = fields.Integer(string="Rating",tracking=True)
    received_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string="PO Received",tracking=True)
    invoice = fields.Char(string="Porforma Invoice",tracking=True)
    mockup_date = fields.Date(string="Mockup Date",tracking=True)
    completion_date = fields.Date(string="Completion Date",tracking=True)
    latest_status_id = fields.Many2one('latest.status.mst',string="Latest Status",tracking=True)
    latest_status_date = fields.Date(string="Latest Status Date",tracking=True)
    landmark = fields.Char(string="Landmark",tracking=True)
    construction_area = fields.Float(string="Construction Area (In SqFt)",tracking=True)
    construction_cost = fields.Float(string="Construction Cost (In INR-Crore)",tracking=True)
    key_account = fields.Char(string="Key Account",tracking=True)
    priority = fields.Selection([('0', 'Very Low'),('1', 'Low'), ('2', 'Medium'), ('3', 'High')], string='Priority')
    is_stage_assign = fields.Boolean('is Stage Assign', default=False)
    assign_ids = fields.Many2many('res.users','project_assign_id',string="Assign to",tracking=True)
    dol_sale_order_count = fields.Integer(string="Sale count")
    mst_id = fields.Many2one('project.contact.mst',string="mst")
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
        string="Stage",tracking=True,default='planning')

    developer_line_ids = fields.Many2many('project.contact.mst','developer_contact_id',string="Developer/Owner")
    mnc_line_ids = fields.Many2many('project.contact.mst','mnc_contact_id',string="MNC Company/ Hotel Brand")
    architect_line_ids = fields.Many2many('project.contact.mst','architect_contact_id',string="Architect")
    mep_line_ids = fields.Many2many('project.contact.mst','mep_contact_id',string="MEP Consultant")
    civil_line_ids = fields.Many2many('project.contact.mst','civil_contact_id',string="Civil Contractor")
    interior_line_ids = fields.Many2many('project.contact.mst','interior_contact_id',string="Interior Contractor")
    pmc_line_ids = fields.Many2many('project.contact.mst','pmc_contact_id',string="PMC")
    facility_line_ids = fields.Many2many('project.contact.mst','facility_contact_id',string="Facility Management")
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('project.menu_main_pm').id
        for record in self:
            url = f'/web#id={record.id}&model=project.project&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'
    
    @api.depends('display_name', 'name', 'city_id')
    def _compute_display_name(self):
        super()._compute_display_name()
        for rec in self:
            city = rec.city_id.name or ''
            if city:
                rec.display_name = f"{rec.name} - {city}"
            else:
                rec.display_name = rec.name

    @api.onchange('city_id')
    def _onchange_city_id(self):
        self.state_id = self.city_id.state_id.id

    def stage_assign_action(self):
        project_stages = self.env['project.task.type'].search([])
        for rec in project_stages:
            if self.id not in rec.project_ids.ids:
                rec.sudo().write({'project_ids': [(4, self.id)]})
                self.is_stage_assign = True
            else:
                self.is_stage_assign = True

    def action_create_sale(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation',
            'view_mode': 'form',
            'res_model': 'sale.order', 
            'context': {'default_project_id': self.id,},
            'target': 'current', 
        }
    
    def action_view_sale(self):
        action = self.sudo().env.ref('sale.action_quotations_with_onboarding')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        result['domain'] = [('project_id', '=', self.id)]

        sale_ids = self.env['sale.order'].sudo().search([('project_id', '=', self.id)])
        if len(sale_ids) == 1:
            res = self.sudo().env.ref('sale.view_order_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = sale_ids.id or False
        else:
            return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'domain': [('id', 'in', sale_ids.ids)],
            'context': {'create': False}
            }

        return result
    
    @api.depends('sale_order_id', 'task_ids.sale_order_id')
    def _compute_sale_order_count(self):
        res = super(InheritprojectProject, self)._compute_sale_order_count()
        for project in self:
            project.dol_sale_order_count = len(self.env['sale.order'].search([('project_id', '=', project.id)]))
        return res

    def action_assign_other_details(self):
        vals = {"model":'project.project','id':self.ids}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Details',
            'view_mode': 'form',
            'res_model': 'project.details.wiz',
            'target':'new',
            'context':vals
        }
