# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Import Phone Rates from Bandwith.com',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'summary': '''This module allows you to load and update the phone rates
    using the file provided by Bandwidth (https://www.bandwidth.com).''',
    'author': 'Open Source Integrators, Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/vertical-isp',
    'depends': [
        'base_phone_rate'
    ],
    'data': [
        'wizard/base_phone_rate_import_view.xml',
    ],
    'installable': True,
    'development_status': 'Beta',
    'external_dependencies': {'python': ['xlrd']},
    'maintainers': [
        'wolfhall',
        'max3903'
    ],
}
