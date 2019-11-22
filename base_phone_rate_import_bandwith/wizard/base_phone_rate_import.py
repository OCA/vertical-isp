# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import Warning
import odoo.tools as tools

from xlrd import open_workbook
import base64
import tempfile
import os


class BasePhoneRateImportBandwith(models.TransientModel):
    _name = "base.phone.rate.import.bandwith"
    _description = "Import Rates from Bandwidth.com"

    upload_file = fields.Binary("Upload File")
    filename = fields.Char("File name")

    @api.multi
    def import_bandwith(self):
        res_country_obj = self.env['res.country']
        phone_rate_obj = self.env['phone.rate']
        for data in self:
            filename_str = tools.ustr(data.filename)
            if not data.upload_file:
                raise Warning(_('Please select a file to proceed.'))
            if not filename_str[-5:] == ".xlsx":
                raise Warning(_('Select .xlsx file only'))
            csv_data = base64.decodestring(data.upload_file)
            temp_path = tempfile.gettempdir()
            fname = os.path.join(temp_path, filename_str)
            with open(fname, 'wb+') as fp:
                fp.write(csv_data)
            wb = open_workbook(fname)
            sheet = wb.sheets()[0]

            for rownum in range(1, sheet.nrows):
                bandwith_data = sheet.row_values(rownum)
                name = bandwith_data[0]
                dial_prefix = int(bandwith_data[1])
                rate = bandwith_data[2]

                country_name = name.split(' (')[0] if ' (' in name else name
                country_rec = res_country_obj.search(
                    [('name', '=ilike', country_name)])
                values = {
                    'name': name,
                    'country_id': country_rec.id,
                    'dial_prefix': dial_prefix,
                    'rate': rate,
                }

                phone_rate_rec = phone_rate_obj.search(
                    [('dial_prefix', '=', dial_prefix)])
                if phone_rate_rec:
                    phone_rate_rec.update(values)
                else:
                    phone_rate_obj.create(values)
            os.remove(fname)
