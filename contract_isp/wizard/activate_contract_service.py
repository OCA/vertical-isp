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

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp.osv import orm, fields

from ..contract import LINE_TYPE_RECURRENT


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


class contract_service_activate(orm.TransientModel):
    _name = 'contract.service.activate'
    _get_account_id = _get_account_id
    _get_service_id = _get_service_id

    _columns = {
        'activation_date': fields.datetime('Activation Date'),
        'account_id': fields.many2one('account.analytic.account', 'Account'),
        'service_id': fields.many2one('contract.service', 'Service')
    }

    _defaults = {
        'activation_date': fields.datetime.now,
        'account_id': _get_account_id,
        'service_id': _get_service_id,
    }

    def activate(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        contract_service_obj = self.pool.get('contract.service')
        contract_service = contract_service_obj.browse(
            cr, uid, wizard.service_id.id, context)

        contract_service.write({
            'activation_date': wizard.activation_date,
            'state': 'active'
        })

        self._create_analytic_lines(cr, uid, ids[0], context)

        return True

    def _create_analytic_lines(self, cr, uid, wiz_id, context=None):
        wizard = self.browse(cr, uid, wiz_id, context)
        contract_service_obj = self.pool.get('contract.service')
        contract_service = contract_service_obj.browse(
            cr, uid, wizard.service_id.id, context)

        activation_date = datetime.date(
            int(wizard.activation_date[:4]),
            int(wizard.activation_date[5:7]),
            int(wizard.activation_date[8:10]))

        # When registering an initial payment, we generate activation lines
        # we do not wish to generate another month entry if not needed
        # vvinet: This is not currently part of our scenarios, remove it
        #         it can be put back if we want to handle it
        # if contract_service.activation_line_generated is False:
        #     contract_service.create_analytic_line(mode='manual',
        #                                           date=activation_date,
        #                                           context=context)
        #     contract_service.write({'activation_line_generated': True})

        # Upon activating, always create activation lines
        if contract_service.analytic_line_type == LINE_TYPE_RECURRENT:
            contract_service.create_analytic_line(mode='prorata',
                                                  date=activation_date,
                                                  context=context)

    def _check_future_date(self, cr, uid, ids, context=None):
        today = datetime.datetime.utcnow().date()
        for wiz in self.browse(cr, uid, ids, context=None):
            act_date = datetime.datetime.strptime(
                wiz.activation_date, DEFAULT_SERVER_DATETIME_FORMAT,
            ).date()

            if act_date > today:
                return False
        return True

    _constraints = [
        (_check_future_date,
         _('You cannot activate a service in the future.'),
         ['activation_date']),
    ]


class contract_service_deactivate(orm.TransientModel):
    _name = 'contract.service.deactivate'

    _columns = {
        'deactivation_date': fields.datetime('Deactivation Date'),
        'account_id': fields.many2one('account.analytic.account', 'Account'),
        'service_id': fields.many2one('contract.service', 'Service')
    }

    _defaults = {
        'deactivation_date': fields.datetime.now,
        'account_id': _get_account_id,
        'service_id': _get_service_id,
    }

    def deactivate(self, cr, uid, ids, context=None):
        context = context or {}
        wizard = self.browse(cr, uid, ids[0], context)
        contract_service_obj = self.pool.get('contract.service')
        context["deactivation_date"] = wizard.deactivation_date
        contract_service_obj.action_deactivate(cr, uid,
                                               [wizard.service_id.id],
                                               context=context)
        # If we activate again, we will need a new activation line, as
        # we will have refunded any extra, and will need to bill in
        # advance again.
        contract_service_obj.write(cr, uid, [wizard.service_id.id], {
            'activation_line_generated': False,
        })

        self._create_refund_lines(cr, uid, ids[0], context)
        return True

    def _create_refund_lines(self, cr, uid, wiz_id, context=None):
        wizard = self.browse(cr, uid, wiz_id, context)
        contract_service_obj = self.pool.get('contract.service')

        deactivate_date = datetime.datetime.strptime(
            wizard.deactivation_date,
            DEFAULT_SERVER_DATETIME_FORMAT,
        ).date()

        contract_service_obj.create_refund_line(
            cr, uid,
            [wizard.service_id.id],
            mode='prorata',
            date=deactivate_date,
            context=context)

    def _check_future_date(self, cr, uid, ids, context=None):
        today = datetime.datetime.utcnow().date()
        for wiz in self.browse(cr, uid, ids, context=None):
            act_date = datetime.datetime.strptime(
                wiz.deactivation_date, DEFAULT_SERVER_DATETIME_FORMAT,
            ).date()

            if act_date > today:
                return False
        return True

    _constraints = [
        (_check_future_date,
         _('You cannot deactivate a service in the future.'),
         ['deactivation_date']),
    ]
