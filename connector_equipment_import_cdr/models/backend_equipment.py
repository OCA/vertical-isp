# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from datetime import datetime
import requests


class BackendEquipment(models.Model):
    _inherit = 'backend.equipment'

    product_line_ids = fields.One2many(
        'backend.equipment.product_line',
        'backend_id', string="Products")
    sync_schedule = fields.Selection(
        [('all_service', 'All Service Profiles Every Day')], 'Sync Schedule')

    @api.multi
    def button_import_cdr(self):
        for rec in self:
            rec.import_cdr(serviceprofile_ids=None)

    def import_cdr(self, serviceprofile_ids=None):
        # WIP
        serviceprofile_obj = self.env['agreement.serviceprofile']
        for rec in self:
            if not serviceprofile_ids:
                serviceprofile_rec = serviceprofile_obj.search(
                    [('domain', '!=', False),
                     ('equipment_id.backend_id', '=', rec.id)])
                for service in serviceprofile_rec:
                    url_path = rec.host
                    token_value = {
                        'grant_type': 'password',
                        'client_id': rec.client,
                        'client_secret': rec.client_secret,
                        'username': rec.user,
                        'password': rec.password,
                    }
                    request_data = requests.get(
                        url_path, params=token_value,
                        headers={'Content-Type': 'application/json'})
                    if serviceprofile_rec:
                        service.last_cdr_sync = datetime.today()
