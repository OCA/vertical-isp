# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoirfaire-Linux Inc. (<www.savoirfairelinux.com>).
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
    'name': 'Contract ISP Package Configurator',
    'version': '1.0',
    'category': 'Sale',
    'description': """
Contract ISP Package Configurator
=================================

This module provides a wizard to help create service packages based on product
inter-dependencies. It uses the dependency tree provided by the
product_dependencies module.""",
    'author': "Savoir-faire Linux,Odoo Community Association (OCA)",
    'website': 'www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'depends': ['contract_isp', 'product_dependencies', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'wizard/package_configurator.xml',
        'workflow/contract_isp_package_configurator.xml',
        'contract_isp_package_configurator_view.xml',
    ],
    'css': [
        'static/src/css/configurator.css',
    ],
    'active': False,
    'installable': True,
}
