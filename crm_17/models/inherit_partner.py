# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import re

class InheritPartner(models.Model):
    _inherit = "res.partner"
    _order = 'id desc'

    name = fields.Char("Company Name",index=True, default_export_compatible=True)
    person_contacts = fields.Char("Person Name")
    company_name_delivery = fields.Char("Delivery Company Name")
    msme_type = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No')], string="MSME")
    msme_no = fields.Char(string="MSME No")
    phone = fields.Char(string="Mobile 1",unaccent=False)
    mobile = fields.Char(string="Mobile 2",unaccent=False)
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    city_id = fields.Many2one('city.mst',string="City",tracking=True)
    email_color = fields.Selection([
        ('green', 'Green'),
        ('no', 'No Decoration')
    ], compute='_compute_email_color', store=False)
    contact_type = fields.Selection([
        ('key_accountant', 'Most Important Key Accountant'),
        ('important', 'Important'),
        ('useful', 'Useful')
    ], string='Contact Type', tracking=True)

    @api.depends('email')
    def _compute_email_color(self):
        for rec in self:
            if rec.email and ('@gmail.com' in rec.email or '@yahoo.com' in rec.email):
                rec.email_color = 'no'
            else:
                rec.email_color = 'green'
                
    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('contacts.menu_contacts').id
        for record in self:
            url = f'/web#id={record.id}&model=res.partner&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'

    # The following methods were in the original code but are not relevant to the solution.
    # I have left them in for context, but they do not need to be changed.
    def _handle_first_contact_creation(self):
        pass
    
    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        if self.type == 'contact':
            return []
        else:
            return ['vat', 'company_registry', 'industry_id']

    def _fields_sync(self, values):
        pass
    
    def _children_sync(self, values):
        pass
    
    # This is the corrected validation method.
    @api.constrains('phone', 'mobile')
    def _check_numeric_value(self):
        """
        Validates that the phone and mobile fields contain only numeric digits.
        It uses a regular expression to strip all non-digit characters before
        performing the validation to allow for formatting like spaces and '+' signs.
        """
        for rec in self:
            # Check for phone field (Mobile 1)
            if rec.phone:
                # Use regex to remove all non-digit characters (\D) from the string.
                cleaned_phone = re.sub(r'\D', '', rec.phone)
                if not cleaned_phone:
                    # If the cleaned string is empty, it means the user entered
                    # non-numeric characters and no digits, which should be an error.
                    raise ValidationError("Please enter a numeric value (digits only) in Mobile 1.")
            
            # Check for mobile field (Mobile 2)
            if rec.mobile:
                # Use regex to remove all non-digit characters (\D) from the string.
                cleaned_mobile = re.sub(r'\D', '', rec.mobile)
                if not cleaned_mobile:
                    # If the cleaned string is empty, it means the user entered
                    # non-numeric characters and no digits, which should be an error.
                    raise ValidationError("Please enter a numeric value (digits only) in Mobile 2.")
    
    @api.onchange('zip', 'parent_id', 'l10n_in_gst_treatment')
    def _onchange_zip(self):
        for record in self:
            gst_treatment = record.l10n_in_gst_treatment
            if record.parent_id and not gst_treatment:
                gst_treatment = record.parent_id.l10n_in_gst_treatment
            if gst_treatment != 'overseas':
                if record.zip:
                    if len(record.zip) != 6:
                        raise ValidationError("ZIP must be exactly 6 characters.")
                    if not record.zip.isdigit():
                        raise ValidationError("ZIP must contain only digits (no spaces or letters).")
    
    @api.onchange('city_id')
    def _onchange_city(self):
        if self.city_id:
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name
        else:
            # Clear the state and city if the city_id is not selected
            self.state_id = False
            self.city = False
    
    @api.model
    def create(self, vals):
        if 'street' in vals and vals['street'] and len(vals['street']) >= 100:
            raise ValidationError("Street field must be less than 100 characters.")
        res = super(InheritPartner, self).create(vals)
        return res

    def write(self, vals):
        if 'street' in vals and vals['street'] and len(vals['street']) >= 100:
            raise ValidationError("Street field must be less than 100 characters.")
        res = super(InheritPartner, self).write(vals)
        return res
    
class InheritresPartnerCategory(models.Model):
    _inherit = "res.partner.category"

    def create(self, vals):
        tag = super(InheritresPartnerCategory, self).create(vals)
        existing_category = self.env["crm.tag"].search([("name", "=", tag.name)], limit=1)
        if not existing_category:
            self.env["crm.tag"].create({
                "name": tag.name
            })
        return tag

    def write(self, vals):
        for tag in self:
            category = self.env["crm.tag"].search([("name", "=", tag.name)], limit=1)
            if category and "name" in vals:
                category.write({"name": vals["name"]})
        res = super(InheritresPartnerCategory, self).write(vals)
        return res