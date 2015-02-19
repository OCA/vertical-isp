# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Savoir-faire Linux (<www.savoirfairelinux.com>).
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

PROCESS_CRON = 'cron'
PROCESS_INITIAL = 'initial'
PROCESS_MANUAL = 'manual'
PROCESS_PRORATA = 'prorata'
PROCESS_RECURRENT = 'recurrent'


class Invoice(orm.Model):
    _name = _inherit = 'account.invoice'
    _columns = {
        'source_process': fields.selection([
            (PROCESS_CRON, 'Scheduled'),
            (PROCESS_INITIAL, 'Initial'),
            (PROCESS_MANUAL, 'Manual'),
            (PROCESS_PRORATA, 'Pro Rata'),
            (PROCESS_RECURRENT, 'Recurrent Billing'),
        ], 'Billing Process', required=False),
    }
