# -*- coding: utf-8 -*-
from odoo import models, fields, api, _  # <--- Checked: '_' is imported
from odoo.exceptions import ValidationError
import re

class InheritPartner(models.Model):
    _inherit = "res.partner"
    _order = 'id desc'

    # [Your existing fields]
    name = fields.Char("Company Name", index=True, default_export_compatible=True)
    person_contacts = fields.Char("Person Name")
    company_name_delivery = fields.Char("Delivery Company Name")
    msme_type = fields.Selection([('Yes', 'Yes'), ('No', 'No')], string="MSME")
    msme_no = fields.Char(string="MSME No")
    phone = fields.Char(string="Mobile 1", unaccent=False)
    mobile = fields.Char(string="Mobile 2", unaccent=False)
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    city_id = fields.Many2one('city.mst', string="City", tracking=True)
    email_color = fields.Selection([('green', 'Green'), ('no', 'No Decoration')], compute='_compute_email_color', store=False)
    contact_type = fields.Selection([('key_accountant', 'Most Important Key Accountant'), ('important', 'Important'), ('useful', 'Useful')], string='Contact Type', tracking=True)

    @api.onchange('vat')
    def onchange_vat(self):
        # Do nothing, blocking the l10n_in module logic
        pass


    def action_open_help_document(self):
        HELP_ATTACHMENT_ID = 1536  # Replace with your real PDF ID

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{HELP_ATTACHMENT_ID}?download=false',
            'target': 'new',
        }
    
    def action_open_workflow_contact_image(self):
        IMAGE_ATTACHMENT_ID = 1547

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{IMAGE_ATTACHMENT_ID}?download=false',
            'target': 'new',
        }



    ##########  add restriction for delivery address gst duplicate  ##########

    # @api.constrains('vat')
    # def _check_unique_gst(self):
    #     for rec in self:
    #         gst = (rec.vat or "").strip().upper()
    #         if gst:
    #             # Search for same GST number in other partners
    #             duplicate = self.env['res.partner'].search([
    #                 ('vat', '=', gst),
    #                 ('id', '!=', rec.id)
    #             ], limit=1)

    #             if duplicate:
    #                 raise ValidationError(
    #                     _("GST Number '%s' already exists for another contact (%s). "
    #                       "Duplicate GST is not allowed.") % (gst, duplicate.name)
    #                 )


    @api.constrains('vat')
    def _check_unique_gst(self):
        for rec in self:
            gst = (rec.vat or "").strip().upper()
            if rec.parent_id:
                continue

            if gst:
                duplicate = self.env['res.partner'].search([
                    ('vat', '=', gst),
                    ('id', '!=', rec.id),
                    ('parent_id', '=', False) 
                ], limit=1)

                if duplicate:
                    raise ValidationError(
                        _("GST Number '%s' already exists for another contact (%s). "
                          "Duplicate GST is not allowed.") % (gst, duplicate.name)
                    )

    @api.depends('email')
    def _compute_email_color(self):
        for rec in self:
            if rec.email and ('@gmail.com' in rec.email or '@yahoo.com' in rec.email):
                rec.email_color = 'no'
            else:
                rec.email_color = 'green'


    @api.onchange('vat')
    def onchange_vat(self):
        """Extracts the 10-character PAN from the GST number (vat), excluding the 2-digit state code."""
        for rec in self:
            gst_number = (rec.vat or "").strip().upper()
            # Check if GST is valid (min 15 characters for a complete GSTIN)
            if gst_number and len(gst_number) >= 12: 
                # PAN is characters from index 2 up to index 12 (10 characters total)
                pan_number = gst_number[2:12]
                rec.l10n_in_pan = pan_number
            else:
                rec.l10n_in_pan = False

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('contacts.menu_contacts').id
        for record in self:
            cids = record.company_id.id if record.company_id else self.env.company.id
            url = f'/web#id={record.id}&model=res.partner&view_type=form&cids={cids}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        if self.type == 'contact':
            return []
        else:
            return ['vat', 'company_registry', 'industry_id']
            
    @api.constrains('phone', 'mobile')
    def _check_numeric_value(self):
        for rec in self:
            if rec.company_type == 'person' and not rec.phone:
                 raise ValidationError("Mobile 1 is required for individual contacts.")

            if rec.phone:
                cleaned_phone = re.sub(r'\D', '', rec.phone)
                if not cleaned_phone:
                    raise ValidationError("Please enter a numeric value (digits only) in Mobile 1.")
                # Allow 10 (raw) or 12 (with 91 prefix) digits
                if len(cleaned_phone) not in [10, 12]:
                    raise ValidationError("Mobile 1 must be exactly 10 digits.")
                    
            if rec.mobile:
                cleaned_mobile = re.sub(r'\D', '', rec.mobile)
                if not cleaned_mobile:
                    raise ValidationError("Please enter a numeric value (digits only) in Mobile 2.")
                if len(cleaned_mobile) not in [10, 12]:
                    raise ValidationError("Mobile 2 must be exactly 10 digits.")

    @api.onchange('phone', 'mobile')
    def _onchange_phone_validation(self):
        for rec in self:
            if rec.phone:
                clean_no = re.sub(r'\D', '', rec.phone)
                # If user enters 10 digits, add +91
                if len(clean_no) == 10:
                    rec.phone = f"+91 {clean_no}"
                elif len(clean_no) > 10:
                    # If starts with 91, keep 12 digits total (91 + 10)
                    if clean_no.startswith('91'):
                        clean_no = clean_no[:12]
                        rec.phone = f"+91 {clean_no[2:]}"
                    else:
                        # Truncate to 10
                         clean_no = clean_no[:10]
                         rec.phone = f"+91 {clean_no}"
            
            if rec.mobile:
                clean_no = re.sub(r'\D', '', rec.mobile)
                # If user enters 10 digits, add +91
                if len(clean_no) == 10:
                    rec.mobile = f"+91 {clean_no}"
                elif len(clean_no) > 10:
                    # If starts with 91, keep 12 digits total (91 + 10)
                    if clean_no.startswith('91'):
                        clean_no = clean_no[:12]
                        rec.mobile = f"+91 {clean_no[2:]}"
                    else:
                        # Truncate to 10
                         clean_no = clean_no[:10]
                         rec.mobile = f"+91 {clean_no}"

    
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
            self.state_id = False
            self.city = False
    
    def _capitalize_input(self, vals):
        for key, value in vals.items():
            if key in self._fields and isinstance(value, str) and value:
                field_type = self._fields[key].type
                if field_type in ['char', 'text']:
                    if key not in ['email', 'website', 'vat', 'phone', 'mobile', 'ref']:
                        vals[key] = value.upper()
        return vals

    @api.model
    def create(self, vals):
        vals = self._capitalize_input(vals)

        if 'street' in vals and vals['street'] and len(vals['street']) >= 225:
            raise ValidationError("Street field must be less than 100 characters.")
        res = super(InheritPartner, self).create(vals)

        # Auto-assign shipping when a delivery contact is created or when the main contact is created without delivery child.
        for partner in res:
            if partner.type == 'delivery' and partner.parent_id:
                partner.parent_id._auto_assign_delivery_address(partner)
            elif not partner.parent_id and partner.type in (False, 'contact', 'invoice'):
                delivery_child = partner.child_ids.filtered(lambda c: c.type == 'delivery')
                if not delivery_child:
                    partner._auto_assign_delivery_address(partner)

        return res

    def write(self, vals):
        vals = self._capitalize_input(vals)

        if 'street' in vals and vals['street'] and len(vals['street']) >= 225:
            raise ValidationError("Street field must be less than 100 characters.")
        res = super(InheritPartner, self).write(vals)

        # If a delivery address is created/updated, push it to related quotations/SOs that had no dedicated delivery address.
        if any(key in vals for key in ['type', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id', 'parent_id']):
            for partner in self:
                # Case 1: this record is a delivery contact under a parent
                if partner.type == 'delivery' and partner.parent_id:
                    partner.parent_id._auto_assign_delivery_address(partner)
                # Case 2: the main contact gets its own address updated and has no delivery child yet
                elif not partner.parent_id and partner.type in (False, 'contact', 'invoice'):
                    delivery_child = partner.child_ids.filtered(lambda c: c.type == 'delivery')
                    # If no delivery child exists, use the main contact as shipping fallback
                    if not delivery_child:
                        partner._auto_assign_delivery_address(partner)

        return res

    def _auto_assign_delivery_address(self, delivery_partner):
        """Assign the given delivery partner to related quotations/SO that didn't have a dedicated shipping.
        We only replace when partner_shipping_id was unset or equal to the billing partner to avoid overriding
        manually chosen addresses."""
        if not delivery_partner:
            return
        parent = self
        SaleOrder = self.env['sale.order']
        orders = SaleOrder.search([
            ('partner_id', '=', parent.id),
            ('partner_shipping_id', 'in', [False, parent.id]),
            ('state', 'not in', ['cancel'])
        ])
        for order in orders:
            order.partner_shipping_id = delivery_partner.id

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