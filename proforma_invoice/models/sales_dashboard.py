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

    def _get_pipeline_overview_data(self, uid):
        domain = [('user_id', '=', uid)] if uid else []
        my_leads_opps = self.env['crm.lead'].search(domain)
        my_opportunities = my_leads_opps.filtered(lambda l: l.type == 'opportunity')
        
        leads_count = len(my_leads_opps)
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

    def _get_opportunity_analysis_data(self, uid):
        stage_order = self._get_opportunity_stage_order()
        
        domain_base = [('type', '=', 'opportunity'), ('stage_id.is_won', '=', False), ('active', '=', True)]
        if uid:
            domain_base.append(('user_id', '=', uid))

        stage_count_data = self.env['crm.lead'].read_group(
            domain_base,
            ['stage_id'], groupby=['stage_id'], lazy=False
        )
        stages_count_map = {s['stage_id'][1]: s['__count'] for s in stage_count_data if s['stage_id']}
        
        stage_value_data = self.env['crm.lead'].read_group(
            domain_base + [], # Copy list
            ['expected_revenue:sum'], groupby=['stage_id'], lazy=False
        )
        stages_value_map = {s['stage_id'][1]: s['expected_revenue'] for s in stage_value_data if s['stage_id']}

        domain_source = [('type', '=', 'opportunity')]
        if uid:
            domain_source.append(('user_id', '=', uid))

        source_data = self.env['crm.lead'].read_group(
            domain_source,
            ['source_id'], groupby=['source_id'], lazy=False
        )

        won_domain = [('type', '=', 'opportunity'), ('stage_id.is_won', '=', True)]
        lost_domain = [('type', '=', 'opportunity'), ('active', '=', False), ('stage_id.is_won', '=', False)]
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

    def _get_quotation_analysis_data(self, uid):
        domain = []
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

    def _get_proforma_analysis_data(self, uid):
        domain = []
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
    
    def _get_sales_over_time_data(self, uid):
        """Helper to get sales data for the last 12 months."""
        today = fields.Date.today()
        date_from = today - relativedelta(months=11, day=1)
        
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', date_from),
        ]
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

    def _get_sales_by_category_data(self, uid):
        """Helper to get revenue breakdown by product category."""
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
        ]
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
        
    def _get_top_products_data(self, uid):
        """Helper to get top 5 selling products by revenue."""
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
        ]
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
    
    def _get_team_overview_data(self, member_ids):
        """Calculates high-level aggregated stats for the team."""
        if not member_ids:
            return {}

        # Team Pipeline
        leads_count = self.env['crm.lead'].search_count([('user_id', 'in', member_ids), ('type', '=', 'lead'), ('stage_id.is_won', '=', False)])
        opportunities_count = self.env['crm.lead'].search_count([('user_id', 'in', member_ids), ('type', '=', 'opportunity'), ('active', '=', True), ('stage_id.is_won', '=', False)])
        pipeline_data = self.env['crm.lead'].read_group([('user_id', 'in', member_ids), ('type', '=', 'opportunity'), ('active', '=', True), ('stage_id.is_won', '=', False)], ['expected_revenue:sum'], [], lazy=False)
        
        # Team Win Rate
        won_count = self.env['crm.lead'].search_count([('user_id', 'in', member_ids), ('type', '=', 'opportunity'), ('stage_id.is_won', '=', True)])
        lost_count = self.env['crm.lead'].search_count([('user_id', 'in', member_ids), ('type', '=', 'opportunity'), ('active', '=', False), ('stage_id.is_won', '=', False)])
        total_closed = won_count + lost_count
        win_rate = (won_count / total_closed * 100) if total_closed > 0 else 0

        # Team Revenue
        revenue_data = self.env['sale.order'].read_group([('user_id', 'in', member_ids), ('state', 'in', ['sale', 'done'])], ['amount_total:sum'], [], lazy=False)
        
        return {
            'leads_count': leads_count,
            'opportunities_count': opportunities_count,
            'pipeline_revenue': pipeline_data[0]['expected_revenue'] if pipeline_data and pipeline_data[0]['expected_revenue'] else 0,
            'win_rate': f"{win_rate:.1f}%",
            'total_revenue': revenue_data[0]['amount_total'] if revenue_data and revenue_data[0]['amount_total'] else 0,
        }

    def _get_team_sales_over_time_data(self, member_ids):
        """Gets aggregated team sales data for the last 12 months."""
        if not member_ids:
            return []
            
        today = fields.Date.today()
        date_from = today - relativedelta(months=11, day=1)
        
        sales_data = self.env['sale.order'].read_group(
            domain=[
                ('user_id', 'in', member_ids),
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', date_from),
            ],
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

    def _get_team_member_performance_data(self, member_ids):
        """Gets revenue breakdown by team member."""
        if not member_ids:
            return []
            
        performance_data = self.env['sale.order'].read_group(
            domain=[
                ('user_id', 'in', member_ids),
                ('state', 'in', ['sale', 'done']),
            ],
            fields=['amount_total'],
            groupby=['user_id'],
            orderby='amount_total desc',
            lazy=False
        )
        return [{'name': perf['user_id'][1], 'revenue': perf['amount_total']} for perf in performance_data if perf['user_id']]
    
    @api.model
    def get_dashboard_data(self):
        """ The main controller method that calls helpers and assembles the data. """
        try:
            # We rely on Odoo's standard Record Rules to filter data. 
            # By passing filter_uid=None, we avoid imposing an extra ('user_id', '=', uid) domain.
            
            filter_uid = None

            # Manager check for Team Analysis tab
            is_sales_manager = self.env.user.has_group('sales_team.group_sale_manager')

            pipeline_overview = self._get_pipeline_overview_data(filter_uid)
            opportunity_analysis = self._get_opportunity_analysis_data(filter_uid)
            quotation_analysis = self._get_quotation_analysis_data(filter_uid)
            proforma_analysis = self._get_proforma_analysis_data(filter_uid)

            quotation_analysis['sales_over_time'] = self._get_sales_over_time_data(filter_uid)
            quotation_analysis['sales_by_category'] = self._get_sales_by_category_data(filter_uid)
            quotation_analysis['top_products'] = self._get_top_products_data(filter_uid)

            team_analysis = {}
            if is_sales_manager:
                team = self.env['crm.team'].search([('user_id', '=', self.env.uid)], limit=1)
                if team:
                    member_ids = team.member_ids.ids + [team.user_id.id]
                    team_analysis = {
                        'overview': self._get_team_overview_data(member_ids),
                        'sales_over_time': self._get_team_sales_over_time_data(member_ids),
                        'member_performance': self._get_team_member_performance_data(member_ids),
                    }

            return {
                'pipeline_overview': pipeline_overview,
                'opportunity_analysis': opportunity_analysis,
                'quotation_analysis': quotation_analysis,
                'proforma_analysis': proforma_analysis,
                
                'team_analysis': team_analysis, 
                
                'is_sales_manager': is_sales_manager,
                'currency_id': self.env.company.currency_id.id,
                'currency_symbol': self.env.company.currency_id.symbol,
                'currency_code': self.env.company.currency_id.name,
            }
        except Exception as e:
            _logger.error("Error in get_dashboard_data: %s", str(e), exc_info=True)
            return {}

    # --- NAVIGATION ACTION METHODS (STILL REQUIRED) ---

    @api.model
    def action_open_my_leads(self):
        # Return all records allowed by record rules
        return { 'name': 'My Leads', 'type': 'ir.actions.act_window', 'res_model': 'crm.lead',
            'views': [[False, 'tree'], [False, 'kanban'], [False, 'form']],
            'domain': [] }

    @api.model
    def action_open_my_opportunities(self):
        return { 'name': 'My Opportunities', 'type': 'ir.actions.act_window', 'res_model': 'crm.lead',
            'views': [[False, 'kanban'], [False, 'tree'], [False, 'form']],
            'domain': [('type', '=', 'opportunity')] }

    @api.model
    def action_open_my_quotations(self, state=None):
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
        return { 'name': action_name, 'type': 'ir.actions.act_window', 'res_model': 'sale.order',
            'views': [[False, 'tree'], [False, 'form'], [False, 'kanban']],
            'domain': domain }

    @api.model
    def action_open_my_proformas(self, state=None):
        domain = []

        action_name = 'My Proformas'
        if state == 'draft':
            domain.append(('state', '=', 'draft'))
            action_name = 'My Draft Proformas (from Opps)'
        elif state == 'posted':
            domain.append(('state', '=', 'posted'))
            action_name = 'My Confirmed Proformas'
        return { 'name': action_name, 'type': 'ir.actions.act_window', 'res_model': 'proforma.invoice',
            'views': [[False, 'tree'], [False, 'form']],
            'domain': domain }