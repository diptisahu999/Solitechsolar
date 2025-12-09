from odoo import api, fields, models,_
from num2words import num2words
import re
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, float_round, format_date, groupby
import math
from odoo.tools import (
    formatLang
)
import base64
import io
import zipfile
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    min_unit_price_watt = fields.Float(
        string='Min Unit Price (₹/Wp)',
        default=13.0,
        config_parameter='crm_17.min_unit_price_watt',
        help='Minimum allowed unit price (₹/Wp) for non-admin users.'
    )

class InheritSaleOrder(models.Model):
    _inherit = "sale.order"

     
    state = fields.Selection(selection_add=[('sale','Quotation Confirm'),
                                            ('draft','Quotation Draft'),
                                            ('discount_approval','Discount Approval'),
                                            ('pi','Create PI')])
    is_manager = fields.Boolean(string='Manager',default=False)
    price_list_id = fields.Many2one('techv.product.pricelist',string="Combo Product")
    partner_vat = fields.Char(string='Partner Vat')
    is_partner_vat = fields.Boolean(string='Is Partner Vat',compute='compute_partner_vat')
    sample_type = fields.Selection([('spare_parts', 'Spare Parts'),('sample', 'Sample'), ('gift', 'Gift')], string='Sample/Gift/Spare Parts')
    # rounding_amount = fields.Float(string="Rounding Amount",copy=False,compute="_compute_amounts",store=True)
    # sale_amount_total = fields.Monetary(string='Total ', store=True, readonly=True)
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    final_quotation = fields.Boolean(string='Final Quotation',default=False)
    is_group_admin = fields.Boolean(string='Is Group Access Right')
    special_instruction_dcr = fields.Selection([
        ('dcr', 'DCR'),
        ('non_dcr', 'NON DCR')
    ], string='DCR Instruction', index=True)

    special_instruction_mess = fields.Selection([
        ('with_mess', 'WITH MESH'),
        ('without_mess', 'WITHOUT MESH')
    ], string='Mesh Instruction', index=True)

    advance_percentage = fields.Float(string='Advance %')
    before_dp_percentage = fields.Float(string='Before DP %')
    lc_days = fields.Integer(string='LC Days')

    delivery_type = fields.Selection([
        ('for', 'FOR'),
        ('ex_works', 'Ex. Works')
    ], string='Delivery Type', index=True)

    advance_display = fields.Char(
        string="Advance %",
        compute="_compute_advance_display",
        inverse="_inverse_advance_display",
        store=False
    )
    before_dp_display = fields.Char(
        string="Before DP Amount",
        compute="_compute_before_dp_display",
        inverse="_inverse_before_dp_display",
        store=False
    )

    salesperson_phone = fields.Char(
        string="Salesperson Contact",
        compute='_compute_salesperson_phone',
        store=True,
        readonly=False # Keep editable if needed, but the computed value is stored
    )



    offer_validity = fields.Datetime(
        string="Offer Validity",
        compute="_compute_offer_validity",
        store=True,
        readonly=True,
    )

    jurisdiction_state = fields.Char(
        string="Jurisdiction (State/City)",
        default="Surat, Gujarat",
        help="Select the applicable state or region."
    )
    start_date = fields.Date(string='Delivery Start Date')

    revision_number = fields.Integer(string='Revision No.', copy=False, default=1)
    

    def write(self, vals):
        """Override write method to increment revision_number when any field actually changes.

        Improvements over previous implementation:
        - Compare new values against existing values to avoid incrementing when the same
          value is written (this happens on prints or other system writes).
        - Handle common command formats for m2m/o2many (6, 4) to detect real changes.
        - Increment per-record so each order gets its own sequential revision.
        - Use a context flag `skip_revision_increment` to avoid nested increments.
        """
        # Fields to exclude from triggering revision number increment
        excluded_fields = {
            'revision_number',  # Don't increment if only revision number changes
            '__last_update',
            'message_ids',      # Chat/message changes should not trigger revision
            'activity_ids',     # Activity/todo changes
            'mail_activity_type_id',
            'write_date',       # Internal field
            'write_uid',        # Internal field
        }

        # If called with skip flag, bypass revision logic.
        if self.env.context.get('skip_revision_increment'):
            return super(InheritSaleOrder, self).write(vals)

        def _is_same_value(record, field, new_val):
            """Return True if new_val represents the same value as record[field]."""
            old = getattr(record, field)

            # Simple scalars and relational single-id written as scalar
            if isinstance(new_val, (int, float, bool, str)) or new_val is None:
                # If old is a record (many2one), compare ids
                if hasattr(old, 'id'):
                    old_val = old.id
                else:
                    old_val = old
                # Normalize None/False
                if old_val is None:
                    old_val = False
                if new_val is None:
                    new_norm = False
                else:
                    new_norm = new_val
                return str(old_val) == str(new_norm)

            # Many2many / one2many write commands are lists of commands
            if isinstance(new_val, (list, tuple)):
                # look for (6, 0, [ids]) command which replaces the set
                for cmd in new_val:
                    if not isinstance(cmd, (list, tuple)):
                        return False
                    op = int(cmd[0])
                    if op == 6:
                        ids = set(cmd[2] or [])
                        try:
                            old_ids = set(getattr(record, field).ids)
                        except Exception:
                            old_ids = set()
                        return ids == old_ids
                    if op == 4:
                        # add a single id: if it's already present, then no net change
                        ids_to_add = {int(cmd[1])}
                        try:
                            old_ids = set(getattr(record, field).ids)
                        except Exception:
                            old_ids = set()
                        # if all ids_to_add already present and no other commands, treat as same
                        # but since multiple commands may exist, we conservatively return False here
                        if ids_to_add.issubset(old_ids):
                            continue
                        return False
                    # other ops (0,1,2,3,5) we treat as change
                    return False

            # fallback: do a direct comparison
            try:
                return old == new_val
            except Exception:
                return False

        # Determine if any real change exists across the recordset
        increment_needed = False
        for order in self:
            for key, new_val in vals.items():
                if key in excluded_fields:
                    continue
                try:
                    same = _is_same_value(order, key, new_val)
                except Exception:
                    same = False
                if not same and order.state != 'cancel':
                    increment_needed = True
                    break
            if increment_needed:
                break

        # If no real change, just perform the write without incrementing
        if not increment_needed:
            return super(InheritSaleOrder, self).write(vals)

        # Otherwise perform per-record write with revision increment, using a context flag
        result = True
        for order in self:
            # Build per-order change list for the message log
            per_changes = []
            # skip logging if record was just created (to avoid initial setup noise)
            newly_created_recently = False
            try:
                created = order.create_date
                if created:
                    # normalize string -> datetime if necessary
                    if isinstance(created, str):
                        created_dt = fields.Datetime.from_string(created)
                    else:
                        created_dt = created
                    # compare in seconds
                    if (fields.Datetime.now() - created_dt).total_seconds() < 5:
                        newly_created_recently = True
            except Exception:
                newly_created_recently = False
            for key, new_val in vals.items():
                if key in excluded_fields:
                    continue
                # special handling: avoid dumping full order_line dicts in the log
                if key == 'order_line':
                    # if it's initial creation, skip logging order_line noise
                    if newly_created_recently:
                        # still treat as a change for revision purposes, but don't add to per_changes
                        continue
                    # otherwise summarize commands (add/remove/replace)
                    try:
                        added = removed = replaced_count = 0
                        if isinstance(new_val, (list, tuple)):
                            for cmd in new_val:
                                if not isinstance(cmd, (list, tuple)):
                                    continue
                                op = int(cmd[0])
                                if op in (0, 1, 4):
                                    added += 1
                                elif op in (2, 3):
                                    removed += 1
                                elif op == 6:
                                    replaced_count = len(cmd[2] or [])
                        summary = []
                        if replaced_count:
                            summary.append(f'replaced {replaced_count} lines')
                        if added:
                            summary.append(f'added {added} lines')
                        if removed:
                            summary.append(f'removed {removed} lines')
                        summary_text = ', '.join(summary) or 'order lines changed'
                        per_changes.append(('Order Lines', '', summary_text))
                        # continue to next field
                        continue
                    except Exception:
                        # fallback: skip heavy order_line logging
                        continue
                try:
                    same = _is_same_value(order, key, new_val)
                except Exception:
                    same = False
                if not same and order.state != 'cancel':
                    # old value
                    old_val = getattr(order, key)

                    def _val_to_str(v):
                        try:
                            # recordset (m2o, o2m, m2m)
                            if hasattr(v, 'mapped') and hasattr(v, 'display_name'):
                                names = v.mapped('display_name')
                                return ', '.join(names)
                        except Exception:
                            pass
                        # list of commands
                        if isinstance(v, (list, tuple)):
                            parts = []
                            for cmd in v:
                                if isinstance(cmd, (list, tuple)):
                                    op = int(cmd[0])
                                    if op == 6:
                                        parts.append('set %s' % (', '.join(map(str, cmd[2] or []))))
                                    elif op == 4:
                                        parts.append('add %s' % (cmd[1]))
                                    else:
                                        parts.append(str(cmd))
                                else:
                                    parts.append(str(cmd))
                            return '; '.join(parts)
                        if v is None:
                            return ''
                        return str(v)

                    old_str = _val_to_str(old_val)
                    new_str = _val_to_str(new_val)

                    # field label
                    try:
                        field_def = order._fields.get(key)
                        label = field_def.string if field_def else key
                    except Exception:
                        label = key

                    per_changes.append((label, old_str, new_str))

            if per_changes:
                rev = (order.revision_number or 0) + 1
                write_vals = dict(vals)
                write_vals['revision_number'] = rev
                # perform the actual write but avoid nested revision increments
                order.with_context(skip_revision_increment=True).write(write_vals)

                # Post a message with the revision and change log
                body_lines = [f'<b>Revision:</b> {rev:03d}', '<b>Changes:</b>']
                for lbl, o, n in per_changes:
                    body_lines.append(f'{lbl}: {o} → {n}')
                body = '<br/>'.join(body_lines)
                try:
                    order.message_post(body=body, subject=f'Quotation updated (Revision {rev:03d})')
                except Exception:
                    # avoid failing the write if message posting fails
                    pass

        return result


    @api.onchange('date_order')
    def _onchange_date_order_set_start_date(self):
        if self.date_order:
            self.start_date = self.date_order.date()

    @api.model
    def create(self, vals):
        if not vals.get('start_date') and vals.get('date_order'):
            vals['start_date'] = vals['date_order']
        return super().create(vals)
    

    @api.depends("date_order")
    def _compute_offer_validity(self):
        for order in self:
            if order.date_order:
                order.offer_validity = order.date_order + timedelta(days=7)
            else:
                order.offer_validity = False

    def action_print_quotation_report(self):
            """Triggers the report using the Quotation action ID, setting print_type='quotation'."""
            report_action = self.env.ref('crm_17.action_report_quotation_custom').report_action(self)
            
            # 1. Update the context to indicate it's a QUOTATION print
            report_action.update({
                'context': {'print_type': 'quotation'} 
            })
            return report_action
    

    def action_open_help_quotation(self):
        HELP_ATTACHMENT_ID = 1544  # your global PDF ID

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{HELP_ATTACHMENT_ID}?download=false',
            'target': 'new',
        }
    
    def action_open_workflow_sale_image(self):
        IMAGE_ATTACHMENT_ID = 1549

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{IMAGE_ATTACHMENT_ID}?download=false',
            'target': 'new',
        }
        
    def action_print_so_custom_report(self):
        """Triggers the report using the SO action ID, setting print_type='sale'."""
        report_action = self.env.ref('crm_17.action_report_so_custom').report_action(self)
        
        # 2. Update the context to indicate it's a SALE print
        report_action.update({
            'context': {'print_type': 'sale'}
        })
        return report_action
    

    def action_confirm(self):
        for order in self:
            partner = order.partner_id

            # GST No
            gst_number = partner.vat
            # BLOCK CONFIRM WHEN GST NO IS EMPTY
            if not gst_number:
                raise UserError(
                    "GST Number is required.\n\n"
                    "Please update the customer's GST No before confirming the quotation."
                )

        return super(InheritSaleOrder, self).action_confirm()
        
    @api.depends('user_id')
    def _compute_salesperson_phone(self):
        for rec in self:
            phone = False
            # Check if user_id and its linked partner_id exist
            if rec.user_id and rec.user_id.partner_id:
                # Use phone first, then mobile
                phone = rec.user_id.partner_id.phone or rec.user_id.partner_id.mobile
            rec.salesperson_phone = phone


    @api.depends('advance_percentage', 'amount_total')
    def _compute_advance_display(self):
        for rec in self:
            if rec.amount_total and rec.advance_percentage:
                amt = rec.amount_total * rec.advance_percentage / 100
                rec.advance_display = f"₹ {amt:.2f} ({rec.advance_percentage:.2f}%)"
            else:
                rec.advance_display = "₹ 0.00 (0%)"

    def _inverse_advance_display(self):
        for rec in self:
            if not rec.advance_display:
                continue
            
            text = rec.advance_display.replace("₹", "").replace(",", "").strip()

            amount = 0.0
            percentage = 0.0

            # Extract entered amount
            if "(" in text:
                amount_text = text.split("(")[0].strip()
                try:
                    amount = float(amount_text)
                except:
                    amount = 0.0

            # ✅ VALIDATION — BLOCK IF AMOUNT > TOTAL
            if amount > rec.amount_total:
                raise ValidationError(
                    f"Advance amount (₹{amount:.2f}) cannot be greater than total amount (₹{rec.amount_total:.2f})."
                )

            # Extract percentage
            if "%" in text:
                percent_text = text.split("(")[1].replace(")", "").replace("%", "")
                try:
                    percentage = float(percent_text)
                except:
                    percentage = 0.0

            # Recalculate % if amount entered
            if amount > 0 and rec.amount_total > 0:
                percentage = (amount / rec.amount_total) * 100

            rec.advance_percentage = percentage
            rec._compute_advance_display()


    @api.depends('before_dp_percentage', 'amount_total')
    def _compute_before_dp_display(self):
        for rec in self:
            if rec.amount_total and rec.before_dp_percentage:
                amt = rec.amount_total * rec.before_dp_percentage / 100
                rec.before_dp_display = f"₹ {amt:.2f} ({rec.before_dp_percentage:.2f}%)"
            else:
                rec.before_dp_display = "₹ 0.00 (0%)"

    def _inverse_before_dp_display(self):
        for rec in self:
            txt = rec.before_dp_display or ""

            # Extract amount
            amount = 0.0
            try:
                amount_str = txt.split("(")[0].replace("₹", "").replace(",", "").strip()
                amount = float(amount_str)
            except:
                amount = 0.0

            # Validate
            if amount > rec.amount_total:
                raise ValidationError(
                    f"Before DP amount (₹{amount:.2f}) cannot exceed total amount (₹{rec.amount_total:.2f})."
                )

            # Calculate %
            percentage = 0.0
            if rec.amount_total:
                percentage = (amount / rec.amount_total) * 100

            rec.before_dp_percentage = percentage
            rec._compute_before_dp_display()



    @api.onchange('fiscal_position_id')
    def _onchange_fiscal_position_id_update_taxes(self):
        """
        When the Fiscal Position changes, manually loop through the order lines
        and re-apply the tax mapping. This automates the "update tax" button.
        """
        if not self.order_line or not self.fiscal_position_id:
            return

        for line in self.order_line:
            if line.product_id:
                # Get the default taxes from the product
                product_taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == self.company_id)

                # Apply the fiscal position's mapping to find the correct new tax
                # If the fiscal position mapping returns no taxes (mapping not configured),
                # keep the original product taxes so tax is not removed for interstate cases.
                mapped_taxes = self.fiscal_position_id.map_tax(product_taxes) or product_taxes
                line.tax_id = mapped_taxes

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('sale.sale_order_menu').id
        for record in self:
            url = f'/web#id={record.id}&model=sale.order&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'
            
    def action_download_product_doc(self):
        attachment_ids = self.order_line.mapped('product_template_id.product_document_ids.ir_attachment_id')
        
        if not attachment_ids:
            return

        # Create an in-memory zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for attachment in attachment_ids:
                filename = attachment.name or f"{attachment.id}.bin"
                file_data = base64.b64decode(attachment.datas)
                zip_file.writestr(filename, file_data)

        zip_buffer.seek(0)
        old_attachments = self.env['ir.attachment'].search([('name', '=', 'product_documents.zip')])
        if old_attachments:
            old_attachments.unlink()
        # Create a new ir.attachment for the zip
        zip_attachment = self.env['ir.attachment'].create({
            'name': 'product_documents.zip',
            'type': 'binary',
            'datas': base64.b64encode(zip_buffer.read()),
            'mimetype': 'application/zip',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{zip_attachment.id}?download=true',
            'target': 'self',
        }
    
    def action_final_quotation(self):
        self.final_quotation = True
 
    @api.model
    def default_get(self, fields):
        res = super(InheritSaleOrder, self).default_get(fields)
        res['user_id'] = self.env.user.id
        return res 

    # @api.onchange('partner_id')
    # def _onchange_partner_id_user_id(self):
    #     self.user_id = self.env.user.id
    #     if not self.partner_id:
    #         self.user_id = False

    @api.onchange('partner_id')
    def compute_partner_vat(self):
        for rec in self:
            if rec.partner_id.vat:
                rec.is_partner_vat = True
                rec.partner_vat =  rec.partner_id.vat
            else:
                rec.is_partner_vat = False
                rec.partner_vat = ""
            for line in rec.order_line:
                line.compute_is_service()

            rec.is_group_admin = True if self.env.user.has_group('base.group_erp_manager') else False


    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """ Override of `sale` to recompute the delivery prices.

        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the sale order and
                 the quantity selected.
        :rtype: float
        """
        price_unit = super()._update_order_line_info(product_id, quantity, **kwargs)
        if self:
            for line in self.order_line:
                line.onchange_sake_product_image()
                line.with_context(is_catlog_product=True)._compute_price_unit()
                line.onchange_gst_product()
        return price_unit

    def create_invoice_direct(self):
        inv_wizard = self.env['sale.advance.payment.inv'].create({
                'sale_order_ids':self.ids,
                'consolidated_billing': True,
                'advance_payment_method': 'delivered'
            })
        if inv_wizard:
            invoices = inv_wizard._create_invoices(inv_wizard.sale_order_ids)
            # inv_wizard.create_invoices()
            self.state = 'pi'
            return self.action_view_invoice(invoices=invoices)
        


    def action_create_proforma(self):
        """Create a Proforma Invoice from this Sale Order and open it.
        
        Shows a wizard popup to capture PO Number (mandatory) before creating PI.
        """
        self.ensure_one()
        # Show a popup wizard to capture PO Number (mandatory) before creating PI
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'proforma.invoice.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def action_create_proforma_invoice(self):
        """Compatibility wrapper called by view button `action_create_proforma_invoice`.

        Previously the button called this name; it now delegates to
        `action_create_proforma` implemented above.
        """
        return self.action_create_proforma()
        
    def _prepare_invoice(self):
        res = super(InheritSaleOrder, self)._prepare_invoice()
        res.update({'sample_type':self.sample_type,
                    'tag_ids':self.tag_ids.ids,
                    'project_id':self.project_id.id})
        return res
    
    @api.onchange('price_list_id')
    def _onchange_price_list_id(self):
        line_list = []
        self.order_line = False
        if self.price_list_id:
            for price in self.price_list_id.line_ids:
                if price.product_id.active:
                    line_list.append((0,0,{
                                    'product_id':price.product_id.id,
                                    'inch_feet_type':price.inch_feet_type,
                                    'height_length':price.height_length,
                                    'width':price.width,
                                    'sqft':price.sqft,
                                    'sqft_rate':price.sqft_rate,
                                    'product_uom_qty':price.qty if price.qty > 0 else 1,
                                    'width':price.width,
                                    'discount':price.disc_per,
                                    # 'price_unit':price.price_unit,
                                    # 'tax_id':[(6,0,price.tax_ids.ids)],
                                }))
            if line_list:
                self.order_line = line_list
                self.order_line.onchange_sake_product_image()
                self.order_line.onchange_gst_product()
                self.order_line._onchange_product_id()

    def sale_quotation_report(self):
        return self.env.ref('crm_17.action_sale_quotation').report_action(self)

    def amount_to_text(self, amount, currency='INR'):
        word = num2words(amount, lang='en_IN').upper()
        word = word.replace(",", " ")
        return word
    
    def _send_payment_succeeded_for_order_mail(self):
        """ Send a mail to the SO customer to inform them that a payment has been initiated.

        :return: None
        """
        mail_template = self.env.ref(
            'sale.mail_template_sale_payment_executed', raise_if_not_found=False
        )
        # for order in self:
        #     order._send_order_notification_mail(mail_template)
    
    def action_draft(self):
        res = super(InheritSaleOrder, self).action_draft()
        self.is_manager = False
        return res
    
    def action_discount_user(self):
        self.state = 'discount_approval'

    def action_discount_manager(self):
        self.is_manager = True
        self.state = 'draft'

    def send_whatsapp_message(self):
        return {
            'type': 'ir.actions.act_url',
            'url': "https://api.whatsapp.com/send?phone=" +
                    self.partner_id.phone + "&text=" + "Hii",
            'target': 'new',
            'res_id': self.id,
        }
    
    def _check_note(self):
        check_note = False
        for rec in self:
            if rec.note:
                if rec.note is False:
                    check_note = True
                if rec.note == '<p><br></p>':
                    check_note = True
            else:
                check_note = True
        return check_note
    
    @api.onchange('l10n_in_gst_treatment','order_line','partner_id')
    def _onchange_l10n_in_gst_treatment(self):
        """When GST treatment changes, update line taxes accordingly.
        For overseas/SEZ: remove taxes.
        For intrastate/interstate: apply product taxes or fiscal position mapped taxes.
        """
        for line in self.order_line:
            if not line.product_id:
                continue
            
            if self.l10n_in_gst_treatment in ['overseas','special_economic_zone']:
                # Remove taxes for overseas and SEZ
                line.tax_id = [(5, 0, 0)]
            else:
                # For intrastate and interstate: apply product taxes with fiscal position mapping
                product_taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == self.company_id)
                if self.fiscal_position_id:
                    mapped = self.fiscal_position_id.map_tax(product_taxes) or product_taxes
                    line.tax_id = mapped
                else:
                    # No fiscal position: use product taxes as-is
                    line.tax_id = product_taxes

    @api.onchange('partner_id', 'partner_shipping_id', 'company_id')
    def _onchange_partner_apply_taxes(self):
        """Ensure order lines have taxes when partner changes.
        If a fiscal position exists we map product taxes; otherwise fall back
        to product default taxes so taxes don't disappear for interstate partners.
        """
        for order in self:
            for line in order.order_line:
                if not line.product_id:
                    continue
                product_taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == order.company_id)
                if order.fiscal_position_id:
                    mapped = order.fiscal_position_id.map_tax(product_taxes) or product_taxes
                    line.tax_id = mapped
                else:
                    line.tax_id = product_taxes
    # def _update_order_line_info(self, product_id, quantity, **kwargs):
    #     res = super(InheritSaleOrder, self)._update_order_line_info(product_id, quantity, **kwargs)
    #     self.order_line.onchange_gst_product()
    #     self.order_line.onchange_sake_product_image()
    #     return res
    
    def action_open_hike_wizard(self):
        self.ensure_one()
        return {
            'name': _("Hike"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.hike',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_hike_type': 'hike'}
        }
    
    def action_open_qty_wizard(self):
        self.ensure_one()
        return {
            'name': _("Qty Update"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.hike',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_hike_type': 'qty'}
        }
    
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
    
    @api.depends(
        'order_line.price_subtotal',
        'order_line.price_tax',
        'order_line.price_total',
        'order_line.product_uom_qty',
        'order_line.price_unit',
        'order_line.unit_price_per_nos',
        'order_line.wattage',
        'currency_id', 'company_id'
    )
    def _amount_all(self):
        """Compute totals using each line's computed subtotal/tax (which we fix on the line)."""
        for order in self:
            untaxed = 0.0
            tax = 0.0
            for line in order.order_line:
                untaxed += line.price_subtotal
                tax += line.price_tax
            order.update({
                'amount_untaxed': untaxed,
                'amount_tax': tax,
                'amount_total': untaxed + tax,
            })

    def update_product_price(self):
        for line in self.order_line:
            if line.price_unit == 0:
                line.sudo().write({'price_unit':line.product_id.list_price})

class InheritSaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _order = "id"

    image_128 = fields.Image(string="Image")
    inch_feet_type = fields.Selection([
        ('inch', 'Inch'),
        ('feet', 'Feet'),
        ('mm', 'MM'),
        ('tile', 'Tile'),
        ('basic', 'Basic'),
        ], 'Inch/Feet',default="basic")
    height_length = fields.Float(string="Height/Length")
    width = fields.Float(string="Width")
    tile_width = fields.Float(string="Tile Width (mm)")
    tile_length = fields.Float(string="Tile Length (mm)")
    layout = fields.Selection([
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
        ('horizontal_vertical', 'Horizontal/ Vertical')
        ], string="Layout")
    tiles_per_box = fields.Integer(string="Tile per Box")
    tile_final = fields.Float(string="Total Tiles")
    sqft = fields.Float(string="Sqft")
    sqft_rate = fields.Float(string="Sqft Rate")
    gst_tax = fields.Char(string='GST Tax',compute='get_gst_percentages')
    is_service = fields.Boolean(string='Service',default=False,compute='compute_is_service')
    no_discount_ok = fields.Boolean(string='No Discount',default=False,compute='compute_is_service')
    is_group_price = fields.Boolean(string='Group price change',default=False,store=True)
    is_categ_widht = fields.Boolean(string='Is Category Widht',default=False,store=True)
    is_tile = fields.Boolean(string='Is Tile',default=False,store=True)
    actual_price = fields.Float(string="Actual Price")
    diff_amount = fields.Float(string="Difference Amount")
    remarks = fields.Char(string='Remarks')
    diff_per = fields.Float(string="Difference Per(%)")
    up_after_disc_amt = fields.Float(string="Unit Price After Discount")
    wattage = fields.Float(
        string="Wattage (Wp)",
        related='product_id.wattage',
        store=True,
        readonly=True
    )

    unit_price_per_nos = fields.Monetary(
        string="Unit Price (₹ per Nos)",
        compute='_compute_unit_price_per_nos',
        store=True,
        readonly=True
    )

    @api.depends('wattage', 'price_unit')
    def _compute_unit_price_per_nos(self):
        """Calculates the price per unit number based on wattage."""
        for line in self:
            if line.wattage:
                line.unit_price_per_nos = (line.wattage or 0.0) * (line.price_unit or 0.0)
            else:
                line.unit_price_per_nos = line.price_unit or 0.0

    def _get_price_for_totals(self):
        """Return the price per sellable unit that should feed totals/taxes."""
        self.ensure_one()
        if self.wattage and self.wattage > 0:
            return self.unit_price_per_nos or 0.0
        return self.price_unit or 0.0

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'wattage', 'actual_price', 'unit_price_per_nos')
    def _compute_amount(self):
        """Make totals use the per-panel price if wattage is set."""
        for line in self:
            price_for_taxes = line._get_price_for_totals()
            price_after_discount = price_for_taxes * (1 - (line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(
                price_after_discount,
                line.order_id.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id,
            )

            # IMPORTANT: store the computed totals so order uses them
            line.price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
            line.price_total = taxes.get('total_included', 0.0)
            line.price_subtotal = taxes.get('total_excluded', 0.0)

            # diff/disc logic unchanged
            if line.actual_price:
                line.diff_amount = line.price_unit - line.actual_price
                line.diff_per = (line.diff_amount / line.actual_price) * 100 if line.actual_price else 0.0
            else:
                line.diff_amount = 0.0
                line.diff_per = 0.0

            line.up_after_disc_amt = line.price_unit * (1 - (line.discount or 0.0) / 100.0) if line.discount else 0.0

    # Make tax totals use the per-panel price instead of ₹/Wp
    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        res = super()._convert_to_tax_base_line_dict()
        res.update({
            'price_unit': self._get_price_for_totals(),  # pass undiscounted per-panel price
            'quantity': self.product_uom_qty,
            'discount': self.discount or 0.0,
            'currency_id': self.order_id.currency_id,
            'product': self.product_id,
            'partner': self.order_id.partner_shipping_id,
            'taxes': self.tax_id,
        })
        return res

    # Ensure invoice uses the per-panel price
    def _prepare_invoice_line(self, **optional_values):
        res = super(InheritSaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res.update({
            'inch_feet_type': self.inch_feet_type,
            'height_length': self.height_length,
            'width': self.width,
            'sqft': self.sqft,
            'sqft_rate': self.sqft_rate,
            'tile_width': self.tile_width,
            'tile_length': self.tile_length,
            'layout': self.layout,
            'tiles_per_box': self.tiles_per_box,
            'tile_final': self.tile_final,
            'remarks': self.remarks,
            'actual_price': self.actual_price,
            'diff_amount': self.diff_amount,
            'diff_per': self.diff_per,
            # Critical: invoice unit price should be per nos, not ₹/Wp
            'price_unit': self._get_price_for_totals(),
        })
        return res

    @api.constrains('product_uom_qty')
    def _check_quantity_integer(self):
        for line in self:
            if line.product_uom_qty != int(line.product_uom_qty):
                raise ValidationError(_("Quantity must be an integer value."))

    @api.onchange('is_service','product_id')
    def compute_is_service(self):
        flg = False
        for service in self:
            service.no_discount_ok = False
            if service.product_id.type == 'service':
                flg =  True
            service.is_service = flg
            if service.product_id.no_discount_ok:
                service.no_discount_ok =  True

            service.is_group_price = self.env.user.has_group('crm_17.group_so_inv_price')
            service.is_categ_widht = True if service.product_id.width > 0 else False
            service.is_tile = service.product_id.is_tile

    @api.onchange('discount')
    def _onchange_discount(self):
        sale_per = self.env['ir.config_parameter'].sudo().get_param('saleperson_per')
        sale_per = float(sale_per or 0.0)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.user_has_groups('sales_team.group_sale_salesman_all_leads') and not self.user_has_groups('sales_team.group_sale_manager'):
            if sale_per and self.discount:
                if self.discount > sale_per:
                    raise UserError("Not Allowed: Discount exceeds %s%%" % sale_per)
            # if not sale_per:
            #     raise UserError("You are not allowed to give any discount. Please contact your manager.")
            
    @api.onchange('inch_feet_type','height_length','width','product_uom_qty','sqft')
    def onchange_inch_feet_type(self):
        for rec in self:
            if rec.inch_feet_type != 'basic':
                if rec.inch_feet_type == 'feet':
                    rec.sqft = math.ceil(rec.height_length * rec.width)

                if rec.inch_feet_type == 'inch':
                    length_feet = rec.height_length / 12.0
                    width_feet = rec.width / 12.0
                    rec.sqft = math.ceil(length_feet * width_feet)

                if rec.inch_feet_type == 'mm':
                    length_feet = rec.height_length / 305.0
                    width_feet = rec.width / 305.0
                    rec.sqft = math.ceil(length_feet * width_feet)
                if rec.sqft_rate == 0:
                    rec.sqft_rate = rec.product_id.list_price
                rec.price_unit = rec.sqft_rate * rec.sqft
            else:
                if self.inch_feet_type != 'tile':
                    rec.sqft_rate = 0
                    rec.sqft = 0
                rec.height_length = 0
                # rec.width = 0
                # self.price_unit = self.product_id.list_price

    @api.onchange('height_length', 'width', 'tile_width', 'tile_length', 'layout','tiles_per_box')
    def _onchange_calculate_tiles(self):
        for rec in self:
            if rec.height_length and rec.width and rec.tile_width and rec.tile_length and rec.layout and rec.tiles_per_box:
                # Setup
                room_length = rec.height_length
                room_width = rec.width
                tile_width = rec.tile_width
                tile_length = rec.tile_length
                layout = rec.layout
                tiles_per_box = rec.tiles_per_box

                # Layout-wise calculation
                if layout == 'horizontal':
                    tiles_along_length = math.ceil(room_length / tile_width)
                    tiles_along_width = math.ceil(room_width / tile_length)

                    val1 = math.ceil(room_length / tile_width)
                    val2 = math.ceil(room_width / tile_length)
                elif layout == 'vertical':
                    tiles_along_length = math.ceil(room_length / tile_length)
                    tiles_along_width = math.ceil(room_width / tile_width)

                    val1 = math.ceil(room_length / tile_length)
                    val2 = math.ceil(room_width / tile_width)
                else:  # horizontal_vertical
                    tiles_along_length = math.ceil(room_length / tile_width)
                    tiles_along_width = math.ceil(room_width / tile_width)

                    val1 = math.ceil(room_length / tile_width)
                    val2 = math.ceil(room_width / tile_length)
                # Total Tiles
                total_tiles = tiles_along_length * tiles_along_width

                # Boxes Needed
                boxes_needed = math.ceil(total_tiles / tiles_per_box)

                # Total Tiles to Give
                total_tiles_to_give = boxes_needed * tiles_per_box

                # Area Calculation
                tile_width_m = tile_width / 1000
                tile_length_m = tile_length / 1000
                area_sqft = tile_width_m * tile_length_m * 10.7639 * total_tiles_to_give

                # Assign results
                rec.sqft = round(area_sqft, 2)

                product = val1 * val2
                divided = product / tiles_per_box
                rounded = math.ceil(divided)    
                rec.tile_final = rounded * tiles_per_box

    @api.onchange('sqft_rate','inch_feet_type')
    def _onchange_sqft_rate(self):
        if self.inch_feet_type != 'basic':
            if self.sqft_rate:
                self.price_unit = self.sqft_rate * self.sqft
        else:
            if self.inch_feet_type != 'tile':
                self.sqft_rate = 0
                self.sqft = 0
            self.height_length = 0
            # self.width = 0
            self.price_unit = self.product_id.list_price

    def get_gst_percentages(self):
        for record in self:
            gst_percentages = []
            for tax in record.tax_id:
                match = re.search(r'\d*\.\d+%|\d+%', tax.name)
                if match:
                    gst_percentages.append(match.group())
            record.gst_tax = ' , '.join(gst_percentages)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.inch_feet_type != 'basic':
                rec.price_unit = rec.sqft_rate * rec.sqft
            else:
                rec.price_unit = rec.product_id.list_price
            rec.actual_price = rec.product_id.list_price
            
            rec.width = rec.product_id.width
            rec.tile_width = rec.product_id.tile_width
            rec.tile_length = rec.product_id.tile_length
            rec.tiles_per_box = rec.product_id.tiles_per_box
    
    @api.depends('product_id','product_uom','inch_feet_type')
    def _compute_price_unit(self):
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
                continue
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                line = line.with_company(line.company_id)
                price = line._get_display_price()
                price_list = line.product_id._get_tax_included_unit_price(
                    line.company_id or line.env.company,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                    )
                if self.env.context.get('is_catlog_product',False):
                    line.price_unit = price_list
                    line.actual_price = price_list
                # if line.price_unit != price_list:
                #     # if line.price_unit == 0:
                #     line.price_unit = price_list
            # if line.inch_feet_type != 'basic':
            #     line.sqft_rate = line.product_id.list_price

    @api.onchange('product_id')
    def onchange_sake_product_image(self):
        for product in self:
            product.image_128 = product.product_id.image_128
    def _get_min_unit_price(self):
        """Read the configured minimal unit price (₹/Wp)."""
        # default to 13.0 if not configured
        val = self.env['ir.config_parameter'].sudo().get_param('crm_17.min_unit_price_watt', '13')
        try:
            return float(val)
        except Exception:
            return 13.0

    def _is_admin_user(self):
        return self.env.user.has_group('base.group_system')

    @api.model_create_multi
    def create(self, vals_list):
        # Allow creating lines (notes/sections) without initial validation.
        # Validation is deferred to the constraint.
        return super(InheritSaleOrderLine, self).create(vals_list)

    def write(self, vals):
        # Logging only. No validation here.
        for line in self:
            changes = []
            if 'product_uom_qty' in vals:
                old_qty = line.product_uom_qty
                new_qty = vals['product_uom_qty']
                if old_qty != new_qty:
                    changes.append(f"Quantity changed from {old_qty} to {new_qty}")
            if 'price_unit' in vals:
                old_price = line.price_unit
                new_price = vals['price_unit']
                if old_price != new_price:
                    changes.append(f"Unit Price changed from ₹{old_price:.2f} to ₹{new_price:.2f}")
            if changes and line.order_id:
                message_body = "<br/>".join(changes)
                line.order_id.message_post(body=message_body, subject="Order Line Updated")
        return super(InheritSaleOrderLine, self).write(vals)

    @api.constrains('price_unit', 'product_id', 'display_type')
    def _check_price_unit_minimum(self):
        min_price = self._get_min_unit_price()
        if self._is_admin_user():
            return
        
        for line in self:
            # 1. SKIP Notes and Sections explicitly
            if line.display_type in ['line_note', 'line_section']:
                continue
            
            # 2. SKIP if there is NO product (e.g. text only)
            if not line.product_id:
                continue

            # 3. SKIP if price is 0 AND product is missing (Safety Catch)
            if line.price_unit == 0.0 and not line.product_id:
                continue

            # 4. Perform Check
            try:
                price = float(line.price_unit or 0.0)
            except Exception:
                price = 0.0
                
            if price < (min_price - 0.01):
                raise ValidationError(f"You cannot use a Unit Price below ₹{min_price:.2f}.")
    def write(self, vals):
        """Override write to track quantity and unit price changes in log note."""
        for line in self:
            changes = []
            
            # Track quantity changes
            if 'product_uom_qty' in vals:
                old_qty = line.product_uom_qty
                new_qty = vals['product_uom_qty']
                if old_qty != new_qty:
                    changes.append(f"Quantity changed from {old_qty} to {new_qty}")
            
            # Track unit price changes (price_unit - ₹/Wp or base price)
            if 'price_unit' in vals:
                old_price = line.price_unit
                new_price = vals['price_unit']
                if old_price != new_price:
                    changes.append(f"Unit Price (₹/Wp) changed from ₹{old_price:.2f} to ₹{new_price:.2f}")
            
            # Post message to order log if any changes detected
            if changes:
                message_body = "<br/>".join(changes)
                if line.order_id:
                    line.order_id.message_post(
                        body=message_body,
                        subject="Order Line Updated"
                    )
        
        return super(InheritSaleOrderLine, self).write(vals)


class InheritSaleOrderReport(models.Model):
    _inherit = "sale.report"
            
    final_quotation = fields.Boolean(string='Final Quotation',default=False)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['final_quotation'] = "s.final_quotation"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.final_quotation"""
        return res