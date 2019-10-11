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

from openerp.addons.contract_isp.contract import (
    LINE_TYPE_RECURRENT,
    LINE_TYPE_ONETIME,
)

from datetime import datetime

YEAR = datetime.today().year


class ServiceSetup(object):
    """ Mixin class to provide setup and utils for testing invoicing """

    def _common_setup(self):
        self._init_modules()
        self._configure_company()
        self._create_partner()
        self._create_account()
        self._create_products()

    def _init_modules(self):
        self.account_obj = self.registry("account.analytic.account")
        self.analytic_line_obj = self.registry("account.analytic.line")
        self.company_obj = self.registry("res.company")
        self.service_obj = self.registry("contract.service")
        self.partner_obj = self.registry("res.partner")
        self.product_obj = self.registry("product.product")
        self.invoice_obj = self.registry("account.invoice")
        self.wiz_activate_obj = self.registry("contract.service.activate")
        self.wiz_deactivate_obj = self.registry("contract.service.deactivate")
        # Remove date constraints for our tests
        self.wiz_activate_obj._constraints[:1] = []
        self.wiz_deactivate_obj._constraints[:1] = []

    def _configure_company(self):
        self.company = self.company_obj.browse(self.cr, self.uid, 1)
        self.company.write({
            "cutoff_day": "7",
            "invoice_day": "14",
            "prorata_bill_delay": 0,
        })

    def _create_partner(self):
        self.partner_id = self.partner_obj.name_create(
            self.cr, self.uid,
            "Test Partner"
        )[0]

    def _get_last_invoice(self, query=None, partner_id=None):
        domain = [("partner_id", "=", partner_id or self.partner_id)]
        if query:
            domain.extend(query)
        invoice = self.invoice_obj.browse(
            self.cr, self.uid,
            self.invoice_obj.search(
                self.cr, self.uid,
                domain,
                order="id desc",
                limit=1,
            )[0]
        )
        return invoice

    def _create_products(self):
        cr, uid = self.cr, self.uid
        self.p_internet = self.product_obj.create(cr, uid, {
            "name": "Cable Internet",
            "type": "service",
            "analytic_line_type": LINE_TYPE_RECURRENT,
            "code": "CBL",
            "list_price": 56.0,
        })
        self.p_inst = self.product_obj.create(cr, uid, {
            "name": "Installation",
            "type": "service",
            "analytic_line_type": LINE_TYPE_ONETIME,
            "code": "INST",
            "list_price": 50.0,
        })

    def _create_account(self):
        wr = self.account_obj.default_get(self.cr, self.uid,
                                          self.account_obj._columns.keys())
        wr.update({
            "partner_id": self.partner_id,
            "pricelist_id": 1,
        })
        onchange = self.account_obj.on_change_partner_id(
            self.cr, self.uid, [],
            self.partner_id, False, False,
        )["value"]
        wr.update(onchange)

        self.account_id = self.account_obj.create(self.cr, self.uid, wr)

    def _create_activate_service(self, product, activation_date, context=None):
        context = context or {}
        cr, uid = self.cr, self.uid
        service = self.service_obj.on_change_product_id(
            cr, uid, [],
            self.p_internet,
        )["value"]
        service.update({
            "product_id": self.p_internet,
            "account_id": self.account_id,
        })
        service_id = self.service_obj.create(cr, uid, service, context=context)
        wiz_id = self.wiz_activate_obj.create(
            cr, uid, {
                "account_id": self.account_id,
                "service_id": service_id,
                "activation_date": activation_date,
            },
            context=context,
        )
        self.wiz_activate_obj.activate(cr, uid, [wiz_id], context=context)
        return service_id

    def _get_invoice_date_range(self, invoice_id):
        # Until we put a bit more common sense into period handling, this
        # is our way of knowing the start/end dates of an invoice
        cr, uid = self.cr, self.uid
        invoice_line = self.analytic_line_obj.browse(
            cr, uid,
            self.analytic_line_obj.search(cr, uid, [
                ('to_invoice', '!=', False),
                ('invoice_id', '=', invoice_id),
            ])[0]
        )
        date_from = invoice_line.name[-24:-14]
        date_to = invoice_line.name[-11:-1]

        if len(date_from.split("/")[-1]) == 4:
            date_from = datetime.strptime(date_from,
                                          '%m/%d/%Y').strftime('%Y-%m-%d')
            date_to = datetime.strptime(date_to,
                                        '%m/%d/%Y').strftime('%Y-%m-%d')
        return date_from, date_to
