# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from datetime import datetime, timedelta
import requests
import json


class BackendEquipment(models.Model):
    _inherit = 'backend.equipment'

    product_line_ids = fields.One2many(
        'backend.equipment.product_line',
        'backend_id', string="Products")
    sync_schedule = fields.Selection(
        [('all_service', 'All Service Profiles Every Day')], 'Sync Schedule')

    @api.multi
    def api_url_build(self, endpoint):
        """
        Given an endpoint,
        return full Netsapiens API URL for the endpoint
        """
        self.ensure_one()
        url = self.host
        if not url.startswith('http'):
            url = 'https://' + url
        if url.endswith('/'):
            url = url[:-1]
        if self.port:
            url = url + self.port
        if endpoint:
            url = url + endpoint
        return url

    @api.multi
    def api_generate_access_token(self):
        """
        Login to Netsapiens and
        return the access token
        """
        self.ensure_one()
        backend = self
        token_value = {
            'grant_type': 'password',
            'client_id': backend.client,
            'client_secret': backend.client_secret,
            'username': backend.user,
            'password': backend.password,
        }
        url_path = self.api_url_build('/ns-api/oauth2/token/?')
        request_data = requests.get(
            url_path,
            params=token_value,
            headers={'Content-Type': 'application/json'})
        if request_data.status_code == 200:
            request_data = json.loads(request_data.text)
            token = request_data.get('access_token')
            return token
        # TODO else Raise an error if not successful?

    @api.model
    def api_get_domain_cdr_data(self, service, from_date=None, to_date=None):
        """
        Given a Service Profile, call the API to get CRD data.
        Returns a dict with the retrieved data.
        """
        backend = service.equipment_id.backend_id
        # TODO convert dates to context timezone!
        today_date = datetime.today()
        yesterday = (today_date - timedelta(days=1)).date()
        token = backend.api_generate_access_token()
        token_value = {
            'object': 'cdr2',
            'action': 'read',
            'start_date': service.last_cdr_sync or '2000-01-01',
            'end_date': yesterday,
            'domain': service.domain,
            'format': 'json'
        }
        url_path = self._api_url_build('/ns-api/?')
        domain_data = requests.post(
            url_path,
            params=token_value,
            headers={'Authorization': 'Bearer' + ' ' + token})
        if domain_data.status_code == 200:
            domain_data = json.loads(domain_data.text)
            return domain_data
