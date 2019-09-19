import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-vertical-isp",
    description="Meta package for oca-vertical-isp Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-connector_equipment',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
