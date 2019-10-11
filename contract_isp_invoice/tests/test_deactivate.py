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

from calendar import monthrange
from datetime import date
from functools import partial

from openerp.tests.common import TransactionCase

from .common import ServiceSetup, YEAR


END_FEB = monthrange(YEAR, 2)[1]  # Last day of February


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
        self._test_invoice(
            deactivation_date=(2, 14),
            operation_date=(2, 17),
            invoice_date=(2, 7),
            invoice_start=(2, 14),
            invoice_end=(3, 31),
            expected_amount=(
                1 +  # March,
                self.service_obj._prorata_rate(END_FEB - 13, END_FEB)
            ) * -56,  # Refund
        )

    def test_after_invoice_after_cutoff(self):
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._test_invoice(
            deactivation_date=(2, 14),
            operation_date=(2, 23),
            invoice_date=(3, 7),
            invoice_start=(2, 14),
            invoice_end=(3, 31),
            expected_amount=(
                1 +  # March,
                self.service_obj._prorata_rate(END_FEB - 13, END_FEB)
            ) * -56,  # Refund
        )

    def test_before_invoice_past_deactivation_curmonth(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._test_invoice(
            deactivation_date=(2, 7),
            operation_date=(2, 8),
            invoice_date=(2, 14),
            invoice_start=(2, 7),
            invoice_end=(2, END_FEB),
            expected_amount=(
                self.service_obj._prorata_rate(END_FEB - 6, END_FEB)
            ) * -56,  # Refund
        )

    def test_before_invoice_past_deactivation_past_month(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._test_invoice(
            deactivation_date=(2, 7),
            operation_date=(3, 8),
            invoice_date=(3, 14),
            invoice_start=(2, 7),
            invoice_end=(3, 31),
            expected_amount=(
                1 +  # March
                self.service_obj._prorata_rate(END_FEB - 6, END_FEB)
            ) * -56,  # Refund
        )

    def test_before_invoice_day_future_deactivation_same_month(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._test_invoice(
            deactivation_date=(2, 14),
            operation_date=(2, 7),
            invoice_date=(2, 14),
            invoice_start=(2, 7),
            invoice_end=(2, 14),
            expected_amount=(
                self.service_obj._prorata_rate(8, END_FEB)  # Feb 7-14 : 8 days
            ) * 56,  # Invoice
        )

    def test_before_invoice_day_future_deactivation_future_month(self):
        self.company.write({"invoice_day": "14", "cutoff_day": "21"})
        self._test_invoice(
            deactivation_date=(4, 16),
            operation_date=(2, 7),
            invoice_date=(2, 14),
            invoice_start=(2, 7),
            invoice_end=(4, 16),
            expected_amount=(
                # From Feb 7th to end of month, so len(feb) - 6 days
                self.service_obj._prorata_rate(END_FEB - 6, END_FEB) +
                # Apr 1-16 : 16 days
                self.service_obj._prorata_rate(16, 30) +
                # All of March
                1
            ) * 56,  # Invoice
        )

    def _test_invoice(self, deactivation_date, operation_date, invoice_date,
                      invoice_start, invoice_end, expected_amount):
        """ deactivate the service, then check the resulting invoice

        Dates are all passed as numeric (month, day) tuples to allow filling
        in the year.

        invoice start and end correspond to date period covered

        amount should be positive for invoices, negative for credits/refunds
        """
        cr, uid = self.cr, self.uid
        strdate = partial("{0}-{1:02}-{2:02}".format, YEAR)
        de_month, de_day = deactivation_date
        op_month, op_day = operation_date
        inv_month, inv_day = invoice_date
        inv_start_month, inv_start_day = invoice_start
        inv_end_month, inv_end_day = invoice_end

        inv_type = "out_invoice"
        if expected_amount < 0:
            inv_type = "out_refund"
            expected_amount = abs(expected_amount)

        self._deactivate_service(
            strdate(de_month, de_day), {
                "operation_date": date(YEAR, op_month, op_day),
            }
        )

        invoice = self.invoice_obj.browse(
            cr, uid,
            self.invoice_obj.search(cr, uid,
                                    [('partner_id', '=', self.partner_id)])[0]
        )
        self.assertEquals(invoice.date_invoice, strdate(inv_month, inv_day),
                          "Wrong invoice date")
        date_from, date_to = self._get_invoice_date_range(invoice.id)
        self.assertEquals(date_from, strdate(inv_start_month, inv_start_day),
                          "Wrong start date")
        self.assertEquals(date_to, strdate(inv_end_month, inv_end_day),
                          "Wrong end date")
        self.assertAlmostEquals(
            invoice.amount_untaxed,
            expected_amount,
            msg="Invoice is not the right amount",
            delta=0.01)
        self.assertEquals(invoice.type, inv_type,
                          msg="Wrong type of invoice/refund")
