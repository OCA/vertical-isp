# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class PhoneRate(models.Model):
    _name = "phone.rate"

    name = fields.Char("Name", required=True)
    country_id = fields.Many2one('res.country', "Country", required=True)
    state_id = fields.Many2one('res.country.state', "Country State")
    dial_prefix = fields.Char("Dial Prefix", required=True)
    rate = fields.Float("Rate", required=True,
                        digits=dp.get_precision('Phone Rate'))

    _sql_constraints = [
        ('dial_prefix',
         'unique(dial_prefix)',
         'Dial Prefix on Phone Rate must be unique!')
    ]

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id:
            self.country_id = self.state_id.country_id

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.state_id.country_id != self.country_id:
            self.state_id = False
