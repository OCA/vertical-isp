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

import logging
import time
import datetime
from openerp.osv import orm, fields
from openerp.addons.contract_isp.contract import add_months, date_interval

_logger = logging.getLogger(__name__)


class res_company(orm.Model):
    _inherit = "res.company"

    def _days(self, cr, uid, context=None):
        return tuple([(str(x), str(x)) for x in range(1, 29)])

    _columns = {
        'invoice_day': fields.selection(_days, 'Invoice day'),
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

        account_analytic_line = self.pool.get('account.analytic.line')
        contract_service_obj = self.pool.get('contract.service')
        res_company_obj = self.pool.get('res.company')
        account_invoice_obj = self.pool.get('account.invoice')

        cuttoff_day = res_company_obj.read(
            cr, uid,
            res_company_obj._company_default_get(cr, uid, context),
            fields=['cutoff_day'],
            context=context)['cutoff_day']

        cutoff_date = datetime.date(
            datetime.date.today().year,
            datetime.date.today().month,
            int(cuttoff_day)
        )

        invoice_day = res_company_obj.read(
            cr, uid,
            res_company_obj._company_default_get(cr, uid, context),
            fields=['invoice_day'],
            context=context)['invoice_day']

        invoice_date = datetime.date(
            datetime.date.today().year,
            datetime.date.today().month,
            int(invoice_day)
        )

        ret = []
        for contract_id in ids:
            #if context.get('create_line_before_invoice', False):
            #    contract_service_obj.
            query = [('account_id', '=', contract_id),
                     ('to_invoice', '!=', None),
                     ('invoice_id', '=', None),
                     ('product_id', '!=', None),
                     ('is_prorata', '=', prorata)]

            ids_to_invoice = account_analytic_line.search(cr, uid, query,
                                                          context=context)
            if ids_to_invoice:
                data = {
                    'name': True,
                }
                inv = account_analytic_line.invoice_cost_create(
                    cr, uid, ids_to_invoice, data=data, context=context)

                # jgama - If its a prorata invoice, change the invoice date
                #         according to the invoice_day variable
                if prorata:
                    if datetime.date.today() <= cutoff_date:
                        date_invoice = invoice_date.strftime('%Y-%m-%d')
                    else:
                        date_invoice = add_months(invoice_date, 1).strftime(
                            '%Y-%m-%d')

                    account_invoice_obj.write(
                        cr, uid, inv, {'date_invoice': date_invoice},
                        context=context)

                a = account_invoice_obj._workflow_signal(
                    cr, uid, inv, 'invoice_open', context)
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
                        ret.append(i)
                else:
                    mail_id = mail_template_obj.send_mail(
                        cr, uid, mail_template_id, inv, context=context)
                    mail_message = mail_mail_obj.browse(
                        cr, uid, mail_id, context=context).mail_message_id
                    mail_message.write({'type': 'email'})
                    ret.append(inv)

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
                partner = account.partner_id
                if (not partner) or not (account.pricelist_id):
                    raise osv.except_osv(
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
                    'partner_id': account.partner_id.id,
                    'company_id': account.company_id.id,
                    'payment_term': partner.property_payment_term.id or False,
                    'account_id': partner.property_account_receivable.id,
                    'currency_id': account.pricelist_id.currency_id.id,
                    'date_due': date_due,
                    'fiscal_position': account.partner_id.property_account_position.id
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
                        unit_price = total_price * -1.0 / qty

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
                            raise osv.except_osv(
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
