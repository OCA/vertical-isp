# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'
    _description = 'Maintenance Equipment'

    @api.multi
    def add_service(self, service_profile):
        return False
        # raise NotImplementedError()

    @api.multi
    def update_service(self, service_profile):
        return False
        # raise NotImplementedError()

    @api.multi
    def activate_service(self, service_profile):
        return False
        # raise NotImplementedError()

    @api.multi
    def suspend_service(self, service_profile):
        return False
        # raise NotImplementedError()

    @api.multi
    def remove_service(self, service_profile):
        return False
        # raise NotImplementedError()
