from odoo import fields, models, api, _


class Partner(models.Model):
    _inherit = "res.partner"

    tcs_applicable = fields.Boolean(string='TCS Applicable', default=False)
    tcs_percentage = fields.Float(string='TCS Percentage', )
    tcs_sec = fields.Many2one('tds.accounting', string='TCS section')
    tds_applicable = fields.Boolean(string='TDS Applicable', default=False)
    tds_percentage = fields.Float(string='TDS Percentage')
    tds_sec = fields.Many2one('tds.accounting', string='TDS section')
    address_type = fields.Char(string='Type')
    pan_no = fields.Char(string='Pan No')
    tan_no = fields.Char(string='Tan No')

    @api.onchange('company_type', 'tds_sec', 'pan_no','tcs_sec')
    def _compute_individual_huf_no_pan(self):
        for rec in self:
            if rec.company_type == 'person' and rec.pan_no:
                rec.tds_percentage = rec.tds_sec.individual_huf
                rec.tcs_percentage = rec.tcs_sec.individual_huf
            elif rec.company_type == 'person' and not rec.pan_no:
                rec.tds_percentage = rec.tds_sec.individual_huf + rec.tds_sec.no_pan
                rec.tcs_percentage = rec.tcs_sec.individual_huf + rec.tcs_sec.no_pan
            elif rec.company_type == 'company' and rec.pan_no:
                rec.tds_percentage = rec.tds_sec.individual_huf
                rec.tcs_percentage = rec.tcs_sec.individual_huf
            elif rec.company_type == 'company' and not rec.pan_no:
                rec.tds_percentage = rec.tds_sec.individual_huf + rec.tds_sec.no_pan
                rec.tcs_percentage = rec.tcs_sec.individual_huf + rec.tcs_sec.no_pan
