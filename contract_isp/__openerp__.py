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
    'name': 'Contract ISP',
    'version': '1.0',
    'category': 'Contract Management',
    'description': """
Manage service based contracts
==============================

This module adds a service based contract category were you can manage diferent services and service types that are included in the contract.

Features:
---------

* Differents types of services (recurrent, exceptions, one time only),
* Pro-rata logic,
* Service activation wizard.
""",
    'author': 'Savoir-faire Linux Inc',
    'website': 'www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'depends': ['account_analytic_analysis'],
    'data': ['security/contract_isp_security.xml',
             'security/ir.model.access.csv',
             'wizard/activate_contract_service.xml',
             'contract_isp_view.xml',
             'contract_isp_data.xml',
             'contract_isp_workflow.xml'],
    'active': False,
    'installable': True,
}
