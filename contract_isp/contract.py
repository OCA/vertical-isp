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
_logger = logging.getLogger(__name__)
import calendar
import datetime

import openerp.addons.decimal_precision as dp
from openerp.osv import orm, fields
from openerp.tools import SUPERUSER_ID, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

LINE_TYPE_EXCEPTION = 'x'
LINE_TYPE_RECURRENT = 'r'
LINE_TYPE_ONETIME = 'o'


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def date_interval(start_date, month_end=True):
    if month_end:
        end_date = datetime.date(start_date.year,
                                 start_date.month,
                                 calendar.monthrange(start_date.year,
                                                     start_date.month)[1])
    else:
        end_date = add_months(start_date, 1) - datetime.timedelta(days=1)

    return start_date, end_date


def format_interval(start, end, date_format=DEFAULT_SERVER_DATE_FORMAT):
    return '(%s - %s)' % (start.strftime(date_format),
                          end.strftime(date_format))


def operation_date(date=None, context=None):
    if context is None:
        context = {}

    if date is None:
        date = context.get("operation_date", datetime.date.today())
        if not isinstance(date, datetime.date):
            date = datetime.datetime.strptime(
                date,
                DEFAULT_SERVER_DATE_FORMAT,
            ).date()

    return date


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'partner_analytic_account_id': fields.many2one(
            'account.analytic.account',
            'Partner Analytic Account')
    }

    def create(self, cr, uid, values, context=None):
        account_analytic_account = self.pool.get('account.analytic.account')
        company_obj = self.pool.get('res.company')
        company_id = company_obj._company_default_get(cr, uid, context)
        company = company_obj.browse(cr, uid, company_id, context)

        ret = super(res_partner, self).create(cr, uid, values, context)

        parent_id = company.parent_account_id and company.parent_account_id.id
        account = {
            'name': values['name'],
            'parent_id': parent_id,
            'type': 'view',
            'partner_id': ret,
            'user_id': uid
        }

        account_id = account_analytic_account.create(cr, uid, account, context)
        self.write(cr, uid, ret,
                   {'partner_analytic_account_id': account_id},
                   context)

        return ret


class product_product(orm.Model):
    _inherit = 'product.product'

    _columns = {
        'analytic_line_type': fields.selection(
            ((LINE_TYPE_RECURRENT, 'Recurrent'),
             (LINE_TYPE_EXCEPTION, 'Exception'),
             (LINE_TYPE_ONETIME, 'One time')),
            'Type in contract',
            required=True),
        'require_activation': fields.boolean('Require activation')
    }


class contract_service(orm.Model):
    _name = 'contract.service'

    def _get_product_price(self, cr, uid, ids, field_name, arg, context=None):
        product_pricelist_obj = self.pool.get('product.pricelist')
        partner_id = self.browse(
            cr, uid, ids[0],
            context=context).account_id.partner_id.id
        pricelist_id = self.browse(
            cr, uid, ids[0],
            context=context
        ).account_id.partner_id.property_product_pricelist.id
        ret = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id:
                ret[line.id] = product_pricelist_obj.price_get(
                    cr, uid, [pricelist_id],
                    line.product_id.id, 1, partner_id,
                    context=context)[pricelist_id]
            else:
                ret[line.id] = None

        return ret

    def _get_total_product_price(self, cr, uid, ids, field_name, arg,
                                 context=None):
        ret = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.qty:
                ret[line.id] = line.unit_price * line.qty
            else:
                ret[line.id] = None

        return ret

    _columns = {
        'activation_date': fields.datetime('Activation date'),
        'billed_to_date': fields.date('Billed until date'),
        'deactivation_date': fields.datetime('Deactivation date'),
        'duration': fields.integer('Duration'),
        'product_id': fields.many2one('product.product',
                                      'Product',
                                      required=True),
        'qty': fields.float(
            'Qty',
            digits_compute=dp.get_precision('Product Unit of Measure')),
        'category_id': fields.many2one('product.category', 'Product Category'),
        'name': fields.char('Description', size=64),
        'analytic_line_type': fields.selection(
            ((LINE_TYPE_RECURRENT, 'Recurrent'),
             (LINE_TYPE_EXCEPTION, 'Exception'),
             (LINE_TYPE_ONETIME, 'One time')),
            'Type'),
        # XXX Should this be a function based on product.product?
        'require_activation': fields.boolean('Require activation'),
        'account_id': fields.many2one('account.analytic.account', 'Contract'),
        'unit_price': fields.function(
            _get_product_price, type='float',
            digits_compute=dp.get_precision('Product Price'),
            string='Unit Price'),
        'price': fields.function(
            _get_total_product_price, type='float',
            digits_compute=dp.get_precision('Product Price'),
            string='Price'),
        'activation_line_generated': fields.boolean(
            'Activation Line Generated?'),
        'state': fields.selection((('draft', 'Waiting for activating'),
                                   ('active', 'Active'),
                                   ('inactive', 'Inactive')),
                                  'State')
    }

    _defaults = {
        'state': 'draft',
        'activation_line_generated': False,
        'category_id': 1,
        'name': '',
        'qty': 1
    }

    def on_change_product_id(self, cr, uid, ids, product_id):
        ret = {'value': {'analytic_line_type': None}}
        product = self.pool.get('product.product').browse(
            cr, uid,
            [product_id],
            None)[0]

        if product_id:
            ret['value']['analytic_line_type'] = product.analytic_line_type
            ret['value']['require_activation'] = product.require_activation
            ret['value']['category_id'] = product.categ_id.id
            ret['value']['unit_price'] = product.list_price
            if product.analytic_line_type == LINE_TYPE_RECURRENT:
                ret['value']['duration'] = 0
            else:
                ret['value']['duration'] = 1

        return ret

    def on_change_qty(self, cr, uid, ids, qty, price):
        ret = {'value': {'price': price}}
        if qty:
            ret['value']['price'] = qty * price

        return ret

    def _prorata_rate(self, days_used, days_in_month):
        """ Returns a rate to compute prorata invoices.
        Current method is days_used / days_in_month, rounded DOWN
        to 2 digits
        """
        return (100 * days_used / days_in_month) / 100.0

    def _get_prorata_interval_rate(self, cr, uid, change_date, context=None):
        """ Get the prorata interval and price rate.

        Returns a tuple (start_date, end_date, price percent)
        """
        month_days = calendar.monthrange(change_date.year,
                                         change_date.month)[1]
        start_date = add_months(change_date, 1)
        end_date = start_date.replace(day=month_days)
        used_days = month_days - change_date.day
        ptx = self._prorata_rate(used_days, month_days)

        return start_date, end_date, ptx

    def _get_prorata_interval_rate_deactivate(self, cr, uid, change_date,
                                              context=None):
        start_date, end_date, ptx = self._get_prorata_interval_rate(
            cr, uid, change_date, context=context)
        ptx = ptx * -1
        return start_date, end_date, ptx

    def _get_date_format(self, cr, uid, obj, context):
        partner_lang = obj.account_id.partner_id.lang
        res_lang_obj = self.pool['res.lang']
        query = [
            ('code', '=', partner_lang),
            ('active', '=', True)
        ]
        lang_id = res_lang_obj.search(cr, uid, query, context=context)
        if lang_id:
            date_format = res_lang_obj.browse(cr, uid,
                                              lang_id[0],
                                              context=context).date_format

        else:
            date_format = '%Y/%m/%d'
        return date_format

    def create_analytic_line(self, cr, uid, ids,
                             mode='manual',
                             date=None,
                             context=None):
        date = operation_date(date, context)

        if type(ids) is int:
            ids = [ids]

        ret = []
        record = {}
        account_analytic_line_obj = self.pool.get('account.analytic.line')
        for line in self.browse(cr, uid, ids, context):
            date_format = self._get_date_format(cr, uid, line, context=context)
            start, end = None, None
            next_month = None

            amount = line.price

            if line.analytic_line_type == LINE_TYPE_RECURRENT:
                if mode == 'prorata':
                    activation_date = date
                    start, end, ptx = self._get_prorata_interval_rate(
                        cr, uid,
                        activation_date,
                        context=context,
                    )

                    amount = amount * ptx

                elif mode == 'cron':
                    next_month = add_months(date, 1)
                    next_month = datetime.date(
                        next_month.year,
                        next_month.month,
                        1)
                    start, end = date_interval(next_month, False)

                elif mode == 'manual':
                    start, end = date_interval(date, False)

                elif mode == 'subscription':
                    line.write({'activation_line_generated': True})

            if start and end:
                interval = format_interval(start, end, date_format)
            else:
                interval = ''

            general_account_id = line.product_id.property_account_expense.id \
                or line.product_id.categ_id.property_account_expense_categ.id

            record = {
                'name': ' '.join([line.product_id.name,
                                  line.name or '',
                                  interval]),
                'amount': (amount * -1),
                'account_id': line.account_id.id,
                'user_id': uid,
                'general_account_id': general_account_id,
                'product_id': line.product_id.id,
                'contract_service_id': line.id,
                'to_invoice': 1,
                'unit_amount': line.qty,
                'is_prorata': mode == 'prorata',
                'date': (next_month or date).strftime('%Y-%m-%d'),
                'journal_id': 1
            }

            if line.analytic_line_type == LINE_TYPE_EXCEPTION:
                new_duration = line.duration - 1
                line.write({'duration': new_duration})
                if new_duration <= 0:
                    self.unlink(cr, SUPERUSER_ID, line.id)
                    record['contract_service_id'] = False
            elif line.analytic_line_type == LINE_TYPE_ONETIME:
                if line.duration > 0:
                    line.write({'duration': line.duration - 1})
                else:
                    # Do not create an already billed line
                    continue

            if 'default_type' in context:
                context.pop('default_type')

            ret.append(account_analytic_line_obj.create(cr, uid, record,
                                                        context))

        return ret

    def create_refund_line(self, cr, uid, ids,
                           mode='manual',
                           date=None,
                           context=None):
        context = context or {}
        date = operation_date(date, context)

        if type(ids) is int:
            ids = [ids]

        ret = []
        record = {}
        account_analytic_line_obj = self.pool.get('account.analytic.line')
        for line in self.browse(cr, uid, ids, context):
            if any((line.analytic_line_type != LINE_TYPE_RECURRENT,
                    mode != "prorata")):
                # Not handled for now, only pro-rata deactivate
                continue

            date_format = self._get_date_format(cr, uid, line, context=context)

            deactivation_date = date
            start, end, ptx = self._get_prorata_interval_rate_deactivate(
                cr, uid,
                deactivation_date,
                context=context,
            )

            amount = line.product_id.list_price * ptx

            interval = format_interval(start, end,
                                       date_format=date_format)

            general_account_id = (
                line.product_id.property_account_expense.id or
                line.product_id.categ_id.property_account_expense_categ.id
            )

            record = {
                'name': ' '.join([line.product_id.name,
                                  line.name or '',
                                  interval]),
                'amount': (amount * -1) * line.qty,
                'account_id': line.account_id.id,
                'user_id': uid,
                'general_account_id': general_account_id,
                'product_id': line.product_id.id,
                'contract_service_id': line.id,
                'to_invoice': 1,
                'unit_amount': line.qty,
                'is_prorata': mode == 'prorata',
                'date': date.strftime('%Y-%m-%d'),
                'journal_id': 1
            }

            if 'default_type' in context:
                context.pop('default_type')

            ret.append(account_analytic_line_obj.create(cr, uid, record,
                                                        context))
        return ret

    def create(self, cr, uid, values, context=None):
        if not values["require_activation"]:
            values["state"] = 'active'
            values["activation_date"] = fields.datetime.now()
        ret = super(contract_service, self).create(cr, uid, values, context)

        return ret

    def action_deactivate(self, cr, uid, ids, context):
        values = {'state': 'inactive'}
        if "deactivation_date" in context:
            values["deactivation_date"] = context["deactivation_date"]
        else:
            values["deactivation_date"] = fields.datetime.now()

        self.write(cr, uid, ids, values, context)

        return True


class account_analytic_account(orm.Model):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

    def _get_invoice_ids(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if ids:
            cr.execute("""
                SELECT account_analytic_id, array_agg(invoice_id)
                FROM account_invoice_line
                WHERE account_analytic_id IN %s
                GROUP BY account_analytic_id
                """, (tuple(ids), ))
            values = dict(cr.fetchall())

            for i in ids:
                res[i] = values.get(i, [])

        return res

    def _search_invoice_ids(self, cr, uid, obj, name, args, context):
        query, params = [], []
        for key, op, value in args:
            if key != "invoice_ids":
                continue
            if op in ("=", "in") and not value:
                query.append("agg.invoice_ids = ARRAY[NULL]::integer[]")
            elif op in ("!=", "not in") and not value:
                query.append("NOT agg.invoice_ids = ARRAY[NULL]::integer[]")
            elif op in ("=", "in", "!=", "not in") and value:
                if isinstance(value, (int, long)):
                    value = [value]
                query.append("{0} agg.invoice_ids && ARRAY[{1}]".format(
                    "NOT" if op in ("!=", "not in") else "",
                    ", ".join(["%s"] * len(value)),
                ))
                params.extend(value)
            else:
                continue

        if not query:
            return []

        else:
            cr.execute(
                """
                SELECT array_agg(agg.id) FROM (
                    SELECT aaa.id as id
                         , array_agg(ail.invoice_id) as invoice_ids
                    FROM account_analytic_account aaa
                    LEFT JOIN account_invoice_line ail ON ail.account_analytic_id = aaa.id
                    GROUP BY aaa.id
                    ) agg
                WHERE {0}""".format(" AND ".join(query)),
                params,
            )

            ids = cr.fetchone()[0]
            return [('id', 'in', tuple(ids))]

    _columns = {
        'contract_service_ids': fields.one2many('contract.service',
                                                'account_id',
                                                'Services'),
        'use_contract_services': fields.boolean('Contract services'),
        'state': fields.selection([('template', 'Template'),
                                   ('draft', 'New'),
                                   ('open', 'In Progress'),
                                   ('pending', 'Suspended'),
                                   ('close', 'Closed'),
                                   ('cancelled', 'Cancelled')],
                                  'Status', required=True,
                                  track_visibility='onchange'),
        'invoice_ids': fields.function(
            _get_invoice_ids,
            fnct_search=_search_invoice_ids,
            string="Invoices",
            type="one2many", obj="account.invoice",
            store=False, method=True,
        ),
    }

    _defaults = {
        'use_contract_services': False
    }

    def create_analytic_lines(self, cr, uid, ids, context=None):
        mode = 'manual'
        if context and context.get('create_analytic_line_mode', False):
            mode = context.get('create_analytic_line_mode')

        contract_service_obj = self.pool.get('contract.service')
        query = [
            ('account_id', 'in', ids),
            ('state', '=', 'active'),
            ('analytic_line_type', 'in', (LINE_TYPE_RECURRENT,
                                          LINE_TYPE_ONETIME,
                                          LINE_TYPE_EXCEPTION))
        ]
        contract_service_ids = contract_service_obj.search(cr, uid,
                                                           query,
                                                           order='account_id',
                                                           context=context)

        if contract_service_ids:
            contract_service_obj.create_analytic_line(cr, uid,
                                                      contract_service_ids,
                                                      mode=mode,
                                                      context=context)

        return {}

    def create_refund_lines(self, cr, uid, ids, context=None):
        context = context or {}
        mode = context.get('create_analytic_line_mode', 'manual')

        contract_service_obj = self.pool["contract.service"]
        query = [
            ('account_id', 'in', ids),
            ('state', '=', 'inactive'),
            # only recurrent is handled in refund right now
            ('analytic_line_type', 'in', (LINE_TYPE_RECURRENT,)),
        ]
        contract_service_ids = contract_service_obj.search(cr, uid,
                                                           query,
                                                           order='account_id',
                                                           context=context)

        if contract_service_ids:
            contract_service_obj.create_refund_line(cr, uid,
                                                    contract_service_ids,
                                                    mode=mode,
                                                    context=context)

        return {}

    def create(self, cr, uid, values, context=None):
        if values['type'] == 'contract' and values['use_contract_services']:
            values['name'] = values['code']
            partner_obj = self.pool.get('res.partner')
            values['parent_id'] = partner_obj.read(
                cr, uid, values['partner_id'],
                fields=['partner_analytic_account_id'],
                context=context)['partner_analytic_account_id'][0]

        ret = super(account_analytic_account, self).create(cr, uid, values,
                                                           context)

        return ret

    def on_change_partner_id(self, cr, uid, ids,
                             partner_id, name,
                             code=None, context=None):
        res = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id,
                                                          context=context)
            if partner.user_id:
                res['manager_id'] = partner.user_id.id
            if not name:
                if code:
                    res['name'] = code
                else:
                    res['name'] = _('Contract: ') + partner.name
            # Use pricelist from customer
            res['pricelist_id'] = partner.property_product_pricelist.id

        return {'value': res}


class account_analytic_line(orm.Model):
    _name = "account.analytic.line"
    _inherit = "account.analytic.line"

    _columns = {
        'contract_service_id': fields.many2one('contract.service',
                                               'Service'),
        'is_prorata': fields.boolean('Prorata')
    }

    _defaults = {
        'is_prorata': False
    }
