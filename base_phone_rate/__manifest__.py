# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Base Phone Rate',
    'version': '12.0.0.1.0',
    'license': 'AGPL-3',
    'summary': 'Store international rates for phone call',
    'author': 'Open Source Integrators, Odoo Community Association (OCA)',
    "website": 'https://github.com/OCA/vertical-isp',
    'depends': [
        'contacts',
        'decimal_precision'
    ],
    'data': [
        'views/phone_rate.xml',
        'security/ir.model.access.csv',
        'data/decimal_precision.xml',
    ],
    'installable': True,
    'development_status': 'Beta',
    'maintainers': [
        'wolfhall',
        'max3903',
        'osi-scampbell',
    ],
}
