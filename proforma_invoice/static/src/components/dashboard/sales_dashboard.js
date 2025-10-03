/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

class SalesDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.user = useService("user");

        // Chart refs
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

    // Navigation actions (no changes needed here)
    openMyLeads() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('My Leads'),
            res_model: 'crm.lead',
            views: [[false, 'tree'], [false, 'kanban'], [false, 'form']],
            domain: [['type', '=', 'lead'], ['user_id', '=', this.user.userId]],
        });
    }

    openMyOpportunities() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('My Opportunities'),
            res_model: 'crm.lead',
            views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
            domain: [['type', '=', 'opportunity'], ['user_id', '=', this.user.userId]],
        });
    }

    openMyQuotations(state = null) {
        let domain = [['user_id', '=', this.user.userId]];
        let name = _t('My Quotations');
        
        if (state === 'draft') {
            domain.push(['state', '=', 'draft']);
            name = _t('My Draft Quotations');
        } else if (state === 'sent') {
            domain.push(['state', '=', 'sent']);
            name = _t('My Sent Quotations');
        } else if (state === 'confirmed') {
            domain.push(['state', 'in', ['sale', 'done']]);
            name = _t('My Confirmed Quotations');
        }
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: 'sale.order',
            views: [[false, 'tree'], [false, 'form'], [false, 'kanban']],
            domain: domain,
        });
    }

    openMyProformas(state = null) {
        let domain = [['user_id', '=', this.user.userId]];
        let name = _t('My Proforma Invoices');
        
        if (state === 'draft') {
            domain.push(['state', '=', 'draft']);
            name = _t('My Draft Proformas');
        } else if (state === 'sent') {
            domain.push(['state', '=', 'sent']);
            name = _t('My Sent Proformas');
        } else if (state === 'posted') {
            domain.push(['state', '=', 'posted']);
            name = _t('My Confirmed Proformas');
        }
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: name,
            res_model: 'proforma.invoice',
            views: [[false, 'tree'], [false, 'form']],
            domain: domain,
        });
    }

    openTopCustomers() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Top Customers'),
            res_model: 'res.partner',
            views: [[false, 'tree'], [false, 'form']],
            domain: [['customer_rank', '>', 0]],
        });
    }

    openTeamPipeline() {
        const team_member_ids = this.state.dashboardData.team_performance.map(m => m.id);
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Team Pipeline'),
            res_model: 'crm.lead',
            views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
            domain: [['user_id', 'in', team_member_ids], ['type', '=', 'opportunity']],
        });
    }
}

SalesDashboard.template = "proforma_invoice.SalesDashboard";
registry.category("actions").add("proforma_invoice.sales_dashboard", SalesDashboard);