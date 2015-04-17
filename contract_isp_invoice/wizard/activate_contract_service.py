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

from openerp.osv import orm
from ..invoice import PROCESS_PRORATA


class contract_service_activate(orm.TransientModel):
    _inherit = 'contract.service.activate'

    def activate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        wizard = self.browse(cr, uid, ids[0], context)

        ret = super(contract_service_activate, self).activate(cr, uid,
                                                              ids,
                                                              context=context)

        self.pool["contract.pending.invoice"].trigger_or_invoice(
            cr, uid,
            contract_id=wizard.account_id.id,
            source_process=PROCESS_PRORATA,
            context=context,
        )

        return ret


class contract_service_deactivate(orm.TransientModel):
    _inherit = 'contract.service.deactivate'

    def deactivate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        wizard = self.browse(cr, uid, ids[0], context)

        ret = super(contract_service_deactivate, self).deactivate(
            cr, uid, ids, context=context)

        self.pool["contract.pending.invoice"].trigger_or_invoice(
            cr, uid,
            contract_id=wizard.account_id.id,
            source_process=PROCESS_PRORATA,
            context=context,
        )

        return ret
