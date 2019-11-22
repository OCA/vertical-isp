# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PhoneRate(models.Model):
    _inherit = "phone.rate"
    _description = "Phone Rate"

    country_id = fields.Many2one('res.country', "Country", required=False)
