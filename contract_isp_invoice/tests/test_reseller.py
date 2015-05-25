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

from ..invoice import PROCESS_RECURRENT

from .common import ServiceSetup, YEAR


class test_reseller_invoice(TransactionCase, ServiceSetup):
    """
    Tests specific reseller behaviors for invoices
    """
    def setUp(self):
        super(test_reseller_invoice, self).setUp()
        self._common_setup()

    def _create_account(self):
        for partner in [self.partner_id1, self.partner_id2]:
            self.partner_id = partner
            super(test_reseller_invoice, self)._create_account()

    def _create_partner(self):
        cr, uid = self.cr, self.uid
        p_o = self.partner_obj
        self.parent_id = p_o.create(cr, uid, {
            "is_company": True,
            "is_reseller": True,
            "name": "Test Company",
        })
        self.partner_id1 = p_o.create(cr, uid, {
            "name": "Test Partner",
            "parent_id": self.parent_id,
        })
        self.partner_id2 = p_o.create(cr, uid, {
            "name": "Test Partner",
            "parent_id": self.parent_id,
        })

    def test_prorata_invoice(self):
        self.partner_id = self.partner_id1
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

    def _get_lines_to_invoice(self):
        return self.analytic_line_obj.search(
            self.cr, self.uid, [
                ('account_id.partner_id', 'child_of', self.parent_id),
                ('invoice_id', '=', False),
                ('to_invoice', '!=', False),
            ])

    def test_create_monthly_invoice(self):
        """
        Test creating the monthly invoice for a client
        """
        cr, uid = self.cr, self.uid
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})

        # Activate a service on Jan 14th. This will create the pro-rata
        # invoice for Feb 14th - Feb 28th
        for partner in (self.partner_id1, self.partner_id2):
            self.partner_id = partner
            self._create_activate_service(
                self.p_internet, "{0}-01-14".format(YEAR), {
                    "operation_date": date(YEAR, 1, 14),
                }
            )

        self.assertFalse(self._get_lines_to_invoice(),
                         "There should not be any lines to invoice")

        # Create the invoice on Feb 7th, it will be for all of March
        context = {
            'create_analytic_line_mode': 'cron',
            'create_invoice_mode': 'reseller',
            'operation_date': date(YEAR, 2, 7),
        }
        self.account_obj.create_lines_and_invoice(
            self.cr, self.uid, [self.account_id], PROCESS_RECURRENT,
            context=context)

        self.assertFalse(self._get_lines_to_invoice(),
                         "There should not be any lines to invoice")

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.parent_id)],
                                    order="id desc", limit=1)[0]
        )
        self.assertEquals(invoice.date_invoice, "{0}-02-07".format(YEAR))
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, "{0}-03-01".format(YEAR),
                          "Wrong start date")
        self.assertEquals(date_to, "{0}-03-31".format(YEAR), "Wrong end date")
