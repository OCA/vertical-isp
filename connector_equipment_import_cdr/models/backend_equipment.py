# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from datetime import datetime


class BackendEquipment(models.Model):
    _inherit = 'backend.equipment'

    product_line_ids = fields.One2many(
        'backend.equipment.product_line',
        'backend_id', string="Products")
    sync_schedule = fields.Selection(
        [('all_service', 'All Service Profiles Every Day')], 'Sync Schedule')

    def import_cdr(self, serviceprofile_ids=None):
        # serviceprofile_obj = self.env['agreement.serviceprofile']
        # for rec in self:
        #     if not serviceprofile_ids:
        #         serviceprofile_rec = serviceprofile_obj.search(
        #             [('domain', '!=', False)])
        #     if serviceprofile_rec:
        #         serviceprofile_rec.last_cdr_sync = datetime.today()
        return True
