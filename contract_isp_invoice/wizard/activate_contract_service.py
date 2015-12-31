# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoirfaire-Linux Inc. (<www.savoirfairelinux.com>).
#    Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>)

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

from openerp import models, api


class contract_service_activate(models.TransientModel):
    _inherit = 'contract.service.activate'

    @api.multi
    def activate(self):
        ret = super(contract_service_activate, self).activate()
        contract_service_obj = self.env['contract.service']

        query = [
            ('account_id', '=', self.account_id.id),
            ('state', '=', 'draft')
        ]
        # Check if all services were activated
        if not contract_service_obj.search(query):

            # jgama - Try to create the prorata invoice
            # pro_inv = account_analytic_account_obj.create_invoice
            # (prorata=True)
            pass
        return ret
