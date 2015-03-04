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

import time
import datetime
from openerp.osv import orm, fields
from openerp.addons.contract_isp.contract import add_months


class contract_service_activate(orm.TransientModel):
    _inherit = 'contract.service.activate'

    def activate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        account_invoice_obj = self.pool.get('account.invoice')
        account_voucher_obj = self.pool.get('account.voucher')
        account_move_obj = self.pool.get('account.move')
        res_company_obj = self.pool.get('res.company')
        wizard = self.browse(cr, uid, ids[0], context)

        ret = super(contract_service_activate, self).activate(cr, uid,
                                                              ids,
                                                              context=context)

        contract_service_obj = self.pool.get('contract.service')
        account_analytic_account_obj = self.pool.get('account.analytic.account')
        account_move_line_obj = self.pool.get('account.move.line')

        query = [
            ('account_id', '=', wizard.account_id.id),
            ('state', '=', 'draft')
        ]
        # Check if all services were activated
        if not contract_service_obj.search(cr, uid, query, context=context):

            # jgama - Try to create the prorata invoice
            pro_inv = account_analytic_account_obj.create_invoice(
                cr, uid, wizard.account_id.id, prorata=True, context=context)

        return ret
