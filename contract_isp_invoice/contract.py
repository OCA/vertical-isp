# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import sys
import logging
import time
import datetime
from openerp.osv import orm, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.contract_isp.contract import add_months, date_interval
from openerp import netsvc
import openerp.exceptions

_logger = logging.getLogger(__name__)


class res_company(orm.Model):
    _inherit = "res.company"

    def _days(self, cr, uid, context=None):
        return tuple([(str(x), str(x)) for x in range(1, 29)])

    _columns = {
        'invoice_day': fields.selection(_days, 'Invoice day'),
        'send_email_contract_invoice': fields.boolean('Send invoice by email')
    }

    _defaults = {
        'send_email_contract_invoice': True
    }


class res_partner(orm.Model):
    _inherit = "res.partner"

    def _get_default_payment_term(self, cr, uid, context=None):
        return self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'contract_isp_invoice',
            'account_payment_term_end_of_month')[1]

    _defaults = {
        'property_payment_term': lambda s, cr, uid, ctx: s._get_default_payment_term(cr, uid, ctx)
    }


class account_voucher(orm.Model):
    _inherit = 'account.voucher'

    _columns = {
        'later_validation': fields.boolean('Later Validation'),
        'original_amount': fields.float(
            'Original Amount', digits_compute=dp.get_precision('Account'),
            required=True, readonly=True,
            states={'draft':[('readonly',False)]}),
    }

    _defaults = {
        'later_validation': False
    }

    def onchange_journal(self, cr, uid, ids, journal_id, line_ids,
                         tax_id, partner_id, date, amount, ttype,
                         company_id, context=None):
        if not journal_id:
            return False

        ret = super(account_voucher, self).onchange_journal(
            cr, uid, ids, journal_id, line_ids,
            tax_id, partner_id, date, amount, ttype,
            company_id, context=None)
        account_journal = self.pool.get('account.journal').browse(
            cr, uid, journal_id, context=context)

        ret['value']['later_validation'] = account_journal.later_validation

        return ret

    def create(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        if context.get('original_amount', False) and data.get('amount', False):
            if data['amount'] < data['original_amount']:
                raise orm.except_orm(
                    _('Error'),
                    _('Amount cannot be less than the invoice amount'))

        return super(account_voucher, self).create(
            cr, uid, data, context=context)

    def proforma_voucher(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        ret = True
        account_analytic_account_obj = self.pool.get(
            'account.analytic.account')
        account_invoice_obj = self.pool.get('account.invoice')

        voucher = self.browse(cr, uid, ids[0], context=context)

        if context.get('not_subscription_voucher', True) is False:

            if context.get('active_model') == 'account.analytic.account' and \
               context.get('active_id', False):
                for line in account_analytic_account_obj.browse(
                        cr, uid, context.get('active_id'),
                        context=context).contract_service_ids:
                    line.create_analytic_line(
                        mode='subscription',
                        date=datetime.datetime.today())

                inv = account_analytic_account_obj.create_invoice(
                    cr, uid, context.get('active_id'), context=context)

                a = account_invoice_obj._workflow_signal(
                    cr, uid, [inv],
                    'invoice_open', context=context)

            else:
                raise openerp.exceptions.Warning(_('Contract not found'))

            if voucher.journal_id.later_validation is False:
                ret = super(account_voucher, self).proforma_voucher(
                    cr, uid, ids, context=context)


            if voucher.journal_id.later_validation is False:
                account_move_line_obj = self.pool.get('account.move.line')
                query = [
                    ('partner_id', '=', voucher.partner_id.id),
                    ('account_id', '=', voucher.partner_id.property_account_receivable.id),
                    ('reconcile_id', '=', False)
                ]

                ids_to_reconcile = account_move_line_obj.search(cr, uid, query,
                                                                context=context)
                if ids_to_reconcile:
                    # Code from account/wizard/account_reconcile.py/\
                    #    account_move_line_reconcile/trans_rec_reconcile_full
                    period_obj = self.pool.get('account.period')
                    date = False
                    period_id = False
                    journal_id = False
                    account_id = False

                    date = time.strftime('%Y-%m-%d')
                    ctx = dict(context or {}, account_period_prefer_normal=True)
                    period_ids = period_obj.find(cr, uid, dt=date, context=ctx)
                    if period_ids:
                        period_id = ids[0]
                        account_move_line_obj.reconcile(cr, uid, ids_to_reconcile,
                                                        'manual', account_id,
                                                        period_id, journal_id,
                                                        context=context)

            mail_template_obj = self.pool.get('email.template')
            ir_model_data_obj = self.pool.get('ir.model.data')
            mail_template_id = ir_model_data_obj.get_object_reference(
                cr, uid, 'account', 'email_template_edi_invoice')[1]
            mail_mail_obj = self.pool.get('mail.mail')
            if isinstance(inv, list):
                for i in inv:
                    mail_id = mail_template_obj.send_mail(
                        cr, uid, mail_template_id, i, context=context)
                    mail_message = mail_mail_obj.browse(
                        cr, uid, mail_id, context=context).mail_message_id
                    mail_message.write({'type': 'email'})
        else:
            ret = super(account_voucher, self).proforma_voucher(
                cr, uid, ids, context=context)

        return ret


class account_journal(orm.Model):
    _inherit = 'account.journal'

    _columns = {
        'later_validation': fields.boolean('Later Validation')
    }

    _defaults = {
        'later_validation': False
    }


class account_analytic_account(orm.Model):
    _inherit = "account.analytic.account"

    _columns = {
        'close_date': fields.datetime('Close date'),
        'close_reason': fields.text('Reasons')
    }

    _defaults = {
        'close_date': fields.datetime.now
    }

    def create_invoice(self, cr, uid, ids, prorata=False, context=None):
        return_int = False
        if isinstance(ids, int):
            return_int = True
            ids = [ids]

        account_analytic_account_obj = self.pool.get('account.analytic.account')
        account_analytic_line = self.pool.get('account.analytic.line')
        contract_service_obj = self.pool.get('contract.service')
        res_company_obj = self.pool.get('res.company')
        account_invoice_obj = self.pool.get('account.invoice')
        res_company_data = res_company_obj.read(
            cr, uid,
            res_company_obj._company_default_get(cr, uid, context),
            context=context)
        wf_service = netsvc.LocalService("workflow")

        if res_company_data['send_email_contract_invoice']:
            mail_template_obj = self.pool.get('email.template')
            ir_model_data_obj = self.pool.get('ir.model.data')
            mail_template_id = ir_model_data_obj.get_object_reference(
                cr, uid, 'account',
                'email_template_edi_invoice')[1]
            mail_mail_obj = self.pool.get('mail.mail')

        cuttoff_day = res_company_data['cutoff_day']

        cutoff_date = datetime.date(
            datetime.date.today().year,
            datetime.date.today().month,
            int(cuttoff_day)
        )

        invoice_day = res_company_data['invoice_day']

        invoice_date = datetime.date(
            datetime.date.today().year,
            datetime.date.today().month,
            int(invoice_day)
        )

        if prorata:
            if datetime.date.today() <= cutoff_date:
                date_invoice = invoice_date.strftime('%Y-%m-%d')
            else:
                date_invoice = add_months(invoice_date, 1).strftime(
                    '%Y-%m-%d')

        ret = []
        for contract_id in ids:
            query = [('account_id', '=', contract_id),
                     ('to_invoice', '!=', False),
                     ('invoice_id', '=', False),
                     ('product_id', '!=', False),
                     ('is_prorata', '=', prorata)]

            ids_to_invoice = account_analytic_line.search(cr, uid, query,
                                                          context=context)
            if ids_to_invoice:
                _logger.info(
                    "Invoicing contract %s" %
                    account_analytic_account_obj.browse(
                        cr, uid, contract_id, context=context).name)

                data = {
                    'name': True,
                }
                inv = account_analytic_line.invoice_cost_create(
                    cr, uid, ids_to_invoice, data=data, context=context)
                if isinstance(inv, list):
                    for i in inv:
                        ret.append(i)

                else:
                    ret.append(inv)

                # jgama - If its a prorata invoice, change the invoice date
                #         according to the invoice_day variable
                if prorata:
                    account_invoice_obj.write(
                        cr, uid, inv, {'date_invoice': date_invoice},
                        context=context)

                if context.get('not_subscription_voucher', True):
                    _logger.debug(
                        "Opening invoice %s" % account_invoice_obj.browse(
                            cr, uid, inv[0], context=context).name)

                    wf_service.trg_validate(
                        uid, 'account.invoice', inv[0], 'invoice_open', cr)
                    #a = account_invoice_obj._workflow_signal(
                    #    cr, uid, inv, 'invoice_open', context)

                    if res_company_data['send_email_contract_invoice']:
                        _logger.info(
                            "Mailing invoice %s" % account_invoice_obj.browse(
                                cr, uid, inv[0], context=context).name)

                        ctx = dict(context, default_type='email')

                        try:
                            mail_id = mail_template_obj.send_mail(
                                cr, uid, mail_template_id, inv[0], context=ctx)
                            mail_message = mail_mail_obj.browse(
                                cr, uid, mail_id,
                                context=context).mail_message_id
                            mail_message.write({'type': 'email'})
                        except:
                            _logger.error(
                                'Error generating mail for invoice %s:'
                                '\n\n%s' % (
                                    account_invoice_obj.browse(
                                        cr, uid, inv[0], context=context).name,
                                    sys.exc_info()[0]))

        if return_int:
            if len(ret) == 0:
                return None
            else:
                return ret[0]
        else:
            return ret

    def set_close(self, cr, uid, ids, context=None):

        return {
            'type': 'ir.actions.act_window',
            'src_model': 'account.analytic.account',
            'res_model': 'contract.isp.close',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new'
        }

    def prepare_voucher(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        res_currency_obj = self.pool.get('res.currency')
        account_analytic_account_obj = self.pool.get(
            'account.analytic.account')
        account_invoice_obj = self.pool.get('account.invoice')

        cur = self.browse(
            cr, uid, ids[0], context=context).pricelist_id.currency_id

        amount_tax = amount_untaxed = 0
        for line in self.browse(
                cr, uid, ids[0], context=context).contract_service_ids:
            for c in self.pool.get('account.tax').compute_all(
                    cr, uid, line.product_id.taxes_id, line.unit_price,
                    line.qty, line.product_id,
                    line.account_id.partner_id)['taxes']:
                amount_tax += c.get('amount', 0.0)

            amount_untaxed += line.unit_price * line.qty
        amount = res_currency_obj.round(cr, uid, cur, amount_tax) + \
            res_currency_obj.round(cr, uid, cur, amount_untaxed)

        # jgama - Create the activation invoice
        context['not_subscription_voucher'] = False

        # amount = account_invoice_obj.browse(
        #     cr, uid, inv, context=context).amount_total

        view_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'account_voucher', 'view_vendor_receipt_form')[1]

        partner = self.browse(
            cr, uid, ids[0], context=context).partner_id

        voucher_partner_id = partner.parent_id and \
            partner.parent_id.id or partner.id

        return {
            'name': _('Create Voucher'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.voucher',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {'not_subscription_voucher': False,
                        'default_type': 'receipt',
                        'default_amount': amount,
                        'original_amount': amount,
                        'default_partner_id': voucher_partner_id}
        }


class account_analytic_line(orm.Model):
    _inherit = 'account.analytic.line'

    def invoice_cost_create(self, cr, uid, ids, data=None, context=None):
        # jgama - Sligtly modified version. Original from
        #         hr_timesheet_invoice.py

        analytic_account_obj = self.pool.get('account.analytic.account')
        account_payment_term_obj = self.pool.get('account.payment.term')
        invoice_obj = self.pool.get('account.invoice')
        product_obj = self.pool.get('product.product')
        invoice_factor_obj = self.pool.get('hr_timesheet_invoice.factor')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        product_uom_obj = self.pool.get('product.uom')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoices = []
        if context is None:
            context = {}
        if data is None:
            data = {}

        journal_types = {}

        # prepare for iteration on journal and accounts
        for line in self.pool.get('account.analytic.line').browse(
                cr, uid, ids, context=context):
            if line.journal_id.type not in journal_types:
                journal_types[line.journal_id.type] = set()
            journal_types[line.journal_id.type].add(line.account_id.id)
        for journal_type, account_ids in journal_types.items():
            for account in analytic_account_obj.browse(
                    cr, uid, list(account_ids), context=context):
                # jgama - If there's a parent, invoice the parent
                partner = account.partner_id.parent_id or account.partner_id

                if (not partner) or not (account.pricelist_id):
                    raise orm.except_orm(
                        _('Analytic Account Incomplete!'),
                        _('Contract incomplete. Please fill in the Customer and Pricelist fields.'))

                date_due = False
                if partner.property_payment_term:
                    pterm_list = account_payment_term_obj.compute(
                        cr, uid, partner.property_payment_term.id, value=1,
                        date_ref=time.strftime('%Y-%m-%d'))
                    if pterm_list:
                        pterm_list = [line[0] for line in pterm_list]
                        pterm_list.sort()
                        date_due = pterm_list[-1]

                curr_invoice = {
                    'name': time.strftime('%d/%m/%Y') + ' - ' + account.name,
                    'origin': account.name,
                    'partner_id': partner.id,
                    'company_id': account.company_id.id,
                    'payment_term': partner.property_payment_term.id or False,
                    'account_id': partner.property_account_receivable.id,
                    'currency_id': account.pricelist_id.currency_id.id,
                    'date_due': date_due,
                    'fiscal_position': partner.property_account_position.id
                }
                context2 = context.copy()
                context2['lang'] = partner.lang
                # set company_id in context, so the correct default journal
                # will be selected
                context2['force_company'] = curr_invoice['company_id']
                # set force_company in context so the correct product
                # properties are selected (eg. income account)
                context2['company_id'] = curr_invoice['company_id']

                last_invoice = invoice_obj.create(
                    cr, uid, curr_invoice, context=context2)
                invoices.append(last_invoice)

                cr.execute("""SELECT product_id, user_id, to_invoice, sum(amount), sum(unit_amount), product_uom_id
                        FROM account_analytic_line as line LEFT JOIN account_analytic_journal journal ON (line.journal_id = journal.id)
                        WHERE account_id = %s
                            AND line.id IN %s AND journal.type = %s AND to_invoice IS NOT NULL
                        GROUP BY product_id, user_id, to_invoice, product_uom_id""", (account.id, tuple(ids), journal_type))

                for product_id, user_id, factor_id, total_price, qty, uom in cr.fetchall():
                    context2.update({'uom': uom})

                    if data.get('product'):
                        # force product, use its public price
                        product_id = data['product'][0]
                        unit_price = self._get_invoice_price(
                            cr, uid, account, product_id, user_id, qty, context2)
                    #elif journal_type == 'general' and product_id:
                    #    # timesheets, use sale price
                    #    unit_price = self._get_invoice_price(cr, uid, account, product_id, user_id, qty, context2)
                    else:
                        # expenses, using price from amount field
                        unit_price = qty and total_price * -1.0 / qty or 0.0

                    factor = invoice_factor_obj.browse(
                        cr, uid, factor_id, context=context2)
                    # factor_name = factor.customer_name and line_name + ' - ' + factor.customer_name or line_name
                    factor_name = ''
                    if data.get('factor_name', False):
                        factor_name = factor.customer_name

                    curr_line = {
                        'price_unit': unit_price,
                        'quantity': qty,
                        'product_id': product_id or False,
                        'discount': factor.factor,
                        'invoice_id': last_invoice,
                        'name': factor_name,
                        'uos_id': uom,
                        'account_analytic_id': account.id,
                    }
                    product = product_obj.browse(
                        cr, uid, product_id, context=context2)
                    if product:
                        factor_name = data.get('product_name', '') and \
                            product_obj.name_get(
                                cr, uid, [product_id], context=context2)[0][1]
                        if factor.customer_name and data.get('factor_name',
                                                             False):
                            factor_name += ' - ' + factor.customer_name

                        general_account = product.property_account_income or \
                            product.categ_id.property_account_income_categ
                        if not general_account:
                            raise orm.except_orm(
                                _("Configuration Error!"),
                                _("Please define income account for product '%s'.") % product.name)
                        taxes = product.taxes_id or general_account.tax_ids
                        tax = fiscal_pos_obj.map_tax(
                            cr, uid,
                            account.partner_id.property_account_position,
                            taxes)
                        curr_line.update({
                            'invoice_line_tax_id': [(6, 0, tax)],
                            'name': factor_name,
                            'invoice_line_tax_id': [(6, 0, tax)],
                            'account_id': general_account.id,
                        })
                    #
                    # Compute for lines
                    #
                    cr.execute("SELECT * FROM account_analytic_line WHERE account_id = %s and id IN %s AND product_id=%s and to_invoice=%s ORDER BY account_analytic_line.date", (account.id, tuple(ids), product_id, factor_id))

                    line_ids = cr.dictfetchall()
                    note = []
                    for line in line_ids:
                        # set invoice_line_note
                        details = []
                        if data.get('date', False):
                            details.append(line['date'])
                        if data.get('time', False):
                            if line['product_uom_id']:
                                details.append("%s %s" % (
                                    line['unit_amount'],
                                    product_uom_obj.browse(
                                        cr, uid, [line['product_uom_id']],
                                        context2)[0].name))

                            else:
                                details.append("%s" % (line['unit_amount'], ))
                        if data.get('name', False):
                            details.append(line['name'])
                        note.append(u' - '.join(
                            map(lambda x: unicode(x) or '', details)))
                    if note:
                        if curr_line['name']:
                            curr_line['name'] += "\n" + ("\n".join(
                                map(lambda x: unicode(x) or '', note)))
                        else:
                            curr_line['name'] = "\n".join(
                                map(lambda x: unicode(x) or '', note))
                    invoice_line_obj.create(
                        cr, uid, curr_line, context=context)
                    cr.execute("update account_analytic_line set invoice_id=%s WHERE account_id = %s and id IN %s", (last_invoice, account.id, tuple(ids)))

                invoice_obj.button_reset_taxes(
                    cr, uid, [last_invoice], context)
        return invoices

