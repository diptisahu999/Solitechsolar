from odoo import api, models, fields, _
from datetime import date,datetime
class SalepersonCrmWizard(models.TransientModel):
    _name = 'saleperson.crm.wiz'
    _description= "Saleperson Crm Wizard"

    user_id = fields.Many2one('res.users', string='Salesperson')
    type_model = fields.Selection([('crm', 'crm'), ('partner', 'partner')],string='Select Model')


    # def action_confirm(self):
    #     if self.env.context.get('model', False) == 'crm.lead':
    #         # Step 1: Disable the 'Personal Leads' record rule temporarily
    #         rule = self.env.ref('crm.crm_rule_personal_lead', raise_if_not_found=False)
    #         if rule:
    #             rule.sudo().active = False  # Disable the rule to bypass access restrictions

    #         # Step 2: Search for the leads and update their user_id
    #         record = self.env['crm.lead'].sudo().search([('id', 'in', self.env.context['id'])])

    #         for line in record:
    #             if line.user_id.id != self.user_id.id:
    #                 # Insert into the log (optional)
    #                 query = f"""
    #                     INSERT INTO crm_lead_sale_line (date, user_by_id, user_to_id, sale_id)
    #                     VALUES ('{datetime.now()}', {line.user_id.id}, {self.user_id.id}, {line.id});
    #                 """
    #                 self.env.cr.execute(query)
    #         # Update the user_id for the leads
    #         query = f"""
    #             UPDATE crm_lead
    #             SET user_id = {self.user_id.id}
    #             WHERE id IN ({', '.join(map(str, record.ids))})
    #         """
    #         self.env.cr.execute(query)
    #         # Step 3: Re-enable the rule after the update
    #         if rule:
    #             rule.with_context(id='kavin').sudo().active = True  # Re-enable the rule to enforce access restrictions again
    #         # Step 4: Perform the reload
    #         action = self.sudo().env.ref('crm.crm_lead_action_pipeline')
    #         result = action.read()[0]
    #         result['target'] = 'current'
    #         result['views'] = [(self.env.ref('crm.crm_case_tree_view_oppor').id, 'tree')]
    #         result['context'] = {'tag': 'reload'}  # Set context for reload
    #         # Return the action for reload
    #         return result
    #     return super(SalepersonCrmWizard, self).action_confirm()

    # def action_confirm(self):
    #     if self.env.context.get('model',False) == 'crm.lead':
    #         record = self.env['crm.lead'].sudo().search([('id','in',self.env.context['id'])])
    #         for line in record:
    #             if line.user_id.id != self.user_id.id:
    #                 query = f""" INSERT INTO crm_lead_sale_line (date, user_by_id, user_to_id,sale_id)
    #                     VALUES ('{datetime.now()}', {line.user_id.id}, {self.user_id.id},{line.id}); """
    #                 self.env.cr.execute(query)
    #         query = """
    #                 UPDATE crm_lead
    #                 SET user_id = """ + str(self.user_id.id)
    #         query +=    """ WHERE id IN """ + str(f"({', '.join(map(str, record.ids))})")
    #         print("*****************",query)
    #         self.env.cr.execute(query)
    #         if self.env.user.has_group('sales_team.group_sale_salesman') and not self.user_has_groups('sales_team.group_sale_salesman_all_leads') and not self.user_has_groups('sales_team.group_sale_manager'):
    #             action = self.sudo().env.ref('crm.crm_lead_action_pipeline')
    #             result = action.read()[0]
    #             result['target'] = 'main'
    #             return result

    def action_confirm(self):
        if self.env.context.get('model', False) == 'crm.lead':
            record = self.env['crm.lead'].sudo().search([('id', 'in', self.env.context['id'])])
            rule = self.env.ref('crm.crm_rule_personal_lead', raise_if_not_found=False)
            if rule:
                rule.sudo().active = False
            for line in record:
                if line.order_ids:
                    for sale in line.order_ids:
                        sale.sudo().write({'user_id': self.user_id.id,'team_id':self.user_id.team_id.id})
                        if sale.invoice_ids:
                            for inv in sale.invoice_ids:
                                inv.sudo().write({'invoice_user_id': self.user_id.id,'team_id':self.user_id.team_id.id})
                line.sudo().write({'user_id': self.user_id.id,'team_id':self.user_id.team_id.id})
            if rule:
                rule.sudo().active = True 

            """Send a sticky notification to the assigned user."""
            # for line in record:
            #     lead_name = line.name or "Unnamed Lead"
            #     salesperson = self.user_id.name
            #     sale_names = ', '.join(line.order_ids.mapped('name'))
            #     invoice_names = ', '.join(line.order_ids.mapped('invoice_ids').mapped('name'))

            #     message_lines = [f"📌 Lead: {lead_name}"]
                
            #     if sale_names:
            #         message_lines.append(f"🛒 Sale Orders: {sale_names}")
            #     if invoice_names:
            #         message_lines.append(f"🧾 Invoices: {invoice_names}")

            #     message_lines.append(f"👤 Assigned to: {salesperson}")
            #     notification_message = '\n'.join(message_lines)

            #     notification_title = f"Lead Assigned: {lead_name}"

            #     self.env['bus.bus']._sendone(self.user_id.partner_id, 'simple_notification', {
            #         'title': _(notification_title),
            #         'message': _(notification_message),
            #         'sticky': True,
            #         'warning': 'info',
            #     })

            # for line in record:
            #     lead_name = line.name or "Unnamed Lead"
            #     salesperson = self.user_id.name
            #     sale_names = ', '.join(line.order_ids.mapped('name'))
            #     invoice_names = ', '.join(line.order_ids.mapped('invoice_ids').mapped('name'))

                # message_lines = [f"📌 Lead: {lead_name}"]
                
                # if sale_names:
                #     message_lines.append(f"🛒 Sale Orders: {sale_names}")
                # if invoice_names:
                #     message_lines.append(f"🧾 Invoices: {invoice_names}")

                # message_lines.append(f"👤 Assigned to: {salesperson}")
                # notification_message = '\n'.join(message_lines)

                # notification_title = f"🔔 New Lead Assigned: {lead_name}"

                # self.user_id.notify_info(notification_message , notification_title,sticky=True)

    def action_confirm_partner(self):
        if self.env.context.get('model', False) == 'res.partner':
            record = self.env['res.partner'].sudo().search([('id', 'in', self.env.context['id'])])
            for line in record:
                line.sudo().write({'user_id': self.user_id.id})