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
    'name': 'Product Dependencies',
    'version': '1.0.1',
    'category': 'Product Management',
    'description': """
Product Dependencies
====================

Allows products to have other products/categories as dependencies.

This module is primarily used by the contract_isp_wizard module to create
product/service packages based on product inter-dependencies. It's aim is
to provide the basic structure so that other modules can build sales
wizards with decision trees based on each product dependency tree.

This module is not related to the manufacturing process or the Bill of
Materials.
    """,
    'author': "Savoir-faire Linux,Odoo Community Association (OCA)",
    'website': 'www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'product_dependencies_view.xml'
    ],
    'active': False,
    'installable': True,
}
