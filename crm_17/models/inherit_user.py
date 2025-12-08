from odoo import api, fields, models,_

class InheritResUsers(models.Model):
    _inherit = "res.users"

    mobile = fields.Char(string="Mobile")
    dol_team_id = fields.Many2one('crm.team', 'Sales Team ')
    dis_per = fields.Selection([
        ('30', '30%'),
        ('50', '50%'),
        ('100', '100%'),
    ], string="Discount (%)")
    state = fields.Selection(selection_add=[('active','Active'),
                                            ('left','Left')])
    is_left = fields.Boolean(string="Is Left")
    user_type = fields.Selection([
        ('filed_sales', 'Field Sales'),
        ('backend_sales', 'Backend Sales'),
        ('exhibition', 'Exhibition'),
        ('services', 'Services'),
    ], string="User Type")
    email_signature = fields.Html(string="Email Signature")
    fcm_token = fields.Char("FCM Token")

    parent_id = fields.Many2one(
        'res.users', 
        string='Reports To',
        help='Direct manager/supervisor in the sales hierarchy',
        domain="[('share', '=', False)]"  
    )
    child_ids = fields.One2many(
        'res.users', 
        'parent_id', 
        string='Direct Subordinates'
    )
    
    def _compute_state(self):
        for user in self:
            if user.login_date:
                user.state = 'active' 
            if user.is_left:
                user.state = 'left' 
            if not user.is_left and not user.login_date:
                user.state = 'new'
    
    def action_button_left(self):
        self.is_left = True
        self.state = 'left'

    def action_button_active(self):
        self.is_left = False
        self.state = 'active'

    def write(self, vals):
        """Override write to allow self-deactivation"""
        # If trying to deactivate (set active=False)
        if 'active' in vals and vals.get('active') is False:
            # Allow self-deactivation by using sudo() to bypass Odoo's restriction
            # This changes the environment user to superuser, bypassing the check
            for record in self:
                # Use sudo() to execute with superuser privileges, bypassing self-deactivation check
                super(InheritResUsers, record.sudo()).write(vals)
            return True
        return super(InheritResUsers, self).write(vals)