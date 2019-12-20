# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AgreementServiceProfile(models.Model):
    _inherit = 'agreement.serviceprofile'

    query_type = fields.Selection(
        [('domain', 'Query by Domain'),
         ('uid', 'Query by User')])
    query_parameter = fields.Char()
    last_cdr_sync = fields.Datetime("Last CDR Sync Date")

    @api.multi
    def import_cdr(self):
        """
        Get call data records: type (in, out, ...), number, seconds
        Filter only outbound calls, type==0
        Add billing Product, from number, using product map
        And Group by Product
        """
        def _get_product_map(product_line_ids):
            res = []
            for line in product_line_ids:
                regexp = re.compile(line.pattern)
                res.append(regexp, line.name)
            return res

        def _phone_to_product(outgoing_number, product_map):
            for regexp, product in product_map:
                match = bool(regexp.match(outgoing_number))
                if match:
                    return product
            return product  # If not found returns last Product

        phone_to_rate = self.env['phone.rate'].get_rate_from_phonenumber

        # We could be duplicating Analytic Lines
        # if same query_param is in several service profiles
        # Alternative - update Last CDR date
        # for all Service Profles with this query_param
        for service in self:
            backend = service.equipment_id.backend_id
            product_map = _get_product_map(backend.product_line_ids)
            date_from = service.last_cdr_sync or datetime(2000, 1, 1)
            date_to = datetime.combine(  # Up to today 00:00h
                fields.Date.today(),
                datetime.min.time())

            # Group Data Lines by Product
            # Prodict may have several patterns assigned,
            # and be used in mor than one line
            products_data = {
                p: [] for p in backend.product_line_ids.mapped('name')}
            cdr_data = backend.api_get_cdr_data(
                service,
                date_from,
                date_to)
            for line in cdr_data or []:
                call_type = {
                    '0': 'outbound',
                    '1': 'inbound',
                    '2': 'missed',
                    '3': 'on-net',
                    }.get(line['type'])
                dialed_number = line['orig_req_user']
                # duration = line['duration']
                if call_type == 'outbound':
                    product = _phone_to_product(dialed_number, product_map)
                    if product.is_international_call:
                        line['phone_rate'] = phone_to_rate(dialed_number)
                    products_data[product].append(line)

            # Create Analytic Line for each Product
            analytic = service.agreement_id.analytic_account_id
            if not analytic:
                raise UserError(_(
                    'Analytic Account is not found in database.'))
            AnalyticLine = self.env["account.analytic.line"]
            for product, lines in products_data.items():
                if lines:
                    from pprint import pprint; pprint(lines)  # TODO remove
                    calls = len(lines)
                    duration_secs = sum(int(x['duration']) for x in lines)
                    duration_mins = duration_secs // 60  # Truncates seconds
                    amount = (product.is_international_call and sum(
                        x.get('phone_rate').rate
                        * int(x.get('duration', '0')) / 60.0
                        for x in lines))
                    uom = self.env.ref(
                        'connector_equipment_import_cdr.product_uom_min')
                    name = 'CDR for %s' % fields.Datetime.to_string(date_to)
                    ref = "# Calls: %d" % (calls,)
                    data = {
                        "name": name,
                        "account_id": analytic.id,
                        "date": fields.Date.today(),
                        "amount": amount or 0,
                        "ref": ref,
                        "partner_id": service.partner_id.id,
                        "unit_amount": duration_mins,
                        "product_id": product.id,
                        "product_uom_id": uom.id,
                    }
                    print('========\nAnalytic Line', data)  # TODO: remove
                    AnalyticLine.create(data)
            service.last_cdr_sync = date_to

    @api.multi
    def button_import_cdr(self):
        self.import_cdr()

    @api.model
    def cron_import_cdr(self):
        serviceprofiles = self.search(
            [('query_type', '!=', False),
             ('query_parameter', '!=', False),
             ('equipment_id.backend_id', '!=', False)])
        serviceprofiles.import_cdr()
