# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoir-faire Linux Inc. (<www.savoirfairelinux.com>).
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
    'name': 'Contract ISP Automatic Invoicing',
    'version': '1.0',
    'category': 'Account',
    'description': """A module to automatically invoice services based contracts""",
    'author': 'Savoir-faire Linux Inc.',
    'website': 'www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'depends': ['contract_isp_invoice'],
    'data': ['contract_isp_automatic_invoicing_data.xml'],
    'active': False,
    'installable': True,
}
