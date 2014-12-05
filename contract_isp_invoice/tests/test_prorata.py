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

from .common import ServiceSetup


class test_prorata_activate_service(TransactionCase, ServiceSetup):
    """
    Tests pro-rata invoicing of services
    """

    def setUp(self):
        super(test_prorata_activate_service, self).setUp()
        self._common_setup()

    def test_prorata_after_invoice_before_cutoff_current_month(self):
        """
        Test prorata when:
            invoice_day < operation_date <= end of month
            operation date < cutoff date
        """
        cr, uid = self.cr, self.uid
        self.company.write({"invoice_day": "7", "cutoff_day": "24"})
        self._create_activate_service(self.p_internet, "2014-01-13", {
            "operation_date": date(2014, 1, 14),
        })

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.partner_id)])[0]
        )
        self.assertEquals(invoice.date_invoice, "2014-01-07")
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, "2014-02-13", "Wrong start date")
        self.assertEquals(date_to, "2014-02-28", "Wrong end date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            self.service_obj._prorata_rate(15, 28) * 56,
            msg="~Half month, 15/28 of 56",
            delta=0.01)

    def test_prorata_after_invoice_before_cutoff_past_month(self):
        """
        Test prorata when:
            invoice_day < operation_date <= end of month
            operation date < cutoff date
        """
        cr, uid = self.cr, self.uid
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._create_activate_service(self.p_internet, "2014-08-11", {
            "operation_date": date(2014, 9, 10),
        })

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.partner_id)])[0]
        )
        self.assertEquals(invoice.date_invoice, "2014-09-07")
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, "2014-09-11",
                          "Wrong start date, expected activation + 1 month")
        self.assertEquals(date_to, "2014-10-31",
                          "Wrong end date, end of (op) next month")

        self.assertAlmostEquals(
            invoice.amount_untaxed,
            (1 + self.service_obj._prorata_rate(19, 30)) * 56,
            msg="Oct 100%, Sept 11-30",
            delta=0.01)

    def test_prorata_after_invoice_after_cutoff(self):
        """
        Test prorata when:
            invoice_day < operation_date <= end of month
            operation date > cutoff date
        """
        cr, uid = self.cr, self.uid
        self.company.write({"invoice_day": "7", "cutoff_day": "24"})
        self._create_activate_service(self.p_internet, "2014-01-15", {
            "operation_date": date(2014, 1, 26),
        })

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.partner_id)])[0]
        )
        self.assertEquals(invoice.date_invoice, "2014-02-07")
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, "2014-02-15", "Wrong start date")
        self.assertEquals(date_to, "2014-02-28", "Wrong end date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            self.service_obj._prorata_rate(13, 28) * 56,
            msg="13/28 of 56",
            delta=0.01)

    def test_prorata_before_invoice_past_month_activation(self):
        """
        Test prorata when:
            1 <= operation_date <= invoice_day
            activation is in the past month

        """
        cr, uid = self.cr, self.uid
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._create_activate_service(self.p_internet, "2014-01-27", {
            "operation_date": date(2014, 2, 1),
        })

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.partner_id)])[0]
        )
        self.assertEquals(invoice.date_invoice, "2014-02-07")
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, "2014-02-27", "Wrong start date")
        self.assertEquals(date_to, "2014-02-28", "Wrong end date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            self.service_obj._prorata_rate(1, 28) * 56,
            msg="1 day in feb",
            delta=0.01)

    def test_prorata_before_invoice_current_month_activation(self):
        """
        Test prorata when:
            1 <= operation_date <= invoice_day
            activation is in the current month and < invoice_day

        """
        cr, uid = self.cr, self.uid
        self.company.write({"invoice_day": "21", "cutoff_day": "24"})
        self._create_activate_service(self.p_internet, "2014-02-14", {
            "operation_date": date(2014, 2, 10),
        })

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.partner_id)])[0]
        )
        self.assertEquals(invoice.date_invoice, "2014-02-21")
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, "2014-03-01", "Wrong start date")
        self.assertEquals(date_to, "2014-03-14", "Wrong end date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            self.service_obj._prorata_rate(14, 31) * 56,
            msg="credit for 1-14 in match",
            delta=0.01)
        self.assertEquals(invoice.type, "out_refund",
                        msg="Expected Credit Note")