# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Connector Equipment Import CDR',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'summary': 'This module allows to import the CDR data from the Netsapiens\
     backend as Odoo analytic lines.',
    'author': 'Open Source Integrators, Odoo Community Association (OCA)',
    "website": 'https://github.com/OCA/vertical-isp',
    'depends': [
        'account',
        'sale_timesheet',
        'agreement_legal_sale',
        'agreement_maintenance',
        'base_phone_rate',
        'connector_equipment',
    ],
    'data': [
        'data/product_data.xml',
        'data/backend_equipment_cron.xml',
        'security/ir.model.access.csv',
        'views/agreement_serviceprofile.xml',
        'views/backend_equipment_productline.xml',
        'views/backend_view.xml',
    ],
    'demo': [
        'demo/backend_equipment_productline_demo.xml',
    ],
    'installable': True,
    'development_status': 'Beta',
    'maintainers': [
        'wolfhall',
        'max3903',
    ],
}
