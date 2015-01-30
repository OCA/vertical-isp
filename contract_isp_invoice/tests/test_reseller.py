# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
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
from __future__ import unicode_literals

from datetime import date

from openerp.tests.common import TransactionCase

from .common import ServiceSetup, YEAR


class test_reseller_invoice(TransactionCase, ServiceSetup):
    """
    Tests specific reseller behaviors for invoices
    """
    def setUp(self):
        super(test_reseller_invoice, self).setUp()
        self._common_setup()

    def _create_partner(self):
        cr, uid = self.cr, self.uid
        p_o = self.partner_obj
        self.parent_id = p_o.create(cr, uid, {
            "is_company": True,
            "is_reseller": True,
            "name": "Test Company",
        })
        self.partner_id = p_o.create(cr, uid, {
            "name": "Test Partner",
            "parent_id": self.parent_id,
        })

    def test_prorata_invoice(self):
        self._create_activate_service(
            self.p_internet, "{0}-02-08".format(YEAR), {
                "operation_date": date(YEAR, 2, 10),
            })

        self.assertEquals(
            len(self.invoice_obj.search(self.cr, self.uid, [
                ('partner_id', '=', self.parent_id),
            ])),
            1,
            "Expected one new invoice on parent"
        )

        self.assertEquals(
            len(self.invoice_obj.search(self.cr, self.uid, [
                ('partner_id', '=', self.partner_id),
            ])),
            0,
            "Expected no new invoice on child"
        )
