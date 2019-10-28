# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Connector Equipment',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'summary': 'Connect Equipment to Outside API',
    'author': 'Open Source Integrators, Odoo Community Association (OCA)',
    "website": 'https://github.com/OCA/vertical-isp',
    'depends': ['maintenance'],
    'data': [
        'views/maintenance_equipment.xml',
        'views/backend_equipment.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [
        'demo/backend_equipment_demo.xml',
    ],
    'installable': True,
    'development_status': 'Beta',
    'maintainers': [
        'wolfhall',
        'max3903',
        'osi-scampbell',
    ],
}
