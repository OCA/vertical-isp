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

from openerp.tools.translate import _
from openerp.osv import orm, fields

from openerp.addons.contract_isp.wizard.activate_contract_service import (
    _get_account_id,
    _get_service_id,
)


class ContractServiceDelete(orm.TransientModel):
    _name = 'contract.service.delete'
    _get_account_id = _get_account_id
    _get_service_id = _get_service_id

    _columns = {
        'message': fields.text('Message'),
        'account_id': fields.many2one('account.analytic.account', 'Account'),
        'service_id': fields.many2one('contract.service', 'Service')
    }

    def _get_message(self, cr, uid, ids, context=None):
        return _("When deleting a duplicate service, make sure you are "
                 "deleting the inactive one")

    _defaults = {
        'message': _get_message,
        'account_id': _get_account_id,
        'service_id': _get_service_id,
    }

    def delete(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context)
        wizard.account_id.write({
            'contract_service_ids': [(2, wizard.service_id.id)],
        })
        return True
