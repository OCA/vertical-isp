# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Savoirfaire-Linux Inc. (<www.savoirfairelinux.com>).
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

from openerp.osv import fields, orm


class AccountAnalyticAccount(orm.Model):
    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'

    def _get_ui_flags(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = cur = {
                'ui_reserve': False,
                'ui_return': False,
            }
            for service in account.contract_service_ids:
                if not service.product_id.type == "product":
                    continue
                if service.prodlot_id:
                    cur['ui_return'] = True
                else:
                    cur['ui_reserve'] = True

        return res

    _columns = {
        'prodlot_id': fields.many2one(
            'stock.production.lot',
            'Serial Number',
            required=False,
        ),
        'ui_reserve': fields.function(
            _get_ui_flags,
            type='boolean', method=True, multi='ui_flags',
        ),
        'ui_return': fields.function(
            _get_ui_flags,
            type='boolean', method=True, multi='ui_flags',
        ),
    }
