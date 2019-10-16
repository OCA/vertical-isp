# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'
    _description = 'Maintenance Equipment'

    backend_id = fields.Many2one('backend.equipment',
                                 string="Backend Equipment")
    managed = fields.Boolean('Can be managed')

    def update_config(self):
        return True

    def _connect(self, function, serviceprofiles=None):
        if function == 'update_config':
            self.update_config()
        elif function == 'add_service':
            if serviceprofiles:
                for sp_id in serviceprofiles:
                    self.add_service(sp_id)
        elif function == 'update_service':
            if serviceprofiles:
                for sp_id in serviceprofiles:
                    self.update_service(sp_id)
        elif function == 'activate_service':
            if serviceprofiles:
                for sp_id in serviceprofiles:
                    self.activate_service(sp_id)
        elif function == 'suspend_service':
            if serviceprofiles:
                for sp_id in serviceprofiles:
                    self.suspend_service(sp_id)
        elif function == 'remove_service':
            if serviceprofiles:
                for sp_id in serviceprofiles:
                    self.remove_service(sp_id)

    @api.multi
    def create(self, vals):
        res = super().create(vals)
        if self.managed:
            self._connect('update_config')
        return res

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if self.managed:
            self._connect('update_config')
        return res
