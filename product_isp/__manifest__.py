# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Product ISP',
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'summary': 'Assign ISPs to Products',
    'author': 'Open Source Integrators, Odoo Community Association (OCA)',
    "website": 'https://github.com/OCA/vertical-isp',
    'depends': [
        'product',
        'base_phone_rate'
    ],
    'data': [
        'views/product_product.xml',
    ],
    'installable': True,
    'development_status': 'Beta',
    'maintainers': [
        'wolfhall',
        'max3903',
        'osi-scampbell',
    ],
}
