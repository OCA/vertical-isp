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


class test_prorata_deactivate_service(TransactionCase, ServiceSetup):
    """
    Tests pro-rata crediting of services at deactivation
    """
    def setUp(self):
        super(test_prorata_deactivate_service, self).setUp()
        self._common_setup()

    def _common_setup(self):
        super(test_prorata_deactivate_service, self)._common_setup()
        self._create_active_service()

    def _create_active_service(self):
        cr, uid = self.cr, self.uid
        service = self.service_obj.on_change_product_id(
            cr, uid, [],
            self.p_internet,
        )["value"]
        service.update({
            "product_id": self.p_internet,
            "account_id": self.account_id,
            "state": "active",
        })
        self.service_id = self.service_obj.create(cr, uid, service)

    def _deactivate_service(self, deactivation_date, context=None):
        context = context or {}
        cr, uid = self.cr, self.uid
        wiz_id = self.wiz_deactivate_obj.create(
            cr, uid, {
                "account_id": self.account_id,
                "service_id": self.service_id,
                "deactivation_date": deactivation_date,
            },
            context=context,
        )
        self.wiz_deactivate_obj.deactivate(cr, uid, [wiz_id], context=context)

    def test_after_invoice_before_cutoff(self):
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._deactivate_service("2014-02-14", {
            "operation_date": date(2014, 2, 17),
        })
        invoice = self._get_last_invoice()
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(invoice.date_invoice, "2014-02-07")
        self.assertEquals(date_from, "2014-02-14", "Wrong start_date")
        self.assertEquals(date_to, "2014-03-31", "Wrong end_date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            (1 + self.service_obj._prorata_rate(14, 28)) * 56,
            msg="Expect refund for 14-28 feb + march")
        self.assertEquals(invoice.type, "out_refund")

    def test_after_invoice_after_cutoff(self):
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._deactivate_service("2014-02-14", {
            "operation_date": date(2014, 2, 23),
        })
        invoice = self._get_last_invoice()
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(invoice.date_invoice, "2014-03-07")
        self.assertEquals(date_from, "2014-02-14", "Wrong start_date")
        self.assertEquals(date_to, "2014-03-31", "Wrong end_date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            (1 + self.service_obj._prorata_rate(14, 28)) * 56,
            msg="Expect refund for 14-28 feb + march")
        self.assertEquals(invoice.type, "out_refund")

    def test_before_invoice_past_deactivation_curmonth(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._deactivate_service("2014-02-07", {
            "operation_date": date(2014, 2, 8),
        })
        invoice = self._get_last_invoice()
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(invoice.date_invoice, "2014-02-14")
        self.assertEquals(date_from, "2014-02-07", "Wrong start_date")
        self.assertEquals(date_to, "2014-02-28", "Wrong end_date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            self.service_obj._prorata_rate(21, 28) * 56,
            msg="Expect refund for 7-28 feb")
        self.assertEquals(invoice.type, "out_refund")

    def test_before_invoice_past_deactivation_past_month(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._deactivate_service("2014-02-07", {
            "operation_date": date(2014, 3, 8),
        })
        invoice = self._get_last_invoice()
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(invoice.date_invoice, "2014-03-14")
        self.assertEquals(date_from, "2014-02-07", "Wrong start_date")
        self.assertEquals(date_to, "2014-03-31", "Wrong end_date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            (1 + self.service_obj._prorata_rate(21, 28)) * 56,
            msg="Expect refund for 7-28 feb + march")
        self.assertEquals(invoice.type, "out_refund")

    def test_before_invoice_day_future_deactivation_same_month(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._deactivate_service("2014-02-14", {
            "operation_date": date(2014, 2, 7),
        })
        invoice = self._get_last_invoice()
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(invoice.date_invoice, "2014-02-14")
        self.assertEquals(date_from, "2014-02-07", "Wrong start_date")
        self.assertEquals(date_to, "2014-02-14", "Wrong end_date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            self.service_obj._prorata_rate(7, 28) * 56,
            msg="Expect invoice for 7-14 feb")
        self.assertEquals(invoice.type, "out_invoice")

    def test_before_invoice_day_future_deactivation_future_month(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._deactivate_service("2014-04-16", {
            "operation_date": date(2014, 2, 7),
        })
        invoice = self._get_last_invoice()
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(invoice.date_invoice, "2014-02-14")
        self.assertEquals(date_from, "2014-02-07", "Wrong start_date")
        self.assertEquals(date_to, "2014-04-16", "Wrong end_date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            56 * (
                self.service_obj._prorata_rate(21, 28) +
                self.service_obj._prorata_rate(16, 30) +
                1),
            msg="Expect invoice for 7-28 feb, march, 1-16 apr")
        self.assertEquals(invoice.type, "out_invoice")
