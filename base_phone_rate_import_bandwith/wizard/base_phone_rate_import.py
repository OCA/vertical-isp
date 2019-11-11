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
            fname = temp_path + '/xsl_file.xlsx'
            fp = open(fname, 'wb+')
            fp.write(csv_data)
            fp.close()
            wb = open_workbook(fname)
            for sheet in wb.sheets():
                for rownum in range(0, sheet.nrows):
                    if rownum > 0:
                        bandwith_data = sheet.row_values(rownum)
                        name = bandwith_data[0]
                        if ' (' in bandwith_data[0]:
                            country = name.split(' (')
                            country_name = country[0]
                        else:
                            country_name = name
                        country_rec = res_country_obj.search(
                            [('name', '=ilike', country_name)])
                        phone_rate_rec = phone_rate_obj.search(
                            [('dial_prefix', '=', bandwith_data[1])])
                        if phone_rate_rec:
                            phone_rate_rec.rate = bandwith_data[2]
                        else:
                            phone_rate_obj.create(
                                {'name': name,
                                 'country_id': country_rec.id,
                                 'dial_prefix': bandwith_data[1],
                                 'rate': bandwith_data[2]})
            os.remove(fname)
