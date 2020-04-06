# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Connector Equipment Service',
    'version': '12.0.1.0.2',
    'license': 'AGPL-3',
    'summary': 'Combine Connector Equipment and Service Profiles',
    'author': 'Open Source Integrators, Odoo Community Association (OCA)',
    "website": "https://github.com/OCA/vertical-isp",
    'depends': [
        'maintenance',
        'connector_equipment',
        'agreement_serviceprofile',
        'agreement_maintenance'
    ],
    'installable': True,
    'data': [
    ],
    'development_status': 'Beta',
    'maintainers': [
        'wolfhall',
        'max3903',
        'osi-scampbell',
    ],
}
