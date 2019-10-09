# Copyright (C) 2018 - TODAY, Pavlov Media
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'
    _description = 'Maintenance Equipment'

    @api.multi
    def add_service(self, service_profile):
        return True

    @api.multi
    def update_service(self, service_profile):
        return True

    @api.multi
    def activate_service(self, service_profile):
        return True

    @api.multi
    def suspend_service(self, service_profile):
        return True

    @api.multi
    def remove_service(self, service_profile):
        return True
