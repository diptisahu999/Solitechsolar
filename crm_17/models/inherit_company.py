from odoo import models, fields, api
from datetime import datetime, timedelta


class InheritCompany(models.Model):
    _inherit = "res.company"

    india_offices = fields.Text("India Offices")
    overseas_offices = fields.Text("Overseas Offices")
    note = fields.Text("Note")
    bank_name = fields.Text("Bank Name")
    bank_ac_name = fields.Text("Bank A/C Name")
    bank_ac_no = fields.Text("Bank A/C No")
    bank_branch_ifsc = fields.Text("Bank Branch IFSC")
    bank_swift_code = fields.Char("SWIFT Code")
    conditions = fields.Html("Terms & Conditions")
    iso_img = fields.Binary("Iso Image")
    sing = fields.Binary("Sing")
    accounts = fields.Char("Accounts")
    service = fields.Char("Service")
    inquiry = fields.Char("Inquiry")
    msme_no = fields.Char(string="MSME No")
    warehouse_address = fields.Text(string="Warehouse Address")
    export_bank = fields.Html(string="Bank details")
    export_terms = fields.Html(string="Terms/Conditions")

    def _convert_text_to_html(self, text):
        """Convert plain text to HTML by replacing newlines with <br/> tags."""
        if not text:
            return ""
        return text.replace('\n', '<br/>')