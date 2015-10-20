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

# import time
# import datetime
# from openerp.addons.contract_isp.models.contract import add_months
from openerp import models, api


class contract_service_activate(models.TransientModel):
    _inherit = 'contract.service.activate'

    @api.multi
    def activate(self):
        if self._context is None:
            context = {}
        account_invoice_obj = self.env['account.invoice']
        account_voucher_obj = self.env['account.voucher']
        account_move_obj = self.env['account.move']
        res_company_obj = self.env['res.company']

        ret = super(contract_service_activate, self).activate()

        contract_service_obj = self.env['contract.service']
        account_analytic_account_obj = self.env['account.analytic.account']
        account_move_line_obj = self.env['account.move.line']

        query = [
            ('account_id', '=', self.account_id.id),
            ('state', '=', 'draft')
        ]
        # Check if all services were activated
        if not contract_service_obj.search(query):

            # jgama - Try to create the prorata invoice
            pro_inv = account_analytic_account_obj.create_invoice(prorata=True)

        return ret
