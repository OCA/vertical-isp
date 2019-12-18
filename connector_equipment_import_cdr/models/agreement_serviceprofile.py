# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AgreementServiceProfile(models.Model):
    _inherit = 'agreement.serviceprofile'

    domain = fields.Char()
    last_cdr_sync = fields.Date("Last CDR Sync Date")

    @api.multi
    def get_billing_day(self):
        self.ensure_one()
        start_date = self.agreement_id.start_date
        billing_date = start_date + timedelta(days=1)
        return billing_date.day

    @api.multi
    def import_cdr(self):
        """
        Get call data for domain: type (in, out, ...), number, seconds
        Filter only outbound calls, type==0
        Add billing Product, from number, using product map
        And Group by Product
        """
        def phone_to_product(outgoing_number, product_map):
            for line in product_map:
                product = line.name
                match = outgoing_number == line.pattern  # TODO apply RegEx
                if match:
                    return product
            return product

        phone_to_rate = self.env['phone.rate'].get_rate_from_phonenumber
        # TODO loop should be by domain?
        # We could be duplicating if same domain is in several service profiles
        for service in self:
            # Group Data Lines by Product
            backend = service.equipment_id.backend_id
            product_map = backend.product_line_ids
            domain_data = backend.api_get_domain_cdr_data(service)
            products_data = {line.name: [] for line in product_map}
            for line in domain_data:
                call_type = {
                    '0': 'outbound',
                    '1': 'inbound',
                    '2': 'missed',
                    '3': 'on-net',
                    }.get(line['type'])
                dialed_number = line['orig_req_user']
                # duration = line['duration']
                if call_type == 'outbound':
                    product = phone_to_product(
                        dialed_number, product_map)
                    if product.is_international_call:
                        line['phone_rate'] = phone_to_rate(dialed_number)
                    products_data[product].append(line)
            # Create Analytic Line for each Product
            analytic = service.agreement_id.analytic_account_id
            if not analytic:
                raise UserError(_(
                    'Analytic Account is not found in database.'))
            AnalyticLine = self.env["account.analytic.line"]
            import pudb; pu.db
            for product, lines in products_data.items():
                if lines:
                    calls = len(lines)
                    duration_secs = sum(int(x['duration']) for x in lines)
                    duration_mins = duration_secs // 60  # TODO rounding rule
                    # start = min(x['time_start'] for x in lines)
                    # end = max(x['time_release'] for x in lines)
                    amount = (product.is_international_call and sum(
                        x.get('phone_rate').rate
                        * int(x.get('duration', '0')) / 60.0
                        for x in lines))
                    uom = self.env.ref(  # TODO Verify it is default data
                        'uom.product_uom_unit')
                        #'connector_equipment_import_cdr.product_uom_min')
                    # billing_day = service.get_billling_day()
                    # TODO name = 'YYYYMM'
                    # name = start + ' to ' + end
                    name = "YYYYMM"  # TODO
                    ref = "# Calls: %d" % (calls,)

                    AnalyticLine.create({
                        "name": name,
                        "account_id": analytic.id,
                        "date": date.today(),
                        "amount": amount or 0,
                        "ref": ref,
                        "partner_id": service.partner_id.id,
                        "unit_amount": duration_mins,
                        "product_id": product.id,
                        "product_uom_id": uom.id,
                    })
            service.last_cdr_sync = date.today()

    @api.multi
    def button_import_cdr(self):
        self.import_cdr()

    @api.model
    def cron_import_cdr(self):
        serviceprofiles = self.search(
            [('domain', '!=', False),
             ('equipment_id.backend_id', '!=', False)])
        serviceprofiles.import_cdr()
