from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# ----------------------------
# Feedback Document Model
# ----------------------------
class FeedbackDocument(models.Model):
    _name = "feedback.document"
    _description = "Feedback Attachment"

    name = fields.Char(required=True)
    file = fields.Binary(attachment=True, required=True)
    feedback_id = fields.Many2one("feedback.record", required=True, ondelete="cascade")

    def action_save(self):
        # Optional custom logic can be added here
        # e.g. validations, logging, notifications
        return {'type': 'ir.actions.act_window_close'}

# ----------------------------
# Feedback Record Model
# ----------------------------
class FeedbackRecord(models.Model):
    _name = "feedback.record"
    _description = "Customer Feedback"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sr_no asc"

    name = fields.Char(string="Title", compute="_compute_name", store=True)
    feedback_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)

    category = fields.Selection([
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("service_required", "Service Required"),
    ], required=True, tracking=True)

    message = fields.Text(string="Feedback Message", tracking=True)

    state = fields.Selection([
        ("new", "New"),
        ("in_review", "In-Review"),
        ("resolved", "Resolved"),
    ], default="new", required=True, tracking=True)

    is_current_user_manager = fields.Boolean(string="Is Current User a Manager?",compute='_compute_is_current_user_manager',default=lambda self: self.env.user.has_group('feedback_manager.group_feedback_manager'))

    partner_id = fields.Many2one("res.partner", string="Customer/Contact", tracking=True)
    assigned_user_ids = fields.Many2many('res.users', string="Assigned Users",default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one("res.company", string="Company",
                                 default=lambda self: self.env.company, index=True)

    sr_no = fields.Integer(string="Serial No", readonly=True)

    _sql_constraints = [
        ("rating_range_check", "CHECK(rating >= 0.0 AND rating <= 5.0)", "Rating must be between 0 and 5.")
    ]

    @api.depends("feedback_date", "category", "partner_id", "state")
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.sr_no:
                parts.append(str(rec.sr_no))
            if rec.partner_id:
                parts.append(rec.partner_id.name)
            if rec.category:
                parts.append(dict(self._fields["category"].selection).get(rec.category))
            if rec.state:
                parts.append(dict(self._fields["state"].selection).get(rec.state))
            rec.name = " - ".join(parts) if parts else _("Feedback")

    @api.model
    def create(self, vals):
        # Automatically set the state to 'in_review' when a new record is created.
        #if 'state' not in vals or vals.get('state') == 'new':
        #    vals['state'] = 'in_review'

        record = super(FeedbackRecord, self).create(vals)
        record._resequence_sr_no()
        record._grant_feedback_group()
        return record
        
    def write(self, vals):
        res = super().write(vals)
        # only re-grant group if the assignment changed
        if 'assigned_user_ids' in vals:
            self._grant_feedback_group()
        return res

    def unlink(self):
        res = super(FeedbackRecord, self).unlink()
        self._resequence_sr_no()
        return res

    @api.model
    def _resequence_sr_no(self):
        records = self.search([], order='create_date asc, id asc')
        for index, rec in enumerate(records, start=1):
            rec.sudo().write({'sr_no': index})

    def action_mark_in_review(self):
        for rec in self:
            rec.state = "in_review"

    def action_mark_resolved(self):
        for rec in self:
            rec.state = "resolved"

    def action_add_document(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Document'),
            'res_model': 'feedback.document',
            'view_mode': 'form',
            'view_id': self.env.ref('feedback_manager.feedback_document_upload_form').id,
            'target': 'new',
            'context': {
                'default_feedback_id': self.id,
            },
        }

    @api.constrains("feedback_date")
    def _check_feedback_date(self):
        for rec in self:
            if rec.feedback_date and rec.feedback_date > fields.Date.today():
                raise ValidationError(_("Feedback Date cannot be in the future."))

    def _grant_feedback_group(self):
        """Ensure every assigned user has the Feedback User group."""
        group = self.env.ref('feedback_manager.group_feedback_user')
        for rec in self:
            for user in rec.assigned_user_ids:
                if group not in user.groups_id:
                    user.groups_id |= group
    
    @api.depends_context('uid')
    def _compute_is_current_user_manager(self):
        is_manager = self.env.user.has_group("feedback_manager.group_feedback_manager")
        for record in self:
            record.is_current_user_manager = is_manager