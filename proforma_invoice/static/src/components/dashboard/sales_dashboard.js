/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef, onPatched } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class SalesDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");
        this.charts = {};

        this.oppsByStageChartRef = useRef("oppsByStageChart");
        this.oppsBySourceChartRef = useRef("oppsBySourceChart");
        this.pipelineValueByStageChartRef = useRef("pipelineValueByStageChart");
        this.salesOverTimeChartRef = useRef("salesOverTimeChart");
        this.salesByCategoryChartRef = useRef("salesByCategoryChart");

        this.state = useState({
            dashboardData: {},
            isLoading: true,
            activeTab: 'overview',
            dateFilter: 'all',
            dateFrom: null,
            dateTo: null,
        });

        onWillStart(async () => {
            const isDrillDown = sessionStorage.getItem('dashboard_drilldown');
            this._restoreDashboardState(isDrillDown);
            sessionStorage.removeItem('dashboard_drilldown');
            await this.loadDashboardData();
        });

        onPatched(() => {
            this.destroyCharts();
            this.renderCharts();
        });
    }

    _restoreDashboardState(isDrillDown = false) {
        const saved = sessionStorage.getItem('sales_dashboard_state');
        if (!saved) {
            this.state.dateFilter = 'all';
            return;
        }

        const data = JSON.parse(saved);
        this.state.activeTab = data.activeTab || 'overview';

        // Reset date filters unless we are coming back from a drill-down
        if (isDrillDown) {
            this.state.dateFilter = data.dateFilter || 'all';
            this.state.dateFrom = data.dateFrom || null;
            this.state.dateTo = data.dateTo || null;
        } else {
            this.state.dateFilter = 'all';
            this.state.dateFrom = null;
            this.state.dateTo = null;
        }
    }

    _setDrillDownFlag() {
        sessionStorage.setItem('dashboard_drilldown', 'true');
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            const data = await this.orm.call(
                "sales.dashboard",
                "get_dashboard_data",
                [this._getDatePayload()]
            );

            // SAFETY DEFAULTS
            this.state.dashboardData = data || {};
            this.state.dashboardData.pipeline_overview ??= {};
            this.state.dashboardData.opportunity_analysis ??= {};
            this.state.dashboardData.quotation_analysis ??= {};
            this.state.dashboardData.proforma_analysis ??= {};
            this.state.dashboardData.team_analysis ??= {};
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    // Add payload builder
    _getDatePayload() {
        return {
            filter: this.state.dateFilter,
            date_from: this.state.dateFrom,
            date_to: this.state.dateTo,
        };
    }

    // Handle dropdown change
    async onDateFilterChange() {
        if (this.state.dateFilter !== 'custom') {
            this.state.dateFrom = null;
            this.state.dateTo = null;
            await this.refreshDashboard();
        }
    }

    // Handle custom date change
    async onCustomDateChange() {
        if (this.state.dateFrom && this.state.dateTo) {
            await this.refreshDashboard();
        }
    }

    async refreshDashboard() {
        this.destroyCharts();
        await this.loadDashboardData();
        this._saveDashboardState();   // ✅ remember filter when navigating away
        // The onPatched hook will automatically call renderCharts after data is loaded and state is set
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    renderCharts() {
        if (this.state.isLoading || !this.state.dashboardData) return;

        if (this.state.activeTab === 'opportunities' && this.state.dashboardData.opportunity_analysis) {
            this.renderOppsByStageChart();
            this.renderOppsBySourceChart();
            this.renderPipelineValueByStageChart();
        } else if (this.state.activeTab === 'quotations' && this.state.dashboardData.quotation_analysis) {
            this.renderSalesOverTimeChart();
            this.renderSalesByCategoryChart();
        }
    }


    renderOppsByStageChart() {
        const canvas = this.oppsByStageChartRef.el;
        if (!canvas) return;
        const data = this.state.dashboardData.opportunity_analysis.by_stage_count || [];
        const ctx = canvas.getContext('2d');
        this.charts.oppsByStage = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: data.map(d => d.name), datasets: [{ data: data.map(d => d.count), backgroundColor: ['rgba(76, 81, 191, 0.8)', 'rgba(102, 126, 234, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(245, 159, 11, 0.8)'] }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
        });
    }

    renderOppsBySourceChart() {
        const canvas = this.oppsBySourceChartRef.el;
        if (!canvas) return;
        const data = this.state.dashboardData.opportunity_analysis.by_source || [];
        const ctx = canvas.getContext('2d');
        this.charts.oppsBySource = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: data.map(d => d.name), datasets: [{ data: data.map(d => d.count), backgroundColor: ['rgba(76, 81, 191, 0.8)', 'rgba(102, 126, 234, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(245, 159, 11, 0.8)', 'rgba(16, 185, 129, 0.8)', 'rgba(107, 114, 128, 0.8)'] }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
        });
    }

    renderPipelineValueByStageChart() {
        const canvas = this.pipelineValueByStageChartRef.el;
        if (!canvas) return;
        const data = this.state.dashboardData.opportunity_analysis.by_stage_value || [];
        const ctx = canvas.getContext('2d');
        this.charts.pipelineValue = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    label: 'Pipeline Value',
                    data: data.map(d => d.value),
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                }]
            },
            options: {
                indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    renderSalesOverTimeChart() {
        const canvas = this.salesOverTimeChartRef.el;
        if (!canvas) return;
        const data = this.state.dashboardData.quotation_analysis.sales_over_time || [];
        const ctx = canvas.getContext('2d');
        this.charts.salesOverTime = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    label: 'Sales Revenue',
                    data: data.map(d => d.revenue),
                    borderColor: 'rgba(76, 81, 191, 1)',
                    backgroundColor: 'rgba(76, 81, 191, 0.1)',
                    fill: true,
                    tension: 0.3,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { callback: (value) => this.formatCurrency(value) } } }
            }
        });
    }

    renderSalesByCategoryChart() {
        const canvas = this.salesByCategoryChartRef.el;
        if (!canvas) return;
        const data = this.state.dashboardData.quotation_analysis.sales_by_category || [];
        const ctx = canvas.getContext('2d');
        this.charts.salesByCategory = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    data: data.map(d => d.revenue),
                    backgroundColor: ['#4c51bf', '#667eea', '#3b82f6', '#f59e0b', '#10b981', '#6b7280', '#ef4444', '#ec4899'],
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.formatCurrency(context.parsed);
                                return ` ${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    }


    formatCurrency(value) {
        if (value === undefined || value === null) return (this.state.dashboardData.currency_symbol || '$') + '0';
        const formatter = new Intl.NumberFormat(this.user.lang.replace('_', '-'), {
            style: 'currency', currency: this.state.dashboardData.currency_code || 'USD',
            minimumFractionDigits: 0, maximumFractionDigits: 0,
        });
        const absValue = Math.abs(value);
        if (absValue >= 1000000) return (this.state.dashboardData.currency_symbol || '$') + (Math.sign(value) * (absValue / 1000000)).toFixed(1) + 'M';
        if (absValue >= 1000) return (this.state.dashboardData.currency_symbol || '$') + (Math.sign(value) * (absValue / 1000)).toFixed(1) + 'K';
        return formatter.format(value);
    }

    // --- YOUR EXISTING NAVIGATION LOGIC (UNCHANGED) ---
    _normalizeAction(action) {
        if (!action || typeof action !== 'object') {
            return null;
        }
        action.type = action.type || 'ir.actions.act_window';
        if (!Array.isArray(action.domain)) {
            if (typeof action.domain === 'string') {
                try {
                    action.domain = JSON.parse(action.domain);
                } catch (e) {
                    action.domain = action.domain ? [action.domain] : [];
                }
            } else {
                action.domain = action.domain || [];
            }
        }
        if (action.context && typeof action.context === 'string') {
            try {
                action.context = JSON.parse(action.context);
            } catch (e) {
                action.context = {};
            }
        } else {
            action.context = action.context || {};
        }
        if (action.views === undefined || action.views === null) {
            if (action.view_mode && typeof action.view_mode === 'string') {
                action.views = action.view_mode.split(',')
                    .map(v => v.trim())
                    .filter(Boolean)
                    .map(v => [false, v]);
            } else if (Array.isArray(action.view_mode)) {
                action.views = action.view_mode.map(v => [false, v]);
            } else if (Array.isArray(action.views)) {
            } else {
                action.views = [[false, 'tree'], [false, 'form'], [false, 'kanban']];
            }
        }
        if (!Array.isArray(action.views) && action.view_id) {
            action.views = [[action.view_id.id || action.view_id, action.view_type || 'form']];
        }
        return action;
    }

    async openMyLeads() {
        try {
            const payload = this._getDatePayload()
            let action = await this.orm.call('sales.dashboard', 'action_open_my_leads', [payload]);
            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
            else console.error("openMyLeads: invalid action", action);
        } catch (err) {
            console.error("openMyLeads error:", err);
        }
    }

    async openMyOpportunities() {
        try {
            const payload = this._getDatePayload();
            let action = await this.orm.call('sales.dashboard', 'action_open_my_opportunities', [payload]);
            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
            else console.error("openMyOpportunities: invalid action", action);
        } catch (err) {
            console.error("openMyOpportunities error:", err);
        }
    }

    async openMyQuotations(state = null) {
        try {
            const payload = this._getDatePayload();
            let action = await this.orm.call('sales.dashboard', 'action_open_my_quotations', [state, payload]);
            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
            else console.error("openMyQuotations: invalid action", action);
        } catch (err) {
            console.error("openMyQuotations error:", err);
        }
    }

    async openMyProformas(state = null) {
        try {
            const payload = this._getDatePayload();   // ⭐ get date filter
            let action = await this.orm.call(
                'sales.dashboard',
                'action_open_my_proformas',
                [state, payload]
            );

            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
            else console.error("openMyProformas: invalid action", action);

        } catch (err) {
            console.error("openMyProformas error:", err);
        }
    }

    async openMySalesOrder() {
        try {
            const payload = this._getDatePayload();
            let action = await this.orm.call('sales.dashboard', 'action_open_my_sales_order', [payload])
            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
            else console.error("openMySalesOrder: invalid action", action);
        } catch (err) {
            console.error("openMySalesOrder error:", err);
        }
    }

    openTopCustomers() {
        try {
            let action = {
                type: 'ir.actions.act_window',
                name: _t('Top Customers'),
                res_model: 'res.partner',
                views: [[false, 'tree'], [false, 'form']],
                domain: [['customer_rank', '>', 0]],
            };
            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
        } catch (err) {
            console.error("openTopCustomers error:", err);
        }
    }

    openTeamPipeline() {
        try {
            const team_member_ids = this.state.dashboardData.team_performance.map(m => m.id);
            let action = {
                type: 'ir.actions.act_window',
                name: _t('Team Pipeline'),
                res_model: 'crm.lead',
                views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
                domain: [['user_id', 'in', team_member_ids], ['type', '=', 'opportunity']],
            };
            action = this._normalizeAction(action);
            if (action) {
                this._setDrillDownFlag();
                this.action.doAction(action);
            }
        } catch (err) {
            console.error("openTeamPipeline error:", err);
        }
    }

    async openContacts() {
        const payload = this._getDatePayload();

        let domain = [
            ['active', '=', true],
            ['type', '!=', 'private'],
            ['parent_id', '=', false],
        ];

        // Apply date filter
        if (payload.filter === 'today') {
            const today = new Date().toISOString().split('T')[0];
            domain.push(['create_date', '>=', today]);
            domain.push(['create_date', '<=', today]);
        }
        else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['create_date', '>=', payload.date_from]);
            domain.push(['create_date', '<=', payload.date_to]);
        }

        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contacts',
            res_model: 'res.partner',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
        });
    }

    // today - //new Date().toISOString().split('T')[0]; //UTC date
    async openContactActivitiesDone() {
        const payload = this._getDatePayload();
        let domain = [
            ['res_model', '=', 'res.partner'],
            ['active', '=', false],
        ];
        if (payload.filter === 'today') {
            const today = luxon.DateTime.local().toISODate();
            domain.push(['date_done', '>=', today], ['date_done', '<=', today]);
        } else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['date_done', '>=', payload.date_from], ['date_done', '<=', payload.date_to]);
        }
        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Completed Contact Activities',
            res_model: 'mail.activity',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { active_test: false, search_default_my_activities: 1, tree_view_ref: 'proforma_invoice.mail_activity_view_tree_done_dashboard' }
        });
    }

    async openContactActivitiesCreated() {
        const payload = this._getDatePayload();
        let domain = [['res_model', '=', 'res.partner']];
        if (payload.filter === 'today') {
            const today = luxon.DateTime.local().toISODate();
            domain.push(['create_date', '>=', today + ' 00:00:00'], ['create_date', '<=', today + ' 23:59:59']);
        } else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['create_date', '>=', payload.date_from + ' 00:00:00'], ['create_date', '<=', payload.date_to + ' 23:59:59']);
        }
        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Created Contact Activities',
            res_model: 'mail.activity',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { active_test: false }
        });
    }

    async openLeadActivitiesDone() {
        const payload = this._getDatePayload();
        const leadIds = await this.orm.search('crm.lead', [['type', '!=', 'opportunity']]);
        let domain = [
            ['res_model', '=', 'crm.lead'],
            ['res_id', 'in', leadIds],
            ['active', '=', false],
        ];
        if (payload.filter === 'today') {
            const today = luxon.DateTime.local().toISODate();
            domain.push(['date_done', '>=', today], ['date_done', '<=', today]);
        } else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['date_done', '>=', payload.date_from], ['date_done', '<=', payload.date_to]);
        }
        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Completed Lead Activities',
            res_model: 'mail.activity',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { active_test: false, tree_view_ref: 'proforma_invoice.mail_activity_view_tree_done_dashboard' }
        });
    }

    async openLeadActivitiesCreated() {
        const payload = this._getDatePayload();
        const leadIds = await this.orm.search('crm.lead', [['type', '!=', 'opportunity']]);
        let domain = [['res_model', '=', 'crm.lead'], ['res_id', 'in', leadIds]];
        if (payload.filter === 'today') {
            const today = luxon.DateTime.local().toISODate();
            domain.push(['create_date', '>=', today + ' 00:00:00'], ['create_date', '<=', today + ' 23:59:59']);
        } else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['create_date', '>=', payload.date_from + ' 00:00:00'], ['create_date', '<=', payload.date_to + ' 23:59:59']);
        }
        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Created Lead Activities',
            res_model: 'mail.activity',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { active_test: false }
        });
    }

    async openOpportunityActivitiesDone() {
        const payload = this._getDatePayload();
        const oppIds = await this.orm.search('crm.lead', [['type', '=', 'opportunity']]);
        let domain = [
            ['res_model', '=', 'crm.lead'],
            ['res_id', 'in', oppIds],
            ['active', '=', false],
        ];
        if (payload.filter === 'today') {
            const today = luxon.DateTime.local().toISODate();
            domain.push(['date_done', '>=', today], ['date_done', '<=', today]);
        } else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['date_done', '>=', payload.date_from], ['date_done', '<=', payload.date_to]);
        }
        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Completed Opportunity Activities',
            res_model: 'mail.activity',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { active_test: false, tree_view_ref: 'proforma_invoice.mail_activity_view_tree_done_dashboard' }
        });
    }

    async openOpportunityActivitiesCreated() {
        const payload = this._getDatePayload();
        const oppIds = await this.orm.search('crm.lead', [['type', '=', 'opportunity']]);
        let domain = [['res_model', '=', 'crm.lead'], ['res_id', 'in', oppIds]];
        if (payload.filter === 'today') {
            const today = luxon.DateTime.local().toISODate();
            domain.push(['create_date', '>=', today + ' 00:00:00'], ['create_date', '<=', today + ' 23:59:59']);
        } else if (payload.filter === 'custom' && payload.date_from && payload.date_to) {
            domain.push(['create_date', '>=', payload.date_from + ' 00:00:00'], ['create_date', '<=', payload.date_to + ' 23:59:59']);
        }
        this._setDrillDownFlag();
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Created Opportunity Activities',
            res_model: 'mail.activity',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            context: { active_test: false }
        });
    }

    _saveDashboardState() {
        sessionStorage.setItem('sales_dashboard_state', JSON.stringify({
            activeTab: this.state.activeTab,
            dateFilter: this.state.dateFilter,
            dateFrom: this.state.dateFrom,
            dateTo: this.state.dateTo,
        }));
    }
}

SalesDashboard.template = "proforma_invoice.SalesDashboard";
registry.category("actions").add("proforma_invoice.sales_dashboard", SalesDashboard);