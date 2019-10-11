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

{
    'name': 'Contract ISP Invoice',
    'version': '1.0',
    'category': 'Contract Management',
    'description': """
Invoicing for service based contracts
=====================================

Generates invoices for service based contracts.

Features:
---------

* Refund on contract closing
* Exception services invoice logic
""",
    'author': "Savoir-faire Linux,Odoo Community Association (OCA)",
    'website': 'www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'depends': ['contract_isp'],
    'data': [
        'security/ir.model.access.csv',
        'contract_isp_invoice_data.xml',
        'contract_isp_invoice_view.xml',
        'view_company.xml',
        'wizard/contract_isp_invoice_invoice_create.xml',
        'wizard/close_contract_view.xml'
    ],
    'demo': [
        'demo_security.xml',
    ],
    'active': False,
    'installable': True,
}
