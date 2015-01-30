# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoir-faire Linux (<http://www.savoirfairelinux.com>).
#
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
from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.addons.contract_isp.contract import date_interval, format_interval


class contract_isp_close(orm.TransientModel):
    _name = 'contract.isp.close'

    def _get_account_id(self, cr, uid, context=None):
        if context.get('active_model', '') == 'account.analytic.account':
            contract_id = context.get('active_id')
            return contract_id
        return None

    _columns = {
        'account_id': fields.many2one('account.analytic.account', 'Contract'),
        'close_date': fields.datetime('Close date', required=True),
        'close_reason': fields.text('Reason')
    }

    _defaults = {
        'account_id': lambda s, cr, uid, ctx: s._get_account_id(cr, uid, ctx),
        'close_date': fields.datetime.now
    }

    def do_close(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        mail_mail_obj = self.pool.get('mail.mail')
        account_analytic_line_obj = self.pool.get('account.analytic.line')
        account_invoice_obj = self.pool.get('account.invoice')
        contract = self.browse(cr, uid, ids, context=context)[0].account_id

        query = [
            ('partner_id', '=', contract.partner_id.id),
            ('origin', '=', contract.name)
        ]

        last_invoice_id = account_invoice_obj.search(cr, uid, query,
                                                     context=context)
        if last_invoice_id:
            last_invoice = account_invoice_obj.browse(cr, uid,
                                                      last_invoice_id[-1],
                                                      context=context)
            if last_invoice.date_invoice > wizard.close_date:
                raise orm.except_orm(_('Error!'),
                                     _('Close date before last invoice date!'))

            amount_untaxed = last_invoice.amount_untaxed

            month_days = calendar.monthrange(int(wizard.close_date[:4]),
                                             int(wizard.close_date[5:7]))[1]

            used_days = month_days - int(wizard.close_date[8:10])
            ptx = (100 * used_days / month_days) / 100.0
            amount = amount_untaxed * ptx
            start_date, end_date = date_interval(
                datetime.date(int(wizard.close_date[:4]),
                              int(wizard.close_date[5:7]),
                              int(wizard.close_date[8:10])),
                True)
            interval = format_interval(start_date, end_date)

            line = {
                'name': ' '.join([_('Credit refund'), interval]),
                'amount': amount,
                'account_id': contract.id,
                'user_id': uid,
                'general_account_id': (
                    contract.partner_id.property_account_receivable.id),
                'to_invoice': 1,
                'unit_amount': 1,
                'is_prorata': True,
                'date': wizard.close_date
            }
            account_analytic_line_obj.create(cr, uid, line, context=context)

        contract.write({'close_date': wizard.close_date,
                        'close_reason': wizard.close_reason})

        mail_template_obj = self.pool.get('email.template')
        mail_template_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'contract_isp_invoice',
            'email_template_contract_isp_invoice_close')
        mail_id = mail_template_obj.send_mail(cr, uid, mail_template_id[1],
                                              contract.id, context=context)
        mail_message = mail_mail_obj.browse(
            cr, uid, mail_id, context=context).mail_message_id
        mail_message.write({'type': 'email'})
        contract.write({'state': 'close'})
        return {}
