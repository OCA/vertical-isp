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

from datetime import date, datetime, timedelta
from functools import partial

from openerp.tests.common import TransactionCase
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

from .common import ServiceSetup, YEAR


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
        self.company.write({"invoice_day": "7", "cutoff_day": "24"})
        self._test_invoice(
            self.p_internet,
            activation_date=(1, 13),
            operation_date=(1, 14),
            invoice_date=(1, 7),
            invoice_start=(2, 13),
            invoice_end=(2, 28),
            expected_amount=self.service_obj._prorata_rate(16, 28) * 56,
        )

    def test_prorata_after_invoice_before_cutoff_past_month(self):
        """
        Test prorata when:
            invoice_day < operation_date <= end of month
            operation date < cutoff date
        """
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._test_invoice(
            self.p_internet,
            activation_date=(8, 11),
            operation_date=(9, 10),
            invoice_date=(9, 7),
            invoice_start=(9, 11),
            invoice_end=(10, 31),
            expected_amount=(1 + self.service_obj._prorata_rate(20, 30)) * 56,
        )

    def test_prorata_after_invoice_after_cutoff(self):
        """
        Test prorata when:
            invoice_day < operation_date <= end of month
            operation date > cutoff date
        """
        self.company.write({"invoice_day": "7", "cutoff_day": "24"})
        self._test_invoice(
            self.p_internet,
            activation_date=(1, 15),
            operation_date=(1, 26),
            invoice_date=(2, 7),
            invoice_start=(2, 15),
            invoice_end=(2, 28),
            expected_amount=self.service_obj._prorata_rate(14, 28) * 56,
        )

    def test_prorata_before_invoice_past_month_activation(self):
        """
        Test prorata when:
            1 <= operation_date <= invoice_day
            activation is in the past month

        """
        self.company.write({"invoice_day": "7", "cutoff_day": "21"})
        self._test_invoice(
            self.p_internet,
            activation_date=(1, 27),
            operation_date=(2, 1),
            invoice_date=(2, 7),
            invoice_start=(2, 27),
            invoice_end=(2, 28),
            expected_amount=self.service_obj._prorata_rate(2, 28) * 56,
        )

    def test_prorata_before_invoice_current_month_activation(self):
        """
        Test prorata when:
            1 <= operation_date <= invoice_day
            activation is in the current month and < invoice_day

        """
        self.company.write({"invoice_day": "21", "cutoff_day": "24"})
        self._test_invoice(
            self.p_internet,
            activation_date=(2, 14),
            operation_date=(2, 10),
            invoice_date=(2, 21),
            invoice_start=(3, 1),
            invoice_end=(3, 14),
            expected_amount=self.service_obj._prorata_rate(14, 31) * -56,
        )

    def test_prorata_febuary(self):
        """
        Test activating a service for Jan 1st between the Jan Cutoff
        and Feb Invoice Day
        """
        self.company.write({"invoice_day": "7", "cutoff_day": "24"})
        self._test_invoice(self.p_internet,
                           activation_date=(1, 1),
                           operation_date=(2, 5),
                           invoice_date=(2, 7),
                           invoice_start=(2, 1),
                           invoice_end=(2, 28),
                           expected_amount=56)

    def _test_invoice(self, product,
                      activation_date, operation_date,
                      invoice_date, invoice_start, invoice_end,
                      expected_amount):
        """ create and activate a service, then check the resulting invoice

        Dates are all passed as numeric (month, day) tuples to allow filling
        in the year.

        invoice start and end correspond to date period covered

        amount should be positive for invoices, negative for credits/refunds
        """
        cr, uid = self.cr, self.uid
        strdate = partial("{0}-{1:02}-{2:02}".format, YEAR)
        act_month, act_day = activation_date
        op_month, op_day = operation_date
        inv_month, inv_day = invoice_date
        inv_start_month, inv_start_day = invoice_start
        inv_end_month, inv_end_day = invoice_end

        inv_type = "out_invoice"
        if expected_amount < 0:
            inv_type = "out_refund"
            expected_amount = abs(expected_amount)

        self._create_activate_service(
            product, strdate(act_month, act_day), {
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

    def test_bill_delay(self):
        cr, uid = self.cr, self.ref("base.user_demo")
        su_uid = self.uid

        self.company.write({"prorata_bill_delay": "5"})
        act_date = "{0}-05-05".format(YEAR)
        self.cr.execute(
            """ SELECT COALESCE(max(id), 0) from account_invoice
            WHERE partner_id = %s
            """,
            (self.partner_id, )
        )
        max_invoice = self.cr.fetchone()[0]
        now = datetime.utcnow()
        sid = self._create_activate_service(self.p_internet, act_date)
        self.wiz_deactivate_obj.deactivate(
            cr, uid,
            [self.wiz_deactivate_obj.create(
                cr, uid, {
                    "account_id": self.account_id,
                    "service_id": sid,
                    "deactivation_date": "{0}-05-06".format(YEAR),
                })],
            {'operation_date': date(YEAR, 5, 6)}
        )

        new_invoices = self.invoice_obj.search(
            cr, uid, [('partner_id', '=', self.partner_id),
                      ('id', '>', max_invoice)],
        )
        self.assertEquals(new_invoices, [],
                          "No new invoice expected")

        # Delay is not passed yet, expecting no new invoice
        self.registry("contract.pending.invoice").cron_send_pending(
            cr, su_uid, curtime=now.strftime(DEFAULT_SERVER_DATETIME_FORMAT))

        new_invoices = self.invoice_obj.search(
            cr, su_uid, [('partner_id', '=', self.partner_id),
                         ('id', '>', max_invoice)],
        )
        self.assertEquals(new_invoices, [],
                          "No new invoice expected")

        self.registry("contract.pending.invoice").cron_send_pending(
            cr, su_uid, curtime=(
                now + timedelta(minutes=6)
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            autocommit=False,
        )

        new_invoices = self.invoice_obj.search(
            cr, su_uid, [('partner_id', '=', self.partner_id),
                         ('id', '>', max_invoice)],
        )
        self.assertEquals(len(new_invoices), 1,
                          "One new invoice expected")
