from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class SalesDashboard(models.Model):
    _name = 'sales.dashboard'
    _description = 'Sales Dashboard Model'

    name = fields.Char() # Dummy field
    
    # My Statistics
    my_leads_count = fields.Integer(compute='_compute_my_data')
    my_opportunities_count = fields.Integer(compute='_compute_my_data')
    my_draft_quotations_count = fields.Integer(compute='_compute_my_data')
    my_sent_quotations_count = fields.Integer(compute='_compute_my_data')
    my_confirmed_quotations_count = fields.Integer(compute='_compute_my_data')
    my_confirmed_quotations_revenue = fields.Monetary(compute='_compute_my_data', currency_field='currency_id')
    my_draft_proformas_count = fields.Integer(compute='_compute_my_data')
    my_sent_proformas_count = fields.Integer(compute='_compute_my_data')
    my_confirmed_proformas_count = fields.Integer(compute='_compute_my_data')
    my_confirmed_proformas_total = fields.Monetary(compute='_compute_my_data', currency_field='currency_id')
    my_pipeline_revenue = fields.Monetary(compute='_compute_my_data', currency_field='currency_id')
    my_won_opportunities_count = fields.Integer(compute='_compute_my_data')
    my_lost_opportunities_count = fields.Integer(compute='_compute_my_data')
    
    # Team Statistics
    is_sales_manager = fields.Boolean(compute='_compute_team_data')
    team_leads_count = fields.Integer(compute='_compute_team_data')
    team_opportunities_count = fields.Integer(compute='_compute_team_data')
    team_draft_quotations_count = fields.Integer(compute='_compute_team_data')
    team_confirmed_quotations_revenue = fields.Monetary(compute='_compute_team_data', currency_field='currency_id')
    team_confirmed_proformas_total = fields.Monetary(compute='_compute_team_data', currency_field='currency_id')
    team_pipeline_revenue = fields.Monetary(compute='_compute_team_data', currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    def _compute_my_data(self):
        for record in self:
            uid = self.env.uid
            
            # Leads & Opportunities
            leads = self.env['crm.lead'].search([('user_id', '=', uid)])
            record.my_leads_count = len(leads.filtered(lambda l: l.type == 'lead' and not l.stage_id.is_won))
            opportunities = leads.filtered(lambda l: l.type == 'opportunity')
            record.my_opportunities_count = len(opportunities.filtered(lambda o: not o.stage_id.is_won and not o.active == False))
            record.my_won_opportunities_count = len(opportunities.filtered(lambda o: o.stage_id.is_won))
            record.my_lost_opportunities_count = len(opportunities.filtered(lambda o: o.active == False and not o.stage_id.is_won))
            record.my_pipeline_revenue = sum(opportunities.filtered(lambda o: not o.stage_id.is_won and o.active).mapped('expected_revenue'))
            
            # Quotations
            quotations = self.env['sale.order'].search([('user_id', '=', uid)])
            record.my_draft_quotations_count = len(quotations.filtered(lambda q: q.state == 'draft'))
            record.my_sent_quotations_count = len(quotations.filtered(lambda q: q.state == 'sent'))
            confirmed_quotations = quotations.filtered(lambda q: q.state in ['sale', 'done'])
            record.my_confirmed_quotations_count = len(confirmed_quotations)
            record.my_confirmed_quotations_revenue = sum(confirmed_quotations.mapped('amount_total'))
            
            # Proformas
            proformas = self.env['proforma.invoice'].search([('user_id', '=', uid)])
            record.my_draft_proformas_count = len(proformas.filtered(lambda p: p.state == 'draft'))
            record.my_sent_proformas_count = len(proformas.filtered(lambda p: p.state == 'sent'))
            confirmed_proformas = proformas.filtered(lambda p: p.state == 'posted')
            record.my_confirmed_proformas_count = len(confirmed_proformas)
            record.my_confirmed_proformas_total = sum(confirmed_proformas.mapped('amount_total'))

    def _compute_team_data(self):
        for record in self:
            team = self.env['crm.team'].search([('user_id', '=', self.env.uid)], limit=1)
            record.is_sales_manager = bool(team)
            
            if team:
                team_members = team.member_ids.ids + [team.user_id.id]
                
                # Team Leads & Opportunities
                team_leads = self.env['crm.lead'].search([('user_id', 'in', team_members)])
                record.team_leads_count = len(team_leads.filtered(lambda l: l.type == 'lead' and not l.stage_id.is_won))
                team_opportunities = team_leads.filtered(lambda l: l.type == 'opportunity')
                record.team_opportunities_count = len(team_opportunities.filtered(lambda o: not o.stage_id.is_won and o.active))
                record.team_pipeline_revenue = sum(team_opportunities.filtered(lambda o: not o.stage_id.is_won and o.active).mapped('expected_revenue'))
                
                # Team Quotations
                team_quotations = self.env['sale.order'].search([('user_id', 'in', team_members)])
                record.team_draft_quotations_count = len(team_quotations.filtered(lambda q: q.state in ['draft', 'sent']))
                team_confirmed = team_quotations.filtered(lambda q: q.state in ['sale', 'done'])
                record.team_confirmed_quotations_revenue = sum(team_confirmed.mapped('amount_total'))
                
                # Team Proformas
                team_proformas = self.env['proforma.invoice'].search([('user_id', 'in', team_members), ('state', '=', 'posted')])
                record.team_confirmed_proformas_total = sum(team_proformas.mapped('amount_total'))
            else:
                record.team_leads_count = 0
                record.team_opportunities_count = 0
                record.team_draft_quotations_count = 0
                record.team_confirmed_quotations_revenue = 0
                record.team_confirmed_proformas_total = 0
                record.team_pipeline_revenue = 0

    @api.model
    def get_dashboard_data(self):
        """Called by the Owl component to fetch all dashboard data."""
        dashboard = self.new({})
        dashboard._compute_my_data()
        dashboard._compute_team_data()
        
        # Get time-series data for charts
        monthly_sales = self._get_monthly_sales_data()
        lead_conversion = self._get_lead_conversion_data()
        top_customers = self._get_top_customers()
        sales_by_product = self._get_sales_by_product()
        team_performance = self._get_team_performance() if dashboard.is_sales_manager else []

        return {
            # My Statistics
            'my_leads_count': dashboard.my_leads_count,
            'my_opportunities_count': dashboard.my_opportunities_count,
            'my_draft_quotations_count': dashboard.my_draft_quotations_count,
            'my_sent_quotations_count': dashboard.my_sent_quotations_count,
            'my_confirmed_quotations_count': dashboard.my_confirmed_quotations_count,
            'my_confirmed_quotations_revenue': dashboard.my_confirmed_quotations_revenue,
            'my_draft_proformas_count': dashboard.my_draft_proformas_count,
            'my_sent_proformas_count': dashboard.my_sent_proformas_count,
            'my_confirmed_proformas_count': dashboard.my_confirmed_proformas_count,
            'my_confirmed_proformas_total': dashboard.my_confirmed_proformas_total,
            'my_pipeline_revenue': dashboard.my_pipeline_revenue,
            'my_won_opportunities_count': dashboard.my_won_opportunities_count,
            'my_lost_opportunities_count': dashboard.my_lost_opportunities_count,
            
            # Team Statistics
            'is_sales_manager': dashboard.is_sales_manager,
            'team_leads_count': dashboard.team_leads_count,
            'team_opportunities_count': dashboard.team_opportunities_count,
            'team_draft_quotations_count': dashboard.team_draft_quotations_count,
            'team_confirmed_quotations_revenue': dashboard.team_confirmed_quotations_revenue,
            'team_confirmed_proformas_total': dashboard.team_confirmed_proformas_total,
            'team_pipeline_revenue': dashboard.team_pipeline_revenue,
            
            # Chart Data
            'monthly_sales': monthly_sales,
            'lead_conversion': lead_conversion,
            'top_customers': top_customers,
            'sales_by_product': sales_by_product,
            'team_performance': team_performance,
            
            # Currency
            'currency_id': self.env.company.currency_id.id,
            'currency_symbol': self.env.company.currency_id.symbol,
            'currency_code': self.env.company.currency_id.name,
        }
    
    @api.model
    def _get_monthly_sales_data(self):
        """Get sales data for the last 12 months using a single query."""
        uid = self.env.uid
        today = fields.Date.today()
        date_from = today - relativedelta(months=11, day=1)
        sales_data = self.env['sale.order'].read_group(
            domain=[
                ('user_id', '=', uid),
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', date_from),
            ],
            fields=['amount_total'],
            groupby=['date_order:month'],
            orderby='date_order:month'
        )

        month_map = {item['date_order:month']: item for item in sales_data}

        data = []
        for i in range(11, -1, -1):
            current_month_start = today - relativedelta(months=i, day=1)
            month_key = current_month_start.strftime('%B %Y')

            result = month_map.get(month_key, {})
            data.append({
                'month': current_month_start.strftime('%b %Y'),
                'revenue': result.get('amount_total', 0),
                'count': result.get('__count', 0)
            })

        return data
    
    @api.model
    def _get_lead_conversion_data(self):
        """Get lead conversion funnel data"""
        uid = self.env.uid
        leads = self.env['crm.lead'].search([('user_id', '=', uid)])
        
        return {
            'leads': len(leads.filtered(lambda l: l.type == 'lead')),
            'opportunities': len(leads.filtered(lambda l: l.type == 'opportunity')),
            'quotations': self.env['sale.order'].search_count([
                ('user_id', '=', uid),
                ('opportunity_id', '!=', False)
            ]),
            'won': len(leads.filtered(lambda l: l.stage_id.is_won)),
        }
    
    @api.model
    def _get_top_customers(self):
        """Get top 5 customers by revenue"""
        uid = self.env.uid
        sales = self.env['sale.order'].search([
            ('user_id', '=', uid),
            ('state', 'in', ['sale', 'done'])
        ])
        
        customer_revenue = {}
        for sale in sales:
            partner = sale.partner_id
            if partner.id not in customer_revenue:
                customer_revenue[partner.id] = {
                    'name': partner.name,
                    'revenue': 0,
                    'order_count': 0
                }
            customer_revenue[partner.id]['revenue'] += sale.amount_total
            customer_revenue[partner.id]['order_count'] += 1
        
        sorted_customers = sorted(customer_revenue.values(), key=lambda x: x['revenue'], reverse=True)
        return sorted_customers[:5]
    
    @api.model
    def _get_sales_by_product(self):
        """Get sales distribution by product category"""
        uid = self.env.uid
        sales = self.env['sale.order'].search([
            ('user_id', '=', uid),
            ('state', 'in', ['sale', 'done'])
        ])
        
        category_sales = {}
        for sale in sales:
            for line in sale.order_line:
                category = line.product_id.categ_id
                if category.id not in category_sales:
                    category_sales[category.id] = {
                        'name': category.name,
                        'revenue': 0
                    }
                category_sales[category.id]['revenue'] += line.price_subtotal
        
        return list(category_sales.values())
    
    @api.model
    def _get_team_performance(self):
        """Get team members performance data"""
        team = self.env['crm.team'].search([('user_id', '=', self.env.uid)], limit=1)
        if not team:
            return []
        
        team_members = team.member_ids + team.user_id
        performance = []
        
        for member in team_members:
            sales = self.env['sale.order'].search([
                ('user_id', '=', member.id),
                ('state', 'in', ['sale', 'done'])
            ])
            
            performance.append({
                'name': member.name,
                'revenue': sum(sales.mapped('amount_total')),
                'deals_closed': len(sales),
                'pipeline': self.env['crm.lead'].search_count([
                    ('user_id', '=', member.id),
                    ('type', '=', 'opportunity'),
                    ('stage_id.is_won', '=', False)
                ])
            })
        
        return sorted(performance, key=lambda x: x['revenue'], reverse=True)

    @api.model
    def action_open_my_leads(self):
        return {
            'name': 'My Leads',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'tree,kanban,form',
            'domain': [('type', '=', 'lead'), ('user_id', '=', self.env.uid)]
        }

    @api.model
    def action_open_my_opportunities(self):
        return {
            'name': 'My Opportunities',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'kanban,tree,form',
            'domain': [('type', '=', 'opportunity'), ('user_id', '=', self.env.uid)]
        }

    @api.model
    def action_open_my_quotations(self, state=None):
        # Prefer existing quotation action; fallback to a generic action dict
        try:
            action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        except Exception:
            # fallback to standard sale quotations action
            action = self.env.ref('sale.action_quotations').read()[0]

        domain = [('user_id', '=', self.env.uid)]
        if state == 'draft':
            domain.append(('state', '=', 'draft'))
            action['name'] = 'My Draft Quotations'
        elif state == 'sent':
            domain.append(('state', '=', 'sent'))
            action['name'] = 'My Sent Quotations'
        elif state == 'confirmed':
            domain.append(('state', 'in', ['sale', 'done']))
            action['name'] = 'My Confirmed Quotations'
        else:
            action['name'] = 'My Quotations'

        action['domain'] = domain
        return action

    @api.model
    def action_open_my_proformas(self, state=None):
        # Try to return the module's proforma action if present, else build a minimal action
        try:
            action = self.env.ref('proforma_invoice.action_proforma_invoice').read()[0]
        except Exception:
            action = {
                'name': 'My Proforma Invoices',
                'type': 'ir.actions.act_window',
                'res_model': 'proforma.invoice',
                'view_mode': 'tree,form',
                'domain': [('user_id', '=', self.env.uid)]
            }

        domain = [('user_id', '=', self.env.uid)]
        if state == 'draft':
            domain.append(('state', '=', 'draft'))
            action['name'] = 'My Draft Proformas'
        elif state == 'sent':
            domain.append(('state', '=', 'sent'))
            action['name'] = 'My Sent Proformas'
        elif state == 'posted':
            domain.append(('state', '=', 'posted'))
            action['name'] = 'My Confirmed Proformas'
        else:
            action['name'] = action.get('name', 'My Proforma Invoices')

        action['domain'] = domain
        return action