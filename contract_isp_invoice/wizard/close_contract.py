# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoirfaire-Linux Inc. (<www.savoirfairelinux.com>).
#    Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>)

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import calendar
import datetime
from openerp.osv import fields
from openerp.tools.translate import _
from openerp.addons.contract_isp.models.contract import date_interval
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class contract_isp_close(models.TransientModel):
    _name = 'contract.isp.close'

    @api.one
    def _get_account_id(self):
        if self._context.get('active_model', '') == 'account.analytic.account':
            contract_id = self._context.get('active_id')
            return contract_id
        return False

    account_id = fields.Many2one('account.analytic.account', 'Contract',
                                 default=lambda s: s._get_account_id())
    close_date = fields.Datetime('Close date', required=True,
                                 default=fields.datetime.now())
    close_reason = fields.Text('Reason')

    @api.multi
    def do_close(self):
        mail_mail_obj = self.env['mail.mail']
        account_analytic_line_obj = self.env['account.analytic.line']
        account_invoice_obj = self.env['account.invoice']
        account_analytic_account = self.env['account.analytic.account']\
            .browse(self._context.get('active_id', False))

        query = [
            ('partner_id', '=', account_analytic_account.partner_id.id),
            ('origin', '=', account_analytic_account.name)
        ]

        last_invoice_id = account_invoice_obj.search(query)
        if last_invoice_id:
            last_invoice = account_invoice_obj.browse(last_invoice_id[-1])
            if last_invoice.date_invoice > self.close_date:
                raise Warning(_('Error!'), _
                              ('Close date before last invoice date!'))

            amount_untaxed = last_invoice.amount_untaxed

            month_days = calendar.monthrange(int(self.close_date[:4]),
                                             int(self.close_date[5:7]))[1]

            used_days = month_days - int(self.close_date[8:10])
            ptx = (100 * used_days / month_days) / 100.0
            amount = amount_untaxed * ptx
            interval = date_interval(datetime.date(int(self.close_date[:4]),
                                                   int(self.close_date[5:7]),
                                                   int(self.close_date[8:10])),
                                     True)

            line = {
                'name': ' '.join([_('Credit refund'), interval]),
                'amount': amount,
                'account_id': account_analytic_account.id,
                'user_id': self.uid,
                'general_account_id': account_analytic_account.partner_id.
                property_account_receivable.id,
                'to_invoice': 1,
                'unit_amount': 1,
                'is_prorata': True,
                'date': self.close_date
            }
            account_analytic_line_obj.create(line)

        account_analytic_account.write({'close_date': self.close_date,
                                        'close_reason': self.close_reason})

        mail_template_obj = self.env['email.template']
        mail_template_id = self.env['ir.model.data'].\
            get_object_reference('contract_isp_invoice',
                                 'email_template_contract_isp_invoice_close')
        mail_id = mail_template_obj.send_mail(mail_template_id[1],
                                              account_analytic_account.id)
        mail_message = mail_mail_obj.browse(mail_id).mail_message_id
        mail_message.write({'type': 'email'})
        account_analytic_account.write({'state': 'close'})
        return {}
