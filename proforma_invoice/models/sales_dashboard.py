from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class SalesDashboard(models.Model):
    _name = 'sales.dashboard'
    _description = 'Sales Dashboard Model - A stateless model to fetch dashboard data.'

    # This model is now stateless. It does not need ORM fields as all data is
    # fetched and returned by a single method call. A dummy 'name' field
    # is kept as a good practice for models.
    name = fields.Char("Name")

    def _get_opportunity_stage_order(self):
        """Helper to get opportunity stages in their correct pipeline order."""
        domain = []
        if not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            domain = [('team_id', 'in', [False, self.env.user.sale_team_id.id])]
        return self.env['crm.stage'].search(domain, order='sequence asc').mapped('name')

    def _get_pipeline_overview_data(self, uid, date_domain):
        # domain = [('user_id', '=', uid)] if uid else []
        # my_leads_opps = self.env['crm.lead'].search(domain)
        # my_opportunities = my_leads_opps.filtered(lambda l: l.type == 'opportunity')
        # leads_count = len(my_leads_opps)
        
        # For Leads
        leads_domain = [('type', '!=', 'opportunity')] + date_domain
        if uid:
            leads_domain.append(('user_id', '=', uid))
            
        my_leads = self.env['crm.lead'].search(leads_domain)
        
        # For Opportunities
        opp_domain = [('type', '=', 'opportunity')] + date_domain
        if uid:
            opp_domain.append(('user_id', '=', uid))
        
        my_opportunities = self.env['crm.lead'].search(opp_domain)
        
        leads_count = len(my_leads)
        opportunities_count = len(my_opportunities)
        total_pipeline_records = leads_count + opportunities_count
        conversion_rate = (opportunities_count / total_pipeline_records * 100) if total_pipeline_records > 0 else 0
        
        return {
            'leads_count': leads_count,
            'opportunities_count': opportunities_count,
            'conversion_rate': f"{conversion_rate:.1f}%",
            'pipeline_revenue': sum(my_opportunities.filtered(lambda o: not o.stage_id.is_won and o.active).mapped('expected_revenue')),
            'won_count': len(my_opportunities.filtered(lambda o: o.stage_id.is_won)),
            'lost_count': len(my_opportunities.filtered(lambda o: not o.active and not o.stage_id.is_won)),
        }

    def _get_opportunity_analysis_data(self, uid, date_domain):
        stage_order = self._get_opportunity_stage_order()
        
        domain_base = [('type', '=', 'opportunity'), ('stage_id.is_won', '=', False), ('active', '=', True)] + date_domain

        # ALL opportunities (open + won + lost)
        domain_all_opps = [('type', '=', 'opportunity'),] + date_domain

        if uid:
            domain_all_opps.append(('user_id', '=', uid))

        stage_count_data = self.env['crm.lead'].read_group(
            domain_all_opps,
            ['stage_id'], groupby=['stage_id'], lazy=False
        )
        stages_count_map = {s['stage_id'][1]: s['__count'] for s in stage_count_data if s['stage_id']}
        
        stage_value_data = self.env['crm.lead'].read_group(
            domain_base + [], # Copy list
            ['expected_revenue:sum'], groupby=['stage_id'], lazy=False
        )
        stages_value_map = {s['stage_id'][1]: s['expected_revenue'] for s in stage_value_data if s['stage_id']}

        domain_source = [('type', '=', 'opportunity')] + date_domain
        if uid:
            domain_source.append(('user_id', '=', uid))

        source_data = self.env['crm.lead'].read_group(
            domain_source,
            ['source_id'], groupby=['source_id'], lazy=False
        )

        won_domain = [('type', '=', 'opportunity'), ('stage_id.is_won', '=', True)] + date_domain
        lost_domain = [('type', '=', 'opportunity'), ('active', '=', False), ('stage_id.is_won', '=', False)] + date_domain
        if uid:
            won_domain.append(('user_id', '=', uid))
            lost_domain.append(('user_id', '=', uid))

        won_deals = self.env['crm.lead'].search(won_domain)
        won_count = len(won_deals)
        lost_count = self.env['crm.lead'].search_count(lost_domain)
        total_closed = won_count + lost_count
        win_rate = (won_count / total_closed * 100) if total_closed > 0 else 0
        total_won_revenue = sum(won_deals.mapped('expected_revenue'))
        avg_deal_size = total_won_revenue / won_count if won_count > 0 else 0

        return {
            'by_stage_count': [{'name': stage, 'count': stages_count_map.get(stage, 0)} for stage in stage_order if stage in stages_count_map],
            'by_stage_value': [{'name': stage, 'value': stages_value_map.get(stage, 0)} for stage in stage_order if stage in stages_value_map],
            'by_source': [{'name': s['source_id'][1] if s['source_id'] else 'Unknown', 'count': s['__count']} for s in source_data],
            'win_rate': f"{win_rate:.1f}%",
            'avg_deal_size': avg_deal_size,
            'top_open_deals': self.env['crm.lead'].search_read(
                domain=domain_base,
                fields=['name', 'partner_id', 'expected_revenue', 'stage_id'],
                order='expected_revenue desc', limit=5
            ),
        }

    def _get_quotation_analysis_data(self, uid, date_domain):
        domain = [] + date_domain
        if uid:
            domain.append(('user_id', '=', uid))
            
        quotation_data = self.env['sale.order'].read_group(
            domain,
            ['state', 'amount_total'], groupby=['state'], lazy=False
        )
        stats = {d['state']: {'count': d['__count'], 'total': d['amount_total']} for d in quotation_data}
        confirmed_count = stats.get('sale', {}).get('count', 0) + stats.get('done', {}).get('count', 0)
        confirmed_revenue = stats.get('sale', {}).get('total', 0) + stats.get('done', {}).get('total', 0)
        return {
            'draft_count': stats.get('draft', {}).get('count', 0),
            'sent_count': stats.get('sent', {}).get('count', 0),
            'confirmed_count': confirmed_count,
            'confirmed_revenue': confirmed_revenue,
            'average_order_value': confirmed_revenue / confirmed_count if confirmed_count > 0 else 0,
        }

    def _get_proforma_analysis_data(self, uid, date_domain):
        domain = [] + date_domain
        if uid:
            domain.append(('user_id', '=', uid))
            
        proforma_data = self.env['proforma.invoice'].read_group(
            domain,
            ['state', 'amount_total'], groupby=['state'], lazy=False
        )
        stats = {d['state']: d for d in proforma_data}
        return {
            'draft_count': stats.get('draft', {}).get('__count', 0),
            'posted_count': stats.get('posted', {}).get('__count', 0),
            'posted_revenue': stats.get('posted', {}).get('amount_total', 0),
        }
    
    def _get_contacts_data(self, uid, date_domain):
        """
        Match Contacts app counter exactly
        """
        domain = [
            ('active', '=', True),          # not archived
            ('type', '!=', 'private'),      # hide private addresses
            ('parent_id', '=', False),      # only top-level contacts
        ]

        domain += date_domain
        if uid:
            domain.append(('user_id', '=', uid))

        total_contacts = self.env['res.partner'].search_count(domain)

        return {
            'total_contacts': total_contacts
        }
    
    def _get_contact_activities_data(self, uid, date_payload):
        """
        Total Contact Activities KPI - Created vs Done
        """
        # 1. Done Activities (filtered by date_done)
        done_domain = [('res_model', '=', 'res.partner'), ('active', '=', False)]
        if uid:
            done_domain.append(('user_id', '=', uid))
        date_done_domain = self._get_date_domain(date_payload, 'date_done')
        total_done = self.env['mail.activity'].with_context(active_test=False).search_count(done_domain + date_done_domain)

        # 2. Created Activities (filtered by create_date)
        created_domain = [('res_model', '=', 'res.partner')]
        if uid:
            created_domain.append(('user_id', '=', uid))
        create_date_domain = self._get_date_domain(date_payload, 'create_date')
        total_created = self.env['mail.activity'].with_context(active_test=False).search_count(created_domain + create_date_domain)

        return {
            'total_contact_activities_done': total_done,
            'total_contact_activities_created': total_created,
        }
    
    def _get_lead_activities_data(self, uid, date_payload):
        """
        Total Lead Activities KPI - Created vs Done
        """
        lead_ids = self.env['crm.lead'].search([('type', '!=', 'opportunity')]).ids

        # 1. Done Activities
        done_domain = [('res_model', '=', 'crm.lead'), ('res_id', 'in', lead_ids), ('active', '=', False)]
        if uid:
            done_domain.append(('user_id', '=', uid))
        date_done_domain = self._get_date_domain(date_payload, 'date_done')
        total_done = self.env['mail.activity'].with_context(active_test=False).search_count(done_domain + date_done_domain)

        # 2. Created Activities
        created_domain = [('res_model', '=', 'crm.lead'), ('res_id', 'in', lead_ids)]
        if uid:
            created_domain.append(('user_id', '=', uid))
        create_date_domain = self._get_date_domain(date_payload, 'create_date')
        total_created = self.env['mail.activity'].with_context(active_test=False).search_count(created_domain + create_date_domain)

        return {
            'total_lead_activities_done': total_done,
            'total_lead_activities_created': total_created,
        }
    
    def _get_opportunity_activities_data(self, uid, date_payload):
        """
        Total Opportunity Activities KPI - Created vs Done
        """
        opp_ids = self.env['crm.lead'].search([('type', '=', 'opportunity')]).ids

        # 1. Done Activities
        done_domain = [('res_model', '=', 'crm.lead'), ('res_id', 'in', opp_ids), ('active', '=', False)]
        if uid:
            done_domain.append(('user_id', '=', uid))
        date_done_domain = self._get_date_domain(date_payload, 'date_done')
        total_done = self.env['mail.activity'].with_context(active_test=False).search_count(done_domain + date_done_domain)

        # 2. Created Activities
        created_domain = [('res_model', '=', 'crm.lead'), ('res_id', 'in', opp_ids)]
        if uid:
            created_domain.append(('user_id', '=', uid))
        create_date_domain = self._get_date_domain(date_payload, 'create_date')
        total_created = self.env['mail.activity'].with_context(active_test=False).search_count(created_domain + create_date_domain)

        return {
            'total_opportunity_activities_done': total_done,
            'total_opportunity_activities_created': total_created,
        }
    
    def _get_sales_over_time_data(self, uid, date_domain):
        """Helper to get sales data for the last 12 months."""
        today = fields.Date.today()
        date_from = today - relativedelta(months=11, day=1)
        
        domain = [
            ('state', 'in', ['sale', 'done']),
        ] + date_domain

        # fallback if All Time
        if not date_domain:
            domain.append(('date_order', '>=', date_from))

        if uid:
            domain.append(('user_id', '=', uid))

        sales_data = self.env['sale.order'].read_group(
            domain=domain,
            fields=['amount_total'],
            groupby=['date_order:month'],
            orderby='date_order:month'
        )
        
        month_map = {item['date_order:month']: item['amount_total'] for item in sales_data}
        
        data = []
        for i in range(11, -1, -1):
            current_month_start = today - relativedelta(months=i, day=1)
            month_key = current_month_start.strftime('%B %Y')
            data.append({
                'month': current_month_start.strftime('%b %Y'),
                'revenue': month_map.get(month_key, 0),
            })
        return data

    def _get_sales_by_category_data(self, uid, date_domain):
        """Helper to get revenue breakdown by product category."""
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
        ] + date_domain
        if uid:
            domain.append(('order_id.user_id', '=', uid))

        product_data = self.env['sale.order.line'].read_group(
            domain=domain,
            fields=['price_subtotal', 'product_id'],
            groupby=['product_id'],
            lazy=False
        )

        if not product_data:
            return []
        
        product_ids = [p['product_id'][0] for p in product_data if p['product_id']]
        product_category_map = {
            p['id']: p['categ_id'][1] if p['categ_id'] else 'Uncategorized'
            for p in self.env['product.product'].search_read([('id', 'in', product_ids)], ['categ_id'])
        }

        category_revenue = {}
        for p_data in product_data:
            if not p_data['product_id']:
                continue
            product_id = p_data['product_id'][0]
            category_name = product_category_map.get(product_id, 'Uncategorized')
            revenue = p_data['price_subtotal']
            
            category_revenue.setdefault(category_name, 0.0)
            category_revenue[category_name] += revenue

        return [{'name': name, 'revenue': rev} for name, rev in category_revenue.items()]
        
    def _get_top_products_data(self, uid, date_domain):
        """Helper to get top 5 selling products by revenue."""
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
        ] + date_domain
        if uid:
            domain.append(('order_id.user_id', '=', uid))

        product_data = self.env['sale.order.line'].read_group(
            domain=domain,
            fields=['price_subtotal'],
            groupby=['product_id'],
            orderby='price_subtotal desc',
            limit=5,
            lazy=False
        )
        return [{'name': p['product_id'][1], 'revenue': p['price_subtotal']} for p in product_data if p['product_id']]
    

    # Add date domain builder
    def _get_date_domain(self, payload, field_name):
        if not payload or payload.get('filter') == 'all':
            return []

        today = fields.Date.today()

        if payload['filter'] == 'today':
            start = today
            end = today

        elif payload['filter'] == 'custom':
            start = payload.get('date_from')
            end = payload.get('date_to')
            if not start or not end:
                return []
        else:
            return []

        return [
            (field_name, '>=', start),
            (field_name, '<=', end),
        ]

    @api.model
    def get_dashboard_data(self, date_payload=None):

        """ The main controller method that calls helpers and assembles the data. """
        try:
            # We rely on Odoo's standard Record Rules to filter data. 
            # By passing filter_uid=None, we avoid imposing an extra ('user_id', '=', uid) domain.
            
            filter_uid = None

            # Manager check for Team Analysis tab
            is_sales_manager = self.env.user.has_group('sales_team.group_sale_manager')

            lead_date_domain      = self._get_date_domain(date_payload, 'create_date')
            order_date_domain     = self._get_date_domain(date_payload, 'date_order')
            invoice_date_domain   = self._get_date_domain(date_payload, 'invoice_date')
            orderline_date_domain = self._get_date_domain(date_payload, 'order_id.date_order')
            partner_date_domain   = self._get_date_domain(date_payload, 'create_date')

            pipeline_overview    = self._get_pipeline_overview_data(filter_uid, lead_date_domain)
            opportunity_analysis = self._get_opportunity_analysis_data(filter_uid, lead_date_domain)
            quotation_analysis   = self._get_quotation_analysis_data(filter_uid, order_date_domain)
            proforma_analysis    = self._get_proforma_analysis_data(filter_uid, invoice_date_domain)
            contacts_analysis    = self._get_contacts_data(filter_uid, partner_date_domain)
            contact_activities   = self._get_contact_activities_data(filter_uid, date_payload)
            lead_activities        = self._get_lead_activities_data(filter_uid, date_payload)
            opportunity_activities = self._get_opportunity_activities_data(filter_uid, date_payload)

            quotation_analysis['sales_over_time']   = self._get_sales_over_time_data(filter_uid, order_date_domain)
            quotation_analysis['sales_by_category'] = self._get_sales_by_category_data(filter_uid, orderline_date_domain)
            quotation_analysis['top_products']      = self._get_top_products_data(filter_uid, orderline_date_domain)


            return {
                'pipeline_overview'      : pipeline_overview,
                'opportunity_analysis'   : opportunity_analysis,
                'quotation_analysis'     : quotation_analysis,
                'proforma_analysis'      : proforma_analysis,
                'contacts_analysis'      : contacts_analysis,
                'contact_activities'     : contact_activities,
                'lead_activities'        : lead_activities,
                'opportunity_activities' : opportunity_activities,
                
                'is_sales_manager'  : is_sales_manager,
                'currency_id'       : self.env.company.currency_id.id,
                'currency_symbol'   : self.env.company.currency_id.symbol,
                'currency_code'     : self.env.company.currency_id.name,
            }
        except Exception as e:
            _logger.error("Error in get_dashboard_data: %s", str(e), exc_info=True)
            return {}

    # --- NAVIGATION ACTION METHODS (STILL REQUIRED) ---

    @api.model
    def action_open_my_leads(self, payload=None):
        # Return all records allowed by record rules
        domain = [('type', '!=', 'opportunity')]

        # ✅ DATE FILTER (minimal add)
        if payload:
            filter_type = payload.get('filter')
            date_from = payload.get('date_from')
            date_to = payload.get('date_to')

            if filter_type == 'today':
                today = fields.Date.context_today(self)
                domain += [
                    ('create_date', '>=', today),
                    ('create_date', '<=', today),
                ]

            elif filter_type == 'custom' and date_from and date_to:
                domain += [
                    ('create_date', '>=', date_from),
                    ('create_date', '<=', date_to),
                ]
        # ✅ END DATE FILTER

        return { 
            'name': 'My Leads', 
            'type': 'ir.actions.act_window', 
            'res_model': 'crm.lead',
            'views': [[False, 'tree'], [False, 'kanban'], [False, 'form']],
            'domain': domain
        }

    @api.model
    def action_open_my_opportunities(self, payload=None):
        domain = [('type', '=', 'opportunity')]

        # ✅ DATE FILTER (minimal add)
        if payload:
            filter_type = payload.get('filter')
            date_from = payload.get('date_from')
            date_to = payload.get('date_to')

            if filter_type == 'today':
                today = fields.Date.context_today(self)
                domain += [
                    ('create_date', '>=', today),
                    ('create_date', '<=', today),
                ]

            elif filter_type == 'custom' and date_from and date_to:
                domain += [
                    ('create_date', '>=', date_from),
                    ('create_date', '<=', date_to),
                ]
        # ✅ END DATE FILTER

        return { 
            'name': 'My Opportunities', 
            'type': 'ir.actions.act_window', 
            'res_model': 'crm.lead',
            'views': [[False, 'tree'], [False, 'kanban'], [False, 'form']],
            'domain': domain
        }

    @api.model
    def action_open_my_quotations(self, state=None, payload=None):
        domain = []
        
        action_name = 'My Quotations'

        if state == 'draft':
            domain.append(('state', '=', 'draft'))
            action_name = 'My Draft Quotations (from Opps)'
        elif state == 'sent':
            domain.append(('state', '=', 'sent'))
            action_name = 'My Sent Quotations (from Opps)'
        elif state == 'confirmed':
            domain.append(('state', 'in', ['sale', 'done']))
            action_name = 'My Confirmed Orders'

        # ✅ DATE FILTER (MINIMAL ADD)
        if payload:
            filter_type = payload.get('filter')
            date_from = payload.get('date_from')
            date_to = payload.get('date_to')

            if filter_type == 'today':
                today = fields.Date.context_today(self)
                domain += [
                    ('date_order', '>=', today),
                    ('date_order', '<=', today),
                ]

            elif filter_type == 'custom' and date_from and date_to:
                domain += [
                    ('date_order', '>=', date_from),
                    ('date_order', '<=', date_to),
                ]
        # ✅ END DATE FILTER

        return { 
            'name': action_name, 
            'type': 'ir.actions.act_window', 
            'res_model': 'sale.order',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': domain 
        }

    @api.model
    def action_open_my_proformas(self, state=None, payload=None):
        domain = []

        action_name = 'My Proformas'

        if state == 'draft':
            domain.append(('state', '=', 'draft'))
            action_name = 'My Draft Proformas (from Opps)'

        elif state == 'posted':
            domain.append(('state', '=', 'posted'))
            action_name = 'My Confirmed Proformas'

        # ✅ DATE FILTER ADDED (ONLY THIS PART NEW)
        if payload:
            filter_type = payload.get('filter')
            date_from = payload.get('date_from')
            date_to = payload.get('date_to')

            if filter_type == 'today':
                today = fields.Date.context_today(self)
                domain += [
                    ('invoice_date', '>=', today),
                    ('invoice_date', '<=', today),
                ]

            elif filter_type == 'custom' and date_from and date_to:
                domain += [
                    ('invoice_date', '>=', date_from),
                    ('invoice_date', '<=', date_to),
                ]
        # ✅ END DATE FILTER

        return { 
            'name': action_name, 
            'type': 'ir.actions.act_window', 
            'res_model': 'proforma.invoice',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': domain 
        }
        
    @api.model
    def action_open_my_sales_order(self, payload=None):
        domain = []

        action_name = 'My Sales Orders'

        # ✅ DATE FILTER (MINIMAL ADDITION)
        if payload:
            filter_type = payload.get('filter')
            date_from = payload.get('date_from')
            date_to = payload.get('date_to')

            if filter_type == 'today':
                today = fields.Date.context_today(self)
                domain += [
                    ('date_order', '>=', today),
                    ('date_order', '<=', today),
                ]

            elif filter_type == 'custom' and date_from and date_to:
                domain += [
                    ('date_order', '>=', date_from),
                    ('date_order', '<=', date_to),
                ]
        # ✅ END
        
        return { 
            'name': action_name, 
            'type': 'ir.actions.act_window', 
            'res_model': 'custom.sale.order',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': domain 
        }

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    dashboard_feedback_safe = fields.Text(string='Feedback Message', compute='_compute_dashboard_feedback_safe')

    def _compute_dashboard_feedback_safe(self):
        """
        Safely fetches done_feedback from the database without needing crm_17 in depends.
        """
        # Check if column exists in DB to avoid crash
        self.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='mail_activity' AND column_name='done_feedback'
        """)
        has_field = bool(self.env.cr.fetchone())

        for rec in self:
            if has_field:
                # Use raw SQL to fetch the value to avoid Odoo Registry errors
                self.env.cr.execute("SELECT done_feedback FROM mail_activity WHERE id = %s", [rec.id])
                res = self.env.cr.fetchone()
                rec.dashboard_feedback_safe = res[0] if res else False
            else:
                # Fallback to the standard note field if done_feedback isn't found
                rec.dashboard_feedback_safe = rec.note or False
