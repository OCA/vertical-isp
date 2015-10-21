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
# from openerp.addons.contract_isp.models.contract import add_months
from openerp import models, fields, api


class contract_service_activate(models.TransientModel):
    _name = 'contract.service.activate'

    @api.one
    def _get_account_id(self):
        if self._context.get('active_model', '') == 'contract.service':
            contract_id = self._context.get('active_id')
            contract_service = self.env['contract.service'].browse(contract_id
                                                                   )
            return contract_service.account_id.id
        return None

    @api.one
    def _get_service_id(self):
        if self._context.get('active_model', '') == 'contract.service':
            service_id = self._context.get('active_id')
            contract_service = self.pool.get('contract.service').\
                browse(service_id)
            return contract_service.id
        return None

    activation_date = fields.Datetime('Activation Date',
                                      default=fields.datetime.now())
    account_id = fields.Many2one('account.analytic.account',
                                 'Account',
                                 default=lambda s: s._get_account_id())
    service_id = fields.Many2one('contract.service',
                                 'Service',
                                 default=lambda s: s._get_service_id())

    @api.multi
    def activate(self):
        company_obj = self.env['res.company']
        company_id = company_obj._company_default_get()
        # company_ids = company_obj.search([('id', '=', company_id)])
        # cutoff = company_ids[0].cutoff_day
        contract_service_obj = self.env['contract.service']
        contract_service = contract_service_obj.browse(self.service_id.id)

        activation_date = datetime.date(
            int(self.activation_date[:4]),
            int(self.activation_date[5:7]),
            int(self.activation_date[8:10]))

        #         cuttoff_day = cutoff
        #         invoice_day = company_ids[0].invoice_day
        #         cutoff_date = datetime.date(datetime.date.today().year,
        #                                     datetime.date.today().month,
        #                                     int(cuttoff_day))
        #         invoice_date = datetime.date(datetime.date.today().year,
        #                                      datetime.date.today().month,
        #                                      int(invoice_day))
        contract_service.write({
            'activation_date': self.activation_date,
            'state': 'active'
        })

        query = [
            ('account_id', '=', self.account_id.id),
            ('state', '=', 'draft')
        ]
        draft_line_ids = contract_service_obj.search(query)

        if not draft_line_ids:
            for line in self.account_id.contract_service_ids:
                if line.activation_line_generated is False:
                    line.create_analytic_line(mode='manual',
                                              date=activation_date)

                    if line.analytic_line_type == 'r':
                        line.create_analytic_line(mode='prorata',
                                                  date=activation_date)

        return True
