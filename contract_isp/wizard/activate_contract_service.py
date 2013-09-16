# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoir-faire Linux (<www.savoirfairelinux.com>).
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

import datetime
from openerp.osv import orm, fields
from openerp.addons.contract_isp.contract import add_months


class contract_service_activate(orm.TransientModel):
    _name = 'contract.service.activate'

    def _get_account_id(self, cr, uid, context=None):
        if context.get('active_model', '') == 'contract.service':
            contract_id = context.get('active_id')
            contract_service = self.pool.get('contract.service').browse(
                cr, uid, contract_id, context)

            return contract_service.account_id.id
        return None

    def _get_service_id(self, cr, uid, context=None):
        if context.get('active_model', '') == 'contract.service':
            service_id = context.get('active_id')
            contract_service = self.pool.get('contract.service').browse(
                cr, uid, service_id, context)

            return contract_service.id
        return None

    _columns = {
        'activation_date': fields.datetime('Activation Date'),
        'account_id': fields.many2one('account.analytic.account', 'Account'),
        'service_id': fields.many2one('contract.service', 'Service')
    }

    _defaults = {
        'activation_date': fields.datetime.now,
        'account_id': lambda s, cr, uid, ctx: s._get_account_id(cr, uid, ctx),
        'service_id': lambda s, cr, uid, ctx: s._get_service_id(cr, uid, ctx)
    }

    def activate(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        company_obj = self.pool.get('res.company')
        company_id = company_obj._company_default_get(cr, uid, context)
        cutoff = company_obj.read(cr, uid, company_id, 'cutoff_day', context)
        contract_service_obj = self.pool.get('contract.service')
        contract_service = contract_service_obj.browse(
            cr, uid, wizard.service_id.id, context)

        activation_date = datetime.date(
            int(wizard.activation_date[:4]),
            int(wizard.activation_date[5:7]),
            int(wizard.activation_date[8:10]))

        cuttoff_day = company_obj.read(
            cr, uid,
            company_id,
            fields=['cutoff_day'],
            context=context)['cutoff_day']

        invoice_day = company_obj.read(
            cr, uid,
            company_id,
            fields=['invoice_day'],
            context=context)['invoice_day']

        cutoff_date = datetime.date(
            datetime.date.today().year,
            datetime.date.today().month,
            int(cuttoff_day))

        invoice_date = datetime.date(
            datetime.date.today().year,
            datetime.date.today().month,
            int(invoice_day))

        contract_service.write({
            'activation_date': wizard.activation_date,
            'state': 'active'
        })

        query = [
            ('account_id', '=', wizard.account_id.id),
            ('state', '=', 'draft')
        ]
        draft_line_ids = contract_service_obj.search(cr, uid, query,
                                                     context=context)

        if not draft_line_ids:
            for line in wizard.account_id.contract_service_ids:
                if line.activation_line_generated is False:
                    line.create_analytic_line(mode='manual',
                                              date=activation_date)

                    if line.analytic_line_type == 'r':
                        line.create_analytic_line(mode='prorata',
                                                  date=activation_date)

        return True
