# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase

import base64
import os


class TestImportBandwith(TransactionCase):

    def setUp(self):
        super(TestImportBandwith, self).setUp()
        self.open_data = None
        self.import_bandwith_obj = self.env['base.phone.rate.import.bandwith']
        with open(os.path.join(os.path.join(os.path.dirname(__file__),
                                            "../demo/bandwith.xlsx")), 'rb'
                  ) as generated_file:
            self.open_data = generated_file.read()
        self.data = base64.encodestring(self.open_data)
        self.wizard_rec = self.import_bandwith_obj.create({
            'upload_file': self.data,
            'filename': 'bandwith.xlsx'
        })

    def test_import_bandwith(self):
        self.wizard_rec.import_bandwith()
