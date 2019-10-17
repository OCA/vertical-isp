# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    international_call_service = fields.Boolean("International Call Service",
                                                default=False)
    phone_rate_ids = fields.Many2many('phone.rate',
                                      string="Phone Rates",
                                      compute='_compute_phone_rate_ids')
    phone_rate_count = fields.Integer(string="Phone Rates",
                                      compute='_compute_phone_rate_ids')

    @api.multi
    def _compute_phone_rate_ids(self):
        for prod_id in self:
            rates = self.env['phone.rate'].search([])
            prod_id.phone_rate_count = len(rates)
            prod_id.phone_rate_ids = rates.ids

    @api.multi
    def action_view_phone_rates(self):
        for prod_id in self:
            action = self.env.\
                ref('base_phone_rate.action_phone_rate').read()[0]
            rates = self.env['phone.rate'].search([])
            if len(rates) == 1:
                action['views'] = [
                    (self.env.ref('base_phone_rate.phone_rate_form_view').id,
                     'form')]
                action['res_id'] = rates.id
            else:
                action['domain'] = [('id', 'in', rates.ids)]
            return action
