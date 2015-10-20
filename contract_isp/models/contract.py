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

# import logging
import calendar
import datetime
import openerp.addons.decimal_precision as dp
# from openerp.report import report_sxw
# from openerp.tools import convert
from openerp.tools.translate import _

from openerp import models, fields, api, _


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


class res_company(models.Model):
    _inherit = "res.company"

    @api.multi
    def _days(self):
        return tuple([(str(x), str(x)) for x in range(1, 29)])

    parent_account_id = fields.Many2one('account.analytic.account', 'Parent Analytic Account')
    cutoff_day = fields.Selection(_days, 'Cutoff day')
    default_journal_id = fields.Many2one('account.analytic.journal',
                                         'Default Journal')


class res_partner(models.Model):
    _inherit = 'res.partner'

    partner_analytic_account_id = fields.Many2one('account.analytic.account',
                                                  'Partner Analytic Account')

    @api.model
    def create(self, vals):
        account_analytic_account = self.env['account.analytic.account']
        company_obj = self.env['res.company']
        company_id = company_obj._company_default_get()
        company = company_obj.browse(company_id)
        ret = super(res_partner, self).create(vals)
        parent_id = company.parent_account_id and company.parent_account_id.id
        account = {
            'name': vals['name'],
            'parent_id': parent_id,
            'type': 'view',
            'partner_id': ret.id,
            'user_id': self._uid
        }
        account_id = account_analytic_account.create(account)
        ret.write({'partner_analytic_account_id': account_id.id})

        return ret


class product_product(models.Model):
    _inherit = 'product.product'

    analytic_line_type = fields.Selection((('r', 'Recurrent'),
                                           ('x', 'Exception'),
                                           ('o', 'One time')),
                                          'Type in contract')
    require_activation = fields.Boolean(string='Require activation')


class contract_service(models.Model):
    _name = 'contract.service'

    @api.depends('price', 'unit_price')
    def _get_product_price(self):
        product_obj = self.env['product.product']
        product_pricelist_obj = self.env['product.pricelist']
        partner_id = self.account_id.partner_id.id
        pricelist_id = self.account_id.partner_id.property_product_pricelist
        for line in self:
            if line.product_id and partner_id:
                self.price = pricelist_id.price_get(line.product_id.id, 1,
                                                    partner_id)\
                                                    [pricelist_id.id]
            else:
                self.price = None

    @api.depends('unit_price', 'qty')
    def _get_total_product_price(self):
        ret = {}
        for record in self:
            ret[record.id] = record.unit_price * record.qty
        return ret

    activation_date = fields.Datetime('Activation date')
    duration = fields.Integer('Duration')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    qty = fields.Float('Qty', digits_compute=dp.get_precision
                       ('Product Unit of Measure'), default=1)
    category_id = fields.Many2one('product.category', 'Product Category',
                                  default=1)
    name = fields.Char('Description', size=64)
    analytic_line_type = fields.Selection((('r', 'Recurrent'),
                                           ('x', 'Exception'),
                                           ('o', 'One time')),
                                          'Type')
    require_activation = fields.Boolean('Require activation')
    account_id = fields.Many2one('account.analytic.account', 'Contract')

    unit_price = fields.Float(compute='_get_product_price',
                              digits_compute=dp.get_precision('Product Price'),
                              string='Unit Price')
    price = fields.Float(compute='_get_total_product_price', type='float',
                         digits_compute=dp.get_precision('Product Price'),
                         string='Price')
    activation_line_generated = fields.Boolean('Activation Line Generated?',
                                               default=False)
    state = fields.Selection((('draft', 'Waiting for activating'),
                              ('active', 'Active'),
                              ('inactive', 'Inactive')),
                             'State', default='draft')
    _defaults = {
                 # 'name': '',from .
                 }

    @api.onchange('product_id')
    def on_change_product_id(self):
        product = self.env['product.product'].browse(self.product_id)
        if self.product_id:
            self.analytic_line_type = product.analytic_line_type
            self.require_activation = product.require_activation
            self.category_id = product.categ_id.id
            self.unit_price = product.list_price
            if product.analytic_line_type in ('r', 'o'):
                self.duration = 0
            else:
                self.duration = 1

    @api.onchange('qty', 'price')
    def on_change_qty(self):
        if self.qty:
            self.price = self.qty * self.price

    @api.multi
    def create_analytic_line(self, mode='manual', date=None):

        if not date:
            date = datetime.date.today()

        if type(self.ids) is int:
            ids = [self.ids]
        context = dict(self._context)
        ret = []
        record = {}
        next_month = None
        company_obj = self.env['res.company']
        company_id = company_obj._company_default_get()
        company = company_obj.browse(company_id)

        account_analytic_line_obj = self.env['account.analytic.line']
        for line in self:
            account_id = line.account_id.id
            partner_lang = line.account_id.partner_id.lang
            res_lang_obj = self.env['res.lang']
            query = [
                ('code', '=', partner_lang),
                ('active', '=', True)
                ]
            lang_id = res_lang_obj.search(query)
            if lang_id:
                date_format = res_lang_obj.browse(lang_id.id).date_format
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
                'user_id': self._uid,
                'general_account_id': general_account_id,
                'product_id': line.product_id.id,
                'contract_service_id': line.id,
                'to_invoice': 1,
                'unit_amount': line.qty,
                'is_prorata': mode == 'prorata',
                'date': next_month and next_month.strftime('%Y-%m-%d') or
                date.strftime('%Y-%m-%d'),
                'journal_id': 1
            }

            if line.analytic_line_type == 'x':
                line.write({'duration': line.duration - 1})
                if line.duration <= 0:
                    line.unlink()
                    record['contract_service_id'] = False

            if 'default_type' in context:
                context.pop('default_type')

            ret.append(account_analytic_line_obj.create(record).id)
        return ret

    @api.model
    def create(self, values):
        if not values["require_activation"]:
            values["state"] = 'active'
            values["activation_date"] = fields.datetime.now()
        return super(contract_service, self).create(values)

    @api.multi
    def action_desactivate(self):
        return self.write({'state': 'inactive', 'activation_date': None})


class account_analytic_account(models.Model):
    _inherit = "account.analytic.account"

    contract_service_ids = fields.One2many('contract.service',
                                           'account_id',
                                           'Services')
    use_contract_services = fields.Boolean('Contract services', default=False)
    state = fields.Selection([('template', 'Template'),
                              ('draft', 'New'),
                              ('open', 'In Progress'),
                              ('pending', 'Suspended'),
                              ('close', 'Closed'),
                              ('cancelled', 'Cancelled')],
                             'Status', required=True,
                             track_visibility='onchange')

    @api.v7
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

    @api.v7
    def create_analytic_lines(self, cr, uid, ids, context=None):
        mode = 'manual'
        if context and context.get('create_analytic_line_mode', False):
            mode = context.get('create_analytic_line_mode')

        contract_service_obj = self.pool.get('contract.service')
        query = [
            ('account_id', 'in', ids),
            ('state', '=', 'active'),
        ]
        contract_service_ids = contract_service_obj.search(cr, uid,
                                                           [],
                                                           order='account_id',
                                                           context=context)
        if contract_service_ids:
            contract_service_obj.create_analytic_line(cr, uid,
                                                      contract_service_ids,
                                                      mode=mode,
                                                      context=context)

        return {}

    @api.model
    def create(self, values):
        if values['type'] == 'contract' and values['use_contract_services']:
            values['name'] = values['code']
            partner_obj = self.env['res.partner']
            values['parent_id'] = partner_obj.read(values['partner_id'],
                                                   fields=
                                                   ['partner_analytic_'
                                                    'account_id'])
            ['partner_analytic_account_id'][0]
        return super(account_analytic_account, self).create(values)


class account_analytic_line(models.Model):
    _inherit = "account.analytic.line"

    contract_service_id = fields.Many2one('contract.service', 'Service')
    is_prorata = fields.Boolean('Prorata', defaults=False)
