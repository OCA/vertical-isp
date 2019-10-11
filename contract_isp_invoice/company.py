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

from openerp.osv import orm, fields


class Company(orm.Model):
    _name = _inherit = "res.company"

    def _days(self, cr, uid, context=None):
        return tuple([(str(x), str(x)) for x in range(1, 29)])

    _columns = {
        'invoice_day': fields.selection(_days, 'Invoice day'),
        'billing_day': fields.selection(_days, 'Billing day'),
        'send_email_contract_invoice': fields.boolean('Send invoice by email'),
        'prorata_bill_delay': fields.integer('Prorata Invoice delay minutes'),
    }

    _defaults = {
        'send_email_contract_invoice': True
    }

    def get_prorata_bill_delay(self, cr, uid, company_id=None, context=None):
        if company_id:
            company = self.browse(cr, uid, company_id)
        else:
            company = self.pool["res.users"].browse(cr, uid, uid).company_id

        return company.prorata_bill_delay or 0
