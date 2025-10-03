/** @odoo-module **/


import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class SalesDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user"); // <-- use this.user.id (not userId)

        // Chart refs...
        this.monthlySalesChartRef = useRef("monthlySalesChart");
        this.leadConversionChartRef = useRef("leadConversionChart");
        this.productSalesChartRef = useRef("productSalesChart");
        this.teamPerformanceChartRef = useRef("teamPerformanceChart");
        
        this.state = useState({
            dashboardData: {},
            isLoading: true,
            selectedPeriod: 'month', // month, quarter, year
            showTeamView: false,
        });

        this.charts = {};

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    async loadDashboardData() {
        try {
            this.state.isLoading = true;
            this.state.dashboardData = await this.orm.call(
                "sales.dashboard",
                "get_dashboard_data",
                []
            );
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async refreshDashboard() {
        await this.loadDashboardData();
        this.destroyCharts();
        this.renderCharts();
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    renderCharts() {
        if (this.state.isLoading || !this.state.dashboardData.monthly_sales) return;
        
        this.renderMonthlySalesChart();
        this.renderLeadConversionChart();
        this.renderProductSalesChart();
        if (this.state.dashboardData.is_sales_manager) {
            this.renderTeamPerformanceChart();
        }
    }

    // Helper for number formatting to avoid repetition
    getCurrencyFormat() {
        return new Intl.NumberFormat(this.user.lang.replace('_', '-'), {
            style: 'currency',
            currency: this.state.dashboardData.currency_code || 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    }

    renderMonthlySalesChart() {
        const canvas = this.monthlySalesChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.monthly_sales;
        
        this.charts.monthlySales = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    label: 'Revenue',
                    data: data.map(d => d.revenue),
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Orders',
                    data: data.map(d => d.count),
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4,
                    fill: false,
                    yAxisID: 'y1',
                    hidden: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            // FIX: Changed to arrow function to preserve 'this' context
                            label: (context) => {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';

                                if (context.dataset.yAxisID === 'y1') {
                                    label += context.parsed.y; // For count
                                } else {
                                    label += this.getCurrencyFormat().format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        ticks: {
                             // FIX: Changed to arrow function to preserve 'this' context
                            callback: (value) => this.getCurrencyFormat().format(value)
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { beginAtZero: true }
                    }
                }
            }
        });
    }

    renderLeadConversionChart() {
        const canvas = this.leadConversionChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.lead_conversion;
        
        this.charts.leadConversion = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Leads', 'Opportunities', 'Quotations', 'Won'],
                datasets: [{
                    label: 'Sales Funnel',
                    data: [data.leads, data.opportunities, data.quotations, data.won],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)', 'rgba(168, 85, 247, 0.8)',
                        'rgba(236, 72, 153, 0.8)', 'rgba(34, 197, 94, 0.8)'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    renderProductSalesChart() {
        const canvas = this.productSalesChartRef.el;
        if (!canvas || !this.state.dashboardData.sales_by_product.length) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.sales_by_product;
        const sortedData = [...data].sort((a, b) => b.revenue - a.revenue).slice(0, 5);
        
        this.charts.productSales = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: sortedData.map(d => d.name),
                datasets: [{
                    data: sortedData.map(d => d.revenue),
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)', 'rgba(168, 85, 247, 0.8)',
                        'rgba(236, 72, 153, 0.8)', 'rgba(251, 146, 60, 0.8)',
                        'rgba(34, 197, 94, 0.8)'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    tooltip: {
                        callbacks: {
                             // FIX: Changed to arrow function to preserve 'this' context
                            label: (context) => {
                                const label = context.label || '';
                                const value = this.getCurrencyFormat().format(context.parsed);
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderTeamPerformanceChart() {
        const canvas = this.teamPerformanceChartRef.el;
        if (!canvas || !this.state.dashboardData.team_performance.length) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.state.dashboardData.team_performance.slice(0, 10);
        
        this.charts.teamPerformance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.name.split(' ')[0]),
                datasets: [{
                    label: 'Revenue',
                    data: data.map(d => d.revenue),
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderWidth: 0,
                    yAxisID: 'y',
                }, {
                    label: 'Deals',
                    data: data.map(d => d.deals_closed),
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderWidth: 0,
                    yAxisID: 'y1',
                    hidden: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            afterLabel: (context) => `Pipeline: ${data[context.dataIndex].pipeline} opportunities`
                        }
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        ticks: {
                            // FIX: Changed to arrow function to preserve 'this' context
                            callback: (value) => this.getCurrencyFormat().format(value)
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: false,
                        position: 'right',
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    formatCurrency(value) {
        if (value === undefined || value === null) return this.state.dashboardData.currency_symbol + '0';
        
        const absValue = Math.abs(value);
        if (absValue >= 1000000) {
            return (Math.sign(value) * (absValue / 1000000)).toFixed(1) + 'M';
        }
        if (absValue >= 1000) {
            return (Math.sign(value) * (absValue / 1000)).toFixed(1) + 'K';
        }
        return this.getCurrencyFormat().format(value);
    }

    toggleTeamView() {
        this.state.showTeamView = !this.state.showTeamView;
    }

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