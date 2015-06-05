# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
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

from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.tools import SUPERUSER_ID


def unique(values):
    if iter(values) is values:
        values = list(values)
    return len(values) == len(set(values))


class Contract(orm.Model):
    _inherit = 'account.analytic.account'

    def _get_has_unique_products(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            res[contract.id] = not unique(
                cs.product_id.default_code
                for cs in contract.contract_service_ids
                if cs.product_id.default_code
            )
        return res

    _columns = {
        'has_duplicate_products': fields.function(
            _get_has_unique_products,
            type="bool",
            store=False,
        ),
    }

    def _check_unique_products(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for contract in self.browse(cr, uid, ids, context=context):
            if contract.has_duplicate_products:
                raise orm.except_orm(
                    _("Validation Error"),
                    _("You are not allowed to have multiple identical "
                      "products in a contract, remove the inactive "
                      "duplicate services first."),
                )

    def _unlink_only_duplicates(self, cr, uid, ids, values, context=None):
        if "contract_service_ids" not in values:
            return

        cs_obj = self.pool["contract.service"]

        csi_vals = []
        for val in values["contract_service_ids"]:
            # Only handle unlinks
            if val[0] != 2:
                csi_vals.append(val)
                continue

            rm_cs = cs_obj.browse(cr, uid, val[1])
            if not rm_cs.is_duplicate:
                csi_vals.append(val)
                continue

            # Use super write to avoid infinite recursion
            # Write one at a time to avoid removing all duplicates
            super(Contract, self).write(cr, SUPERUSER_ID, ids,
                                        {'contract_service_ids': [val]},
                                        context=context)

        values["contract_service_ids"] = csi_vals
        return values

    def create(self, cr, uid, values, context=None):
        # Do it simple, check after creation
        res = super(Contract, self).create(cr, uid, values, context=context)
        self._check_unique_products(cr, uid, res)
        return res

    def write(self, cr, uid, ids, values, context=None):
        self._unlink_only_duplicates(cr, uid, ids, values, context=context)

        res = super(Contract, self).write(cr, uid, ids, values,
                                          context=context)
        if values.get("contract_service_ids"):
            self._check_unique_products(cr, uid, ids, context=context)
        return res


class ContractService(orm.Model):
    _inherit = 'contract.service'

    def _get_is_duplicate(self, cr, uid, ids, fields, arg, context):
        res = {}
        account_obj = self.pool["account.analytic.account"]
        account_ids = account_obj.search(
            cr, uid,
            [('contract_service_ids', 'in', ids)],
            context=context)
        for account in account_obj.browse(cr, uid, account_ids,
                                          context=context):
            codes = {}
            for cs in account.contract_service_ids:
                codes.setdefault(cs.product_id.default_code, []).append(cs.id)

            for key, vals in codes.iteritems():
                is_dup = (key and len(vals) > 1)
                for v in vals:
                    res[v] = is_dup

        return res

    _columns = {
        'is_duplicate': fields.function(_get_is_duplicate,
                                        type="bool", store=False),
    }

    def create(self, cr, uid, values, context=None):
        res = super(ContractService, self).create(cr, uid, values,
                                                  context=context)
        if "account_id" in values:
            self.pool["account.analytic.account"]._check_unique_products(
                cr, uid, values["account_id"], context=context)
        return res
