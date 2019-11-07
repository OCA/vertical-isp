# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class AgreementServiceProfile(models.Model):
    _inherit = 'agreement.serviceprofile'

    domain = fields.Char()
    last_cdr_sync = fields.Date("Last CDR Data Sync Date")
