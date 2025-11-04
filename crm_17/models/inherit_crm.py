from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.exceptions import AccessError
from odoo.tools import date_utils, email_split, is_html_empty, groupby, parse_contact_from_email

class InheritCRM(models.Model):
    _inherit = "crm.lead"
    _order = 'id desc'

    person_contacts = fields.Char("Person Name")
    interest = fields.Char("Interest ")
    activity_type = fields.Char("Activity Type")
    activity_date = fields.Date("Activity Date")
    activity_user = fields.Char("Assigned to")
    activity_dec = fields.Html("description")
    bulk_requirement = fields.Boolean("Bulk Requirement")
    partner_vat = fields.Char(string='Partner Vat')
    source_id = fields.Many2one(ondelete='set null',tracking=True)
    label_ids = fields.Many2many('label.mst',string="Label",tracking=True)

    sale_line_ids = fields.One2many('crm.lead.sale.line','sale_id',string="Lead Assigned")
    kw = fields.Float(string="KW")
    create_date_formatted = fields.Char(
        string='Create Date (Formatted)',
        compute='_compute_create_date_formatted',
        store=False
    )
    last_date_formatted = fields.Char(
        string='Last Update Date',
        compute='_compute_write_date_formatted',
        store=False
    )

    pi_no = fields.Integer(string='PI No.',store=True)
    team_leader_id = fields.Many2one(related='team_id.user_id')
    due_days = fields.Integer("Due Days",compute='_compute_due_days',store=False)
    last_update = fields.Date(string="Last Update", store=True)
    is_same_lead = fields.Boolean("Same Lead", store=True)
    same_lead = fields.Char("Same Lead Name")
    interest_id = fields.Many2one('interest.mst',string='Interest',tracking=True)
    is_create_uid = fields.Boolean("Is Create by", store=True,default=True)
    is_group_uid = fields.Boolean("Is Saleperson by", store=True,default=True)
    is_group_manager = fields.Boolean("Access Right Group", store=True,default=True)

    phone = fields.Char(string="Mobile 1",unaccent=False)
    mobile = fields.Char(string="Mobile 2",unaccent=False)
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    project_id = fields.Many2one('project.project',string="Project",tracking=True)
    status = fields.Selection([
        ('busy', 'BUSY'),
        ('not_connect', 'NOT CONNECT'),
        ('call_not_lifting', 'CALL NOT LIFTING'),
        ('interested', 'INTERESTED'),
        ('not_interested','NOT INTRESTED'),
        ('pending', 'PENDING'),
    ], string="Status", tracking=True, default='pending')

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        if self.stage_id:
            if not self.stage_id.is_lost:
                self.lost_reason_id = False

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('crm.menu_crm_opportunities').id
        for record in self:
            url = f'/web#id={record.id}&model=crm.lead&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'

    @api.depends('user_id', 'type')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for lead in self:
            # setting user as void should not trigger a new team computation
            # if not lead.user_id:
            #     continue
            # user = lead.user_id
            # if lead.team_id and user in (lead.team_id.member_ids | lead.team_id.user_id):
            #     continue
            # team_domain = [('use_leads', '=', True)] if lead.type == 'lead' else [('use_opportunities', '=', True)]
            # team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=team_domain)
            # if lead.team_id != team:
            #     lead.team_id = team.id
            if self.env.user.team_id.id:
                lead.team_id = self.env.user.team_id.id
            if self.user_id.team_id.id:
                lead.team_id = self.user_id.team_id.id

    def _get_all_followers(self):
        user_ids = []
        for follower in self.message_follower_ids:
            if follower.partner_id.user_ids:
                user_ids += follower.partner_id.user_ids.ids
        return user_ids
    
    def action_new_quotation(self):
        action = super(InheritCRM, self).action_new_quotation()
        action['context']['default_project_id'] = self.project_id.id
        return action

    def action_view_sale_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_draft'] = 1
        action['domain'] = expression.AND([[('opportunity_id', '=', self.id)], self._get_lead_quotation_domain()])
        quotations = self.order_ids.filtered_domain(self._get_lead_quotation_domain())
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    def _get_lead_quotation_domain(self):
        return [('state', 'in', ('draft', 'sent', 'sale','discount_approval','cancel'))]

    # @api.depends('write_date')
    # def _compute_last_update(self):
    #     print("********************",self.write_date)
    #     for record in self:
    #         record.last_update = record.write_date or record.create_date

    @api.depends('last_update')
    def _compute_due_days(self):
        for record in self:
            if record.partner_vat != record.partner_id.vat:
                record.partner_vat = record.partner_id.vat
            if record.last_update:
                days_since_update = (date.today() - record.last_update).days
                record.due_days = max(0, days_since_update)
            elif not record.last_update:
                if record.create_date:
                    days_since_update = (date.today() - record.create_date.date()).days
                    record.due_days = max(0, days_since_update)
                else:
                    record.due_days = 0
            else:
                record.due_days = 0

    @api.depends('write_date')
    def _compute_write_date_formatted(self):
        for record in self:
            if record.write_date:
                local_date = fields.Datetime.context_timestamp(self, record.write_date)
                record.last_date_formatted = local_date.strftime('%d-%m-%Y %I:%M %p')
            else:
                record.last_date_formatted = ''

    @api.depends('create_date')
    def _compute_create_date_formatted(self):
        for record in self:
            if record.create_date:
                local_date = fields.Datetime.context_timestamp(self, record.create_date)
                record.create_date_formatted = local_date.strftime('%d-%m-%Y %I:%M %p')
            else:
                record.create_date_formatted = ''

            if record.create_uid.id == record.env.user.id or self.user_has_groups('sales_team.group_sale_manager'):
                record.is_create_uid = True
            else:
                record.is_create_uid = False

            if record.create_uid.id == record.env.user.id or record.user_id.id == record.env.user.id or self.user_has_groups('base.group_erp_manager'):
                record.is_group_uid = True
            else:
                record.is_group_uid = False

            # if self.user_has_groups('base.group_erp_manager'):
            #     record.is_group_manager = True
            # else:
            #     record.is_group_manager = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            rec.person_contacts = rec.partner_id.person_contacts
            rec.tag_ids = False
            if rec.partner_id.category_id:
                for tag in rec.partner_id.category_id:
                    tag_ids = rec.env['crm.tag'].search([('name', '=', tag.name)])
                    if tag_ids:
                        rec.tag_ids |= tag_ids
                    # else:
                    #     tag_ids = rec.env['crm.tag'].create({'name' : tag.name})
                    #     rec.tag_ids |= tag_ids  
            if not rec.partner_id.category_id:
                if rec.partner_id.parent_id:
                    if not rec.partner_id.category_id:
                        rec.partner_id.category_id |= rec.partner_id.parent_id.category_id
                    for tag in rec.partner_id.category_id:
                        tag_ids = rec.env['crm.tag'].search([('name', '=', tag.name)])
                        if tag_ids:
                            rec.tag_ids |= tag_ids
            if rec.partner_id:                  
                if not rec.partner_id.category_id:
                    partner_id = rec.partner_id.name
                    rec.partner_id = False
                    return {
                        'warning': {
                            'title': "Validation",
                            'message': f"Please add a tag to the ({partner_id}) customer.",
                        }
                    }

    def action_assign_other_saleperson(self):
        vals = {"model":'crm.lead','id':self.ids,'default_type_model':'crm'}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Other Saleperson',
            'view_mode': 'form',
            'res_model': 'saleperson.crm.wiz',
            'target':'new',
            'context':vals
        }

    def action_assign_other_details(self):
        vals = {"model":'crm.lead','id':self.ids}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Details',
            'view_mode': 'form',
            'res_model': 'crm.details.wiz',
            'target':'new',
            'context':vals
        }
    
    def bill_chr_vld(self):
        company_id = str(self.env.company.id) if self.env.company.id else str(self.company.id)
        query = ''' Select max(pi_no) From crm_lead Where company_id = ''' + str(company_id)

        self.env.cr.execute(query)
        query_result = self.env.cr.dictfetchall()
        if query_result[0]['max'] == None :
            serial = 1
        else:
            serial = 1 + query_result[0]['max']
        return serial
    
    def action_open_partner_view(self):
        partner = self.partner_id
        if partner.parent_id:
            partner = partner.parent_id

        return {
            'name': _("Customer"),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': partner.id,
        }
    
    @api.model
    def create(self, vals):
        if vals.get('pi_no') == None or vals.get('pi_no') == 0:
            vals['pi_no'] = self.bill_chr_vld()
        # The following line is the cause of the error; it has been commented out.
        # if vals.get('expected_revenue',False) == 0 and vals.get('type',False) == 'opportunity':
        #     raise UserError("Expected Revenue it Compulsory !!!")

        # record = self.env['crm.lead'].search([
        #     ('company_id', '=', vals.get('company_id')),
        #     ('phone', '=', vals.get('phone')),
        #     ('street', '=', vals.get('street')),
        #     ('street2', '=', vals.get('street2')),
        #     ('name', '=', vals.get('name')),
        #     ('mobile', '=', vals.get('mobile')),
        # ])
        # if record:
        #     vals['is_same_lead'] = True
        #     vals['same_lead'] = ', '.join(str(rec.pi_no) for rec in record)
        # else:
        #     vals['is_same_lead'] = False
        #     vals['same_lead'] = False
        res = super(InheritCRM, self).create(vals)
        if res.user_id and res.user_id.partner_id:
        # Subscribe assigned salesperson
            res.message_subscribe(partner_ids=[res.user_id.partner_id.id])
        
        if self.env.user.partner_id:
        # Subscribe the creator (current user)
            res.message_subscribe(partner_ids=[self.env.user.partner_id.id])
        
        for record in res:
            if record.user_id:
                users_to_notify = record._get_all_followers()
                # The following lines are causing the error and have been commented out.
                # self.env['notification.manager'].send_push_notification(
                #     user_ids=users_to_notify,
                #     title="New Task Created & Assigned",
                #     message=f"Task '{record.name}' was assigned to {record.user_id.name}."
                # )

        return res

    def write(self, vals):
        for record in self:
            line_list = []
            if vals.get('user_id', False):
                if record.user_id.id != vals.get('user_id', False):
                    line_list.append((0, 0, {
                        'date': datetime.now(),
                        'user_by_id': record.user_id.id,
                        'user_to_id': vals.get('user_id', False),
                    }))
                if line_list:
                    vals.update({'sale_line_ids': line_list})

        
            
            vals.update({'last_update': (vals.get('write_date') or record.write_date) or (vals.get('create_date') or record.create_date)})

        original_tags = set(self.tag_ids.ids)
        old_partner = self.partner_id.id
        res = super(InheritCRM, self).write(vals)

        if not self.env.user.has_group('crm_17.group_tag_remove'):
            if 'tag_ids' in vals:
                new_tags = set(self.tag_ids.ids)
                removed_tags = original_tags - new_tags
                if removed_tags and old_partner == self.partner_id.id:
                    raise AccessError("You do not have permission to remove tags from CRM leads.")
        
        # --- Notification logic after write ---
        # for res in self:
        #     if 'user_id' in vals and vals.get('user_id') and res.user_id:

        #         # Subscribe the newly assigned user
        #         if res.user_id.partner_id.id not in res.message_follower_ids.mapped('partner_id').ids:
        #             res.message_subscribe(partner_ids=[res.user_id.partner_id.id])

        #         # Subscribe the one who is doing the reassignment (the current user)
        #         current_user_partner = self.env.user.partner_id
        #         if current_user_partner and current_user_partner.id not in res.message_follower_ids.mapped('partner_id').ids:
        #             res.message_subscribe(partner_ids=[current_user_partner.id])

        #         #  Send notification to all followers (including newly subscribed)
        #         users_to_notify = res._get_all_followers()
        #         self.env['notification.manager'].send_push_notification(
        #             user_ids=users_to_notify,
        #             title="Lead Reassigned",
        #             message=f"Lead '{res.name}' has been assigned to {res.user_id.name} by {self.env.user.name}."
        #         )

        return res
    
    def _create_customer(self):
        """ Create a partner from lead data and link it to the lead.

        :return: newly-created partner browse record
        """
        Partner = self.env['res.partner']
        contact_name = self.contact_name
        if not contact_name:
            contact_name = parse_contact_from_email(self.email_from)[0] if self.email_from else False

        if self.partner_name:
            partner_company = Partner.create(self._prepare_customer_values(self.partner_name, is_company=True))
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = None
        # if contact_name:
        #     return Partner.create(self._prepare_customer_values(contact_name, is_company=False, parent_id=partner_company.id if partner_company else False))

        if partner_company:
            return partner_company
        return Partner.create(self._prepare_customer_values(self.name, is_company=False))
    
    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        res = super(InheritCRM, self)._prepare_customer_values(partner_name, is_company=False, parent_id=False)
        res.update({'person_contacts':self.contact_name})
        res.update({'company_type':'company'})
        tag_ids = self.env['res.partner.category']
        if self.tag_ids:
            for tag in self.tag_ids:
                matched_tags = self.env['res.partner.category'].search([('name', '=', tag.name)])
                tag_ids |= matched_tags

        res.update({'category_id': tag_ids.ids})
        return res
    
    def _convert_opportunity_data(self, customer, team_id=False):
        res = super(InheritCRM, self)._convert_opportunity_data(customer, team_id=False)
        if customer.person_contacts:
            res['person_contacts'] = customer.person_contacts
        return res
    
class CRMSalePerson(models.Model):
    _name = "crm.lead.sale.line"
    _description = 'CRM Sale Person'

    sale_id = fields.Many2one('crm.lead',string="Mst")

    date = fields.Datetime(string="Date ")
    user_by_id = fields.Many2one('res.users',string="Assigned by")
    user_to_id = fields.Many2one('res.users',string="Assigned to")
    date_formatted = fields.Char(
        string='Date',
        compute='_compute_date_formatted',
        store=False
    )

    @api.depends('date')
    def _compute_date_formatted(self):
        for record in self:
            if record.date:
                local_date = fields.Datetime.context_timestamp(self, record.date)
                record.date_formatted = local_date.strftime('%d-%m-%Y %I:%M %p')
            else:
                record.date_formatted = ''


class InheritCRMTeam(models.Model):
    _inherit = "crm.team"

    def update_sale_team_in_user(self):
        user_rec = self.env['res.users'].search([('id','=',self.user_id.id)])
        if user_rec:
            user_rec.sudo().write({'dol_team_id':self.id}) 

class InheritCRMStage(models.Model):
    _inherit = "crm.stage"

    is_lost = fields.Boolean("Is Lost Stage?")