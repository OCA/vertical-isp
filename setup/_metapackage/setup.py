import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-vertical-isp",
    description="Meta package for oca-vertical-isp Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-base_phone_rate',
        'odoo12-addon-base_phone_rate_import_bandwith',
        'odoo12-addon-connector_equipment',
        'odoo12-addon-connector_equipment_service',
        'odoo12-addon-product_isp',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
