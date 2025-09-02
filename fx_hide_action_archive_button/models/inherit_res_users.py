import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class InheritResUsers(models.Model):
    _inherit = "res.users"

    is_hide_archive = fields.Boolean(string="Hide All Action Archive",default=True)
    applied_archive_models_ids = fields.Many2many(
        comodel_name="ir.model", string="Applied Models for Hiding Archive"
    )

    @api.model
    def get_is_hide_archive_and_applied_models(self):
        current_user = self.env.user

        is_hide_archive = current_user.is_hide_archive
        applied_archive_models = []
        for model in current_user.applied_archive_models_ids:
            applied_archive_models.append((model.id, model.model if model else False))

        return {
            "is_hide_archive": is_hide_archive,
            "applied_archive_models_ids": applied_archive_models,
        }
