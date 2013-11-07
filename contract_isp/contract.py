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
import calendar
import datetime
import openerp.addons.decimal_precision as dp
from openerp.osv import orm, fields
from openerp.report import report_sxw
from openerp.tools import convert
from openerp.tools.translate import _


def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def date_interval(start_date, month_end=True, date_format='%m/%d/%Y'):
    if month_end:
        end_date = datetime.date(start_date.year,
                                 start_date.month,
                                 calendar.monthrange(start_date.year,
                                                     start_date.month)[1])
    else:
        end_date = add_months(start_date, 1) - datetime.timedelta(days=1)

    interval = '(%s - %s)' % (start_date.strftime(date_format),
                              end_date.strftime(date_format))

    return interval


class res_company(orm.Model):
    _inherit = 'res.company'

    def _days(self, cr, uid, context=None):
        return tuple([(str(x), str(x)) for x in range(1, 29)])

    _columns = {
        'parent_account_id': fields.many2one('account.analytic.account',
                                             'Parent Analytic Account'),
        'cutoff_day': fields.selection(_days, 'Cutoff day'),
        'default_journal_id': fields.many2one('account.analytic.journal',
                                              'Default Journal')
    }


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'partner_analytic_account_id': fields.many2one('account.analytic.account',
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
        'analytic_line_type': fields.selection((('r', 'Recurrent'),
                                                ('x', 'Exception'),
                                                ('o', 'One time')),
                                               'Type in contract'),
        'require_activation': fields.boolean('Require activation')
    }


class contract_service(orm.Model):
    _name = 'contract.service'

    def _get_product_price(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
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

    def _get_total_product_price(self, cr, uid, ids, field_name, arg, context=None):
        ret = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.qty:
                ret[line.id] = line.unit_price * line.qty
            else:
                ret[line.id] = None

        return ret

    _columns = {
        'activation_date': fields.datetime('Activation date'),
        'duration': fields.integer('Duration'),
        'product_id': fields.many2one('product.product',
                                      'Product',
                                      required=True),
        'qty': fields.float(
            'Qty',
            digits_compute=dp.get_precision('Product Unit of Measure')),
        'category_id': fields.many2one('product.category', 'Product Category'),
        'name': fields.char('Description', size=64),
        'analytic_line_type': fields.selection((('r', 'Recurrent'),
                                                ('x', 'Exception'),
                                                ('o', 'One time')),
                                               'Type'),
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
            if product.analytic_line_type in ('r', 'o'):
                ret['value']['duration'] = 0
            else:
                ret['value']['duration'] = 1

        return ret

    def on_change_qty(self, cr, uid, ids, qty, price):
        ret = {'value': {'price': price}}
        if qty:
            ret['value']['price'] = qty * price

        return ret

    def create_analytic_line(self, cr, uid, ids,
                             mode='manual',
                             date=None,
                             context=None):

        if not date:
            date = datetime.date.today()

        if type(ids) is int:
            ids = [ids]

        ret = []
        record = {}
        next_month = None
        company_obj = self.pool.get('res.company')
        company_id = company_obj._company_default_get(cr, uid, context)
        company = company_obj.browse(cr, uid, company_id, context)

        account_analytic_line_obj = self.pool.get('account.analytic.line')
        for line in self.browse(cr, uid, ids, context):
            account_id = line.account_id.id
            partner_lang = line.account_id.partner_id.lang
            res_lang_obj = self.pool.get('res.lang')
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

            if line.analytic_line_type == 'r':
                if mode == 'prorata':
                    activation_date = date

                    month_days = calendar.monthrange(activation_date.year,
                                                     activation_date.month)[1]

                    used_days = month_days - activation_date.day
                    ptx = (100 * used_days / month_days) / 100.0

                    amount = line.product_id.list_price * ptx
                    interval = date_interval(add_months(date, 1),
                                             True,
                                             date_format)

                elif mode == 'cron':
                    amount = line.product_id.list_price
                    next_month = add_months(date, 1)
                    next_month = datetime.date(
                        next_month.year,
                        next_month.month,
                        1)
                    interval = date_interval(next_month,
                                             False,
                                             date_format)

                elif mode == 'manual':
                    amount = line.product_id.list_price
                    interval = date_interval(date, False, date_format)

                elif mode == 'subscription':
                    amount = line.product_id.list_price
                    interval = ''

            else:
                interval = ''
                amount = line.product_id.list_price

            general_account_id = line.product_id.property_account_expense.id \
                or line.product_id.categ_id.property_account_expense_categ.id

            record = {
                'name': ' '.join([line.product_id.name,
                                  True and line.name or '',
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
                'date': next_month and next_month.strftime('%Y-%m-%d') or date.strftime('%Y-%m-%d'),
                'journal_id': 1
            }

            if line.analytic_line_type == 'x':
                line.write({'duration': line.duration - 1})
                if line.duration <= 0:
                    line.unlink()
                    record['contract_service_id'] = False

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

    def action_desactivate(self, cr, uid, ids, context):
        return self.write(cr, uid, ids,
                          {'state': 'inactive', 'activation_date': None},
                          context)


class account_analytic_account(orm.Model):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

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
    }

    _defaults = {
        'use_contract_services': False
    }

    def create_analytic_lines(self, cr, uid, ids, context=None):
        mode = 'manual'
        if context and context.get('create_analytic_line_mode', False):
            mode = context.get('create_analytic_line_mode')

        account_analytic_line_obj = self.pool.get('account.analytic.line')
        contract_service_obj = self.pool.get('contract.service')
        query = [
            ('account_id', 'in', ids),
            ('state', '=', 'active'),
            ('analytic_line_type', 'in', ('r', 'x'))
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
