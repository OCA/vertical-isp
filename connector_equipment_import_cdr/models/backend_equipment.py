# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import Warning
import requests
import json


class BackendEquipment(models.Model):
    _inherit = 'backend.equipment'

    product_line_ids = fields.One2many(
        'backend.equipment.product_line',
        'backend_id', string="Products")
    sync_schedule = fields.Selection(
        [('all_service', 'All Service Profiles Every Day')], 'Sync Schedule')

    @api.model
    def generate_access_token(self, backend):
        token = False
        if backend:
            token_value = {
                'grant_type': 'password',
                'client_id': backend.client,
                'client_secret': backend.client_secret,
                'username': backend.user,
                'password': backend.password,
            }
            url_path = self.url_build('/ns-api/oauth2/token/?')
            request_data = requests.get(
                url_path, params=token_value,
                headers={'Content-Type': 'application/json'})
            if request_data.status_code == 200:
                request_data = json.loads(request_data.text)
                token = request_data.get('access_token')
        return token

    @api.model
    def url_build(self, endpoint):
        url = self.host
        if endpoint:
            url = url + endpoint
        return url

    @api.multi
    def button_import_cdr(self):
        for rec in self:
            rec.import_cdr(serviceprofile_ids=None)

    def import_cdr(self, serviceprofile_ids=None):
        serviceprofile_obj = self.env['agreement.serviceprofile']
        analytic_account_obj = self.env["account.analytic.account"]
        analytic_line_obj = self.env["account.analytic.line"]
        today_date = datetime.today()
        yesterday = (today_date - timedelta(days=1)).date()
        for rec in self:
            if not serviceprofile_ids:
                serviceprofile_rec = serviceprofile_obj.search(
                    [('domain', '!=', False),
                     ('equipment_id.backend_id', '=', rec.id)])
            else:
                serviceprofile_rec = serviceprofile_ids
            for service in serviceprofile_rec:
                token = rec.generate_access_token(
                    service.equipment_id.backend_id)
                token_value = {
                    'object': 'cdr2',
                    'action': 'read',
                    'start_date': service.last_cdr_sync or '2000-01-01',
                    'end_date': yesterday,
                    'domain': service.domain,
                    'format': 'json'
                }
                url_path = self.url_build('/ns-api/?')
                domain_data = requests.post(
                    url_path, params=token_value,
                    headers={'Authorization': 'Bearer' + ' ' + token})
                if domain_data.status_code == 200:
                    domain_data = json.loads(domain_data.text)
                    for data in domain_data:
                        analytic = analytic_account_obj.search([
                            ('name', "=", data.get('domain'))])
                        product_uom_unit = self.env.ref(
                            'connector_equipment_import_cdr.product_uom_min')
                        # Todo (logic?)
                        if data.get('type') == 1:
                            product = self.env.ref(
                                'connector_equipment_import_cdr.demo_call_product_product_1')
                        else:
                            product = self.env.ref(
                                'connector_equipment_import_cdr.demo_call_product_product_2')
                        if analytic:
                            analytic_line_obj.create({
                                "name": 'Demo',  # Todo (logic?)
                                "amount": 1.0,  # Todo (logic?)
                                "account_id": analytic.id,
                                "date": today_date.date(),
                                "unit_amount": float(data.get('duration')),
                                "product_id": product.id,  # Todo (logic?)
                                "product_uom_id": product_uom_unit.id,
                            })
                            if serviceprofile_rec:
                                service.last_cdr_sync = today_date.date()
                        else:
                            raise Warning(_('Analytic Account is not found in database.'))
