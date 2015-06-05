# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
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
    'name': 'Contract ISP - Unique Product in Contract',
    'version': '0.1',
    'author': "Savoir-faire Linux,Odoo Community Association (OCA)",
    'maintainer': 'Odoo Community Association (OCA)',
    'website': 'http://www.savoirfairelinux.com',
    'license': 'AGPL-3',
    'category': 'Contract Manage',
    'summary': 'Selectively enforce unique product lines in contracts',
    'description': """
This module prevents creating or updating contracts with multiple services
with the same product code.

Contributors
------------
* Vincent Vinet (vincent.vinet@savoirfairelinux.com)
""",
    'depends': [
        'contract_isp',
    ],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        'contract_view.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
