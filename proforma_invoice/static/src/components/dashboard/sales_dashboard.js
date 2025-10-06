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
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

         onPatched(() => {
            this.destroyCharts();
            this.renderCharts();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            this.state.dashboardData = await this.orm.call("sales.dashboard", "get_dashboard_data", []);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async refreshDashboard() {
        this.destroyCharts();
        await this.loadDashboardData();
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
            let action = await this.orm.call('sales.dashboard', 'action_open_my_leads', []);
            action = this._normalizeAction(action);
            if (action) this.action.doAction(action);
            else console.error("openMyLeads: invalid action", action);
        } catch (err) {
            console.error("openMyLeads error:", err);
        }
    }

    async openMyOpportunities() {
        try {
            let action = await this.orm.call('sales.dashboard', 'action_open_my_opportunities', []);
            action = this._normalizeAction(action);
            if (action) this.action.doAction(action);
            else console.error("openMyOpportunities: invalid action", action);
        } catch (err) {
            console.error("openMyOpportunities error:", err);
        }
    }

    async openMyQuotations(state = null) {
        try {
            let action = await this.orm.call('sales.dashboard', 'action_open_my_quotations', [state]);
            action = this._normalizeAction(action);
            if (action) this.action.doAction(action);
            else console.error("openMyQuotations: invalid action", action);
        } catch (err) {
            console.error("openMyQuotations error:", err);
        }
    }

    async openMyProformas(state = null) {
        try {
            let action = await this.orm.call('sales.dashboard', 'action_open_my_proformas', [state]);
            action = this._normalizeAction(action);
            if (action) this.action.doAction(action);
            else console.error("openMyProformas: invalid action", action);
        } catch (err) {
            console.error("openMyProformas error:", err);
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
            if (action) this.action.doAction(action);
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
            if (action) this.action.doAction(action);
        } catch (err) {
            console.error("openTeamPipeline error:", err);
        }
    }
}

SalesDashboard.template = "proforma_invoice.SalesDashboard";
registry.category("actions").add("proforma_invoice.sales_dashboard", SalesDashboard);