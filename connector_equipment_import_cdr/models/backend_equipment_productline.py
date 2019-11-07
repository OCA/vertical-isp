# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BackendEquipmentProductline(models.Model):
    _name = 'backend.equipment.product_line'
    _description = 'Backend Equipment Productline'
    _order = "sequence"

    name = fields.Many2one('product.product', "Product")
    pattern = fields.Char('Pattern', help="The pattern is a regular expression that\
     will applied on the phone number to detect a domestic call, an\
      international call or a toll free call.")
    sequence = fields.Integer('Sequence')
    backend_id = fields.Many2one('backend.equipment', "Backend")
