from odoo import models, fields, api, _

class InheritAccountPayment(models.Model):
    _inherit = "account.payment"

    cheque_reference = fields.Char(string="Cheque Reference", copy=False)
    bank_reference = fields.Char(string="Bank Reference", copy=False)
    effective_date = fields.Date('Effective Date',
                                 help='Effective date of PDC', copy=False,
                                 default=False)
    # invoice_pay_is = fields.Boolean(string="invoice Payment Pending Is", copy=False,compute='_compute_invoice_pay',)

    payment_line_ids = fields.One2many('account.payment.line','mst_id',string="payment line")
    pay_amount = fields.Float(string="Pay Amount", copy=False)
    due_amount = fields.Float(string="Due Amount", copy=False)
    remaining_amt = fields.Float(string="Remaining Amount", copy=False)

    def update_amount(self):
        for rec in self:
            if tuple(self.ids):
                self._cr.execute('''
                SELECT
                    round(sum(part.amount),2) as amount
                FROM account_payment payment
                JOIN account_move move ON move.id = payment.move_id
                JOIN account_move_line line ON line.move_id = move.id
                JOIN account_partial_reconcile part ON
                    part.debit_move_id = line.id
                    OR
                    part.credit_move_id = line.id
                JOIN account_move_line counterpart_line ON
                    part.debit_move_id = counterpart_line.id
                    OR
                    part.credit_move_id = counterpart_line.id
                JOIN account_move invoice ON invoice.id = counterpart_line.move_id
                JOIN account_account account ON account.id = line.account_id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                    AND payment.id IN %(payments)s
                    AND line.id != counterpart_line.id
                    AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                    ''', {
                        'payments': tuple(self.ids)
                    })
                query_res = self._cr.dictfetchone()
                rec.pay_amount  = query_res.get('amount',0)
                rec.due_amount = self.amount - rec.pay_amount

    @api.onchange('payment_line_ids')
    def _onchange_payment_line_ids(self):
        total_adjustment_amount = self.due_amount
        for line in self.payment_line_ids:
            if total_adjustment_amount > 0 and line.adjustment:
                if line.amount_residual > total_adjustment_amount:
                    line.adjustment_amt = total_adjustment_amount
                else:
                    line.adjustment_amt = line.amount_residual
                
                total_adjustment_amount -= line.adjustment_amt  # Reduce remaining amount
            else:
                line.adjustment_amt = 0 
                line.adjustment = False
        self.remaining_amt = self.due_amount - sum(self.payment_line_ids.mapped('adjustment_amt'))
    def action_post(self):
        ret = super(InheritAccountPayment, self).action_post()
        self.create_payment_line_ids()
        return ret
              
    @api.onchange('partner_id')
    @api.depends('partner_id')
    def create_payment_line_ids(self):
        for rec in self:
            rec.payment_line_ids = False
            line_list = []
            if rec.payment_type == 'inbound':
                invoice_rec = self.env['account.move'].sudo().search([('partner_id', '=', rec.partner_id.id),('move_type', '=', 'out_invoice'),('state', '=', 'posted')])
                if invoice_rec:
                    for inv in invoice_rec:
                        if inv.amount_residual > 0:
                            line_list.append((0,0,{'invoice_id':inv.id,
                                                   'amount_residual':inv.amount_residual,
                                                   'amount_total':inv.amount_total,
                                                   'bill_amt':inv.amount_total - inv.amount_residual}))

            if rec.payment_type == 'outbound':
                invoice_rec = self.env['account.move'].sudo().search([('partner_id', '=', rec.partner_id.id),('move_type', '=', 'in_invoice'),('state', '=', 'posted')])
                if invoice_rec:
                    for inv in invoice_rec:
                        if inv.amount_residual > 0:
                            line_list.append((0,0,{'invoice_id':inv.id,
                                                   'amount_residual':inv.amount_residual,
                                                   'amount_total':inv.amount_total,
                                                   'bill_amt':inv.amount_total - inv.amount_residual}))

            if line_list:
                rec.payment_line_ids = line_list
            # rec.invoice_pay_is = True

        self.update_amount()
        self._onchange_payment_line_ids()


    def action_apply_payment(self):
        for line in self.payment_line_ids:
            if self.due_amount > 0 and line.adjustment:
                move_line =[]
                if line.invoice_id:
                    context_vals =  line.invoice_id.invoice_outstanding_credits_debits_widget.get('content',False)                
                    for m_line in context_vals:
                        if m_line.get('journal_name',False) == self.name:
                            move_line.append(m_line.get('id'))
                    if move_line:
                        line.invoice_id.sudo().js_assign_outstanding_line(move_line)
                    self.update_amount()
        self.create_payment_line_ids()

class AccountPaymentLine(models.Model):
    _name = "account.payment.line"
    _description = 'Account Payment Line'

    mst_id = fields.Many2one('account.payment',string="Mst")

    invoice_id = fields.Many2one('account.move',string="invoice")
    amount_residual = fields.Float(string="Amount Due")
    date = fields.Date(related='invoice_id.date',string="Bill Date")
    amount_total = fields.Float(string="Amount")
    bill_amt = fields.Float(string="Bill Amount")
    adjustment_amt = fields.Float(string="Adjustment Amount")
    adjustment = fields.Boolean(string="Adjustment",default=False)
    invoice_outstanding_credits_debits_widget = fields.Binary(related='invoice_id.invoice_outstanding_credits_debits_widget')

    def action_open_invoice(self):
        self.ensure_one()
        name = 'Invoice'
        if self.mst_id.payment_type == 'outbound':
            name = 'Bills'            
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'target': 'new',
        }

class InheritAccount(models.Model):
    _inherit = "account.move"
    def js_remove_outstanding_partial(self, partial_id):
            self.ensure_one()
            partial = self.env['account.partial.reconcile'].browse(partial_id)
            rec =  partial.unlink()
            if self.payment_id:
                self.payment_id.create_payment_line_ids()
            return rec