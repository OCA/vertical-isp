# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _name = 'backend.equipment'
    _description = 'Backend Equipment'

    name = fields.Char('Name')
    host = fields.Char('Host')
    port = fields.Char('Port')
    user = fields.Char('User')
    password = fields.Char('Password')
    protocol = fields.Selection([('http_json', 'HTTP/JSON'),
                                 ('rest', 'REST')], 'Protocol')

    equipment_ids = fields.One2many('maintenance.equipment', 'backend_id',
                                    string="Equipments")
    client = fields.Char('Client ID')
    client_secret = fields.Char('Client Secret')
