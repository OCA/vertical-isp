# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Savoirfaire-Linux Inc. (<www.savoirfairelinux.com>).
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

from openerp.tools import SUPERUSER_ID
from openerp.osv import orm, fields
from openerp.tools.translate import _


class contract_service_configurator_line(orm.TransientModel):
    _name = 'contract.service.configurator.line'

    _columns = {
        'name': fields.char('Name'),
        'product_id': fields.many2one('product.product', 'Product'),
        'configurator_id': fields.many2one('contract.service.configurator',
                                           'Package Configurator'),
        'parent_id': fields.many2one('contract.service.configurator.line',
                                     'Parent'),
        'serial': fields.many2one('stock.production.lot', 'Serial Number'),
        'message': fields.text('Message'),
        'handle_dependency': fields.boolean('Handle dependencies'),
        'stock_move_id': fields.many2one('stock.move', 'Stock Move'),
        'state': fields.selection((('draft', _('Added')),
                                   ('message', _('Information')),
                                   ('serial', _('Select serial number')),
                                   ('stock', ('No Stock')),
                                   ('done', _('Done'))), 'State'),
    }

    _defaults = {
        'state': 'draft'
    }

    def router(self, cr, uid, ids, data=None, context=None):
        stock_move_id = None
        if isinstance(ids, list):
            ids = ids[0]
        line = self.browse(cr, uid, ids, context=context)
        line.write({'state': 'done', 'stock_move_id': stock_move_id})

        return line.configurator_id.router(data={})

    def onchange_product_id(self, cr, uid, ids, product_id, context):
        ret = {}
        product_product_obj = self.pool.get('product.product')

        description = product_product_obj.browse(cr, uid, product_id,
                                                 context=context).description
        if description:
            ret['warning'] = {
                'title': _('Information'),
                'message': description,
            }
        return ret


class contract_service_configurator_dependency_line(orm.TransientModel):
    _name = 'contract.service.configurator.dependency.line'
    _inherit = 'contract.service.configurator.line'


class contract_service_configurator(orm.TransientModel):
    _name = 'contract.service.configurator'

    def _get_default_category(self, cr, uid, context=None):
        res_company_obj = self.pool.get("res.company")
        company_id = res_company_obj._company_default_get(cr, uid, context)
        res_company = res_company_obj.browse(cr, uid, company_id,
                                             context=context)
        return res_company.default_product_category and \
            res_company.default_product_category.id

    def _get_is_level2(self, cr, uid, context=None):
        ir_model_data_obj = self.pool.get('ir.model.data')
        res_user = self.pool.get('res.users').browse(
            cr, uid, uid, context={})
        group_agent_n2_id = ir_model_data_obj.get_object_reference(
            cr, uid, 'contract_isp', 'group_isp_agent2')[1]

        groups_id = [i.id for i in res_user.groups_id]
        if group_agent_n2_id not in groups_id:
            return False
        else:
            return True

    _columns = {
        'contract_id': fields.many2one('account.analytic.account', 'Contract'),
        'state': fields.selection((('draft', _('Start')),
                                   ('product', _('Select product')),
                                   ('dependency', _('Select components')),
                                   ('done', _('Done'))), 'State'),
        'line_ids': fields.one2many('contract.service.configurator.line',
                                    'configurator_id',
                                    'Line'),
        'current_product_id': fields.many2one('product.product',
                                              'Add Product'),
        'dependency_ids': fields.many2many(
            'contract.service.configurator.dependency.line',
            'contract_service_configurator_dependency_rel',
            'configurator_id',
            'dependency_id',
            'Dependencies'),
        'root_category_id': fields.many2one('product.category', 'Category'),
        'product_category_id': fields.many2one('product.category', 'Category'),
        'is_level2': fields.boolean('Is level 2')
    }

    _defaults = {
        'state': 'draft',
        'product_category_id': _get_default_category,
        'root_category_id': _get_default_category,
        'is_level2': _get_is_level2,
    }

    def onchange_product_category_id(self, cr, uid, ids,
                                     product_category_id, is_level2):
        domain = [
            ('categ_id', 'child_of', product_category_id),
            ('sale_ok', '=', True),
        ]
        ret = {'domain': {'current_product_id': None}}

        if not is_level2:
            domain.append(('list_price', '>=', 0))

        ret['domain']['current_product_id'] = domain

        return ret

    def do_next(self, cr, uid, ids, context=None):
        contract_service_configurator_line_obj = self.pool[
            'contract.service.configurator.line']
        csc_dependency_line_obj = self.pool[
            'contract.service.configurator.dependency.line']
        product_product_obj = self.pool.get('product.product')

        wizard = self.browse(cr, uid, ids[0], context=context)

        for line in wizard.dependency_ids:
            if line.configurator_id.id == ids[0]:
                state = 'done'

                l = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'configurator_id': wizard.id,
                    'handle_dependency': (
                        line.product_id.dependency_ids and True or False
                    ),
                    'message': line.product_id.description,
                    'state': state
                }
                contract_service_configurator_line_obj.create(
                    cr, uid, l, context=context)

        query = [('configurator_id', '=', wizard.id)]
        ids_to_unlink = csc_dependency_line_obj.search(cr,
                                                       uid,
                                                       query,
                                                       context=context)
        if ids_to_unlink:
            csc_dependency_line_obj.unlink(cr, uid,
                                           ids_to_unlink,
                                           context)

        loop_deps = False
        for line in wizard.line_ids:
            if line.handle_dependency:
                loop_deps = True
                for dep in line.product_id.dependency_ids:
                    if dep.type == 'product':
                        if not wizard.is_level2 and dep.list_price < 0:
                            continue

                        state = 'done'

                        wl = {
                            'name': dep.product_id.name,
                            'product_id': dep.product_id.id,
                            'configurator_id': wizard.id,
                            'parent_id': line.id,
                            'message': line.product_id.description,
                            'state': state
                        }
                        new_dep = csc_dependency_line_obj.create(
                            cr, uid, wl, context=context)

                        if dep.auto:
                            wizard.write({'dependency_ids': [(4, new_dep)]})

                    elif dep.type == 'category':
                        query = [('categ_id', 'child_of', dep.category_id.id)]
                        product_ids = product_product_obj.search(
                            cr, uid, query,
                            context=context)
                        for product in product_product_obj.browse(
                                cr, uid, product_ids,
                                context=context):
                            if not wizard.is_level2 and dep.list_price < 0:
                                continue

                            state = 'done'

                            wl = {
                                'name': product.name,
                                'product_id': product.id,
                                'configurator_id': wizard.id,
                                'parent_id': line.id,
                                'message': product.description,
                                'state': state
                            }
                            csc_dependency_line_obj.create(cr, uid, wl,
                                                           context=context)
                line.write({'handle_dependency': False})
                break

        if loop_deps:
            record = {
                'state': 'dependency',
            }
            wizard.write(record)
            return self.router(cr, uid, ids, {}, context=context)

        else:
            record = {
                'state': 'product',
                'current_product_id': None,
                'dependency_ids': [(5)],
            }
            wizard.write(record)

            query = [('configurator_id', '=', wizard.id)]
            ids_to_unlink = csc_dependency_line_obj.search(cr, uid, query,
                                                           context=context)
            return self.router(cr, uid, ids, {}, context=context)

    def do_add_current_product_id(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        deps = 0
        wizard = self.browse(cr, uid, ids[0], context=context)
        contract_service_configurator_line_obj = self.pool.get(
            'contract.service.configurator.line')
        csc_dependency_line_obj = self.pool.get(
            'contract.service.configurator.dependency.line')
        product_product_obj = self.pool.get('product.product')

        if wizard.current_product_id:
            state = 'done'

            record = {
                'name': wizard.current_product_id.name,
                'product_id': wizard.current_product_id.id,
                'configurator_id': wizard.id,
                'message': wizard.current_product_id.description,
                'state': state
            }
            new_line = contract_service_configurator_line_obj.create(
                cr, uid, record, context=context)

            for dep in contract_service_configurator_line_obj.browse(
                    cr, uid, new_line,
                    context=context).product_id.dependency_ids:

                if dep.type == 'product':
                    if not wizard.is_level2 and dep.product_id.list_price < 0:
                        continue

                    state = 'done'

                    deps += 1
                    wl = {
                        'name': dep.product_id.name,
                        'product_id': dep.product_id.id,
                        'configurator_id': wizard.id,
                        'parent_id': new_line,
                        'message': dep.product_id.description,
                        'state': state
                    }
                    new_dep = csc_dependency_line_obj.create(cr, uid, wl,
                                                             context=context)

                    if dep.auto:
                        wizard.write({'dependency_ids': [(4, new_dep)]})

                elif dep.type == 'category':
                    query = [('categ_id', 'child_of', dep.category_id.id)]
                    product_ids = product_product_obj.search(cr, uid, query,
                                                             context=context)
                    for product in product_product_obj.browse(cr, uid,
                                                              product_ids,
                                                              context=context):
                        if (not wizard.is_level2 and
                                dep.product_id.list_price < 0):
                            continue

                        state = 'done'

                        deps += 1
                        record = {
                            'name': product.name,
                            'product_id': product.id,
                            'configurator_id': wizard.id,
                            'parent_id': new_line,
                            'message': product.description,
                            'state': state
                        }
                        csc_dependency_line_obj.create(
                            cr, uid, record, context=context)

            record = {
                'current_product_id': None,
                'product_category_id': self._get_default_category(
                    cr, uid, context=context),
                'state': deps and 'dependency' or 'product'
            }

            wizard.write(record)

            return wizard.router({})
        raise orm.except_orm(_('Error'), _('Product not found!'))

    def do_done(self, cr, uid, ids, context=None):
        contract_service_obj = self.pool.get('contract.service')
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        wizard = self.browse(cr, uid, ids[0], context=context)
        for line in wizard.line_ids:
            l = {
                'name': line.serial and line.serial.name or '',
                'account_id': wizard.contract_id.id,
                'product_id': line.product_id.id,
                'category_id': line.product_id.categ_id.id,
                'analytic_line_type': line.product_id.analytic_line_type,
                'require_activation': line.product_id.require_activation
            }
            l.update(
                contract_service_obj.on_change_product_id(
                    cr, uid, None, l["product_id"],
                ).get("value", {})
            )
            contract_service_obj.create(cr, uid, l, context=context)

            if line.product_id.type == 'product' and line.stock_move_id:
                line.write({'stock_move_id': None})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.account',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': wizard.contract_id.id,
            'context': context
        }

    def router(self, cr, uid, ids, data=None, context=None):
        if isinstance(ids, list):
            ids = ids[0]

        return {
            'name': _('Package Configurator'),
            'type': 'ir.actions.act_window',
            'res_model': 'contract.service.configurator',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': ids,
            'nodestroy': True,
            'context': context
        }


class ManageEquipmentWizard(orm.TransientModel):
    _name = 'contract.service.equipment.manage'

    def _get_products(self, contract_obj):
        prods = {
            'products_all': [],
            'products_with_serial': [],
            'products_no_serial': [],
        }
        for service in contract_obj.contract_service_ids:
            product = service.product_id
            if not product.type == "product":
                continue

            prods["products_all"].append(product.id)
            if service.prodlot_id:
                prods["products_with_serial"].append(product.id)
            else:
                prods["products_no_serial"].append(product.id)

        return prods

    def _get_contract_products(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for wiz in self.browse(cr, uid, ids, context=context):
            res[wiz.id] = self._get_products(wiz.contract_id)

        return res

    _columns = {
        'products_all': fields.function(
            _get_contract_products,
            type='many2many', obj='product.product',
            method=True, multi="products"),
        'products_with_serial': fields.function(
            _get_contract_products,
            type='many2many', obj='product.product',
            method=True, multi="products"),
        'products_no_serial': fields.function(
            _get_contract_products,
            type='many2many', obj='product.product',
            method=True, multi="products"),
        'prodlot_id': fields.many2one('stock.production.lot', 'Serial Number'),

        'contract_id': fields.many2one('account.analytic.account', 'Contract'),
        'product_id': fields.many2one(
            'product.product', 'Selected Product', required=True),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(ManageEquipmentWizard, self).default_get(
            cr, uid, fields_list, context=context)

        if res.get("contract_id"):
            contract = self.pool["account.analytic.account"].browse(
                cr, uid, res["contract_id"], context=context)
            res.update(self._get_products(contract))

        return res

    def restrict_available_prodlots(self, cr, uid, ids, product_id):
        ret = {'domain': {'prodlot_id': False}}
        stock_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'stock', 'stock_location_stock')[1]

        m_inv = self.pool["report.stock.inventory"]
        lots = m_inv.read_group(
            cr, SUPERUSER_ID,  # Make sure we have access
            [
                ('product_id', '=', product_id),
                ('location_id', '=', stock_id),
                ('state', 'in', ('done', 'assigned', 'confirmed', 'waiting')),
            ],
            fields=["product_id", "location_id", "prodlot_id", "product_qty"],
            groupby=["prodlot_id"],
        )
        available_lots = [
            group['prodlot_id'][0]
            for group in lots
            if group["product_qty"] > 0 and group["prodlot_id"]
        ]

        ret['domain']['prodlot_id'] = [('id', 'in', available_lots)]
        return ret

    def _do_move(self, cr, uid, move, context):
        stock_move_obj = self.pool["stock.move"]
        stock_move_id = stock_move_obj.create(
            cr, uid, move, context=context)
        stock_move_obj.action_confirm(
            cr, uid, [stock_move_id], context=context)
        stock_move_obj.action_done(
            cr, uid, [stock_move_id], context=context)

    def _move_to_stock(self, cr, uid,
                       contract_br, product_br, serial_id,
                       context=None):
        location_dest_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'stock', 'stock_location_stock')[1]
        location_id = contract_br.partner_id.property_stock_customer.id
        move = {
            'name': product_br.name or '',
            'product_id': product_br.id,
            'product_uom': product_br.uom_id and product_br.uom_id.id or None,
            'prodlot_id': serial_id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'partner_id': contract_br.partner_id.id,
            'type': 'out'
        }
        self._do_move(cr, uid, move, context)

    def _move_to_client(self, cr, uid,
                        contract_br, product_br, serial_id,
                        context=None):
        location_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'stock', 'stock_location_stock')[1]
        location_dest_id = contract_br.partner_id.property_stock_customer.id
        move = {
            'name': product_br.name or '',
            'product_id': product_br.id,
            'product_uom': product_br.uom_id and product_br.uom_id.id or None,
            'prodlot_id': serial_id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'partner_id': contract_br.partner_id.id,
            'type': 'out'
        }
        self._do_move(cr, uid, move, context)

    def _move_to_scrap(self, cr, uid,
                       contract_br, product_br, serial_id,
                       context=None):
        location_dest_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'stock', 'stock_location_scrapped')[1]
        location_id = contract_br.partner_id.property_stock_customer.id
        move = {
            'name': product_br.name or '',
            'product_id': product_br.id,
            'product_uom': product_br.uom_id and product_br.uom_id.id or None,
            'prodlot_id': serial_id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'partner_id': contract_br.partner_id.id,
            'type': 'out'
        }
        self._do_move(cr, uid, move, context)

    def do_reserve(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context=context)
        contract_br = wizard.contract_id
        prodlot_id = wizard.prodlot_id.id
        for service in contract_br.contract_service_ids:
            if all((service.product_id.id == wizard.product_id.id,
                    not service.prodlot_id,
                    )):
                product_br = service.product_id
                service.write({'prodlot_id': prodlot_id,
                               'name': wizard.prodlot_id.name})
                break
        else:
            raise orm.except_orm(
                _('Error'), _('Product without serial not found'))

        self._move_to_client(cr, uid,
                             contract_br, product_br, prodlot_id,
                             context=context)
        contract_br.message_post(
            _("Reserved {product} serial {serial}").format(
                product=product_br.name,
                serial=wizard.prodlot_id.name,
            ),
            context=context,
        )
        return {}

    def do_exchange(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context=context)
        contract_br = wizard.contract_id
        prodlot_id = wizard.prodlot_id.id
        for service in contract_br.contract_service_ids:
            if all((service.product_id.id == wizard.product_id.id,
                    service.prodlot_id,
                    )):
                product_br = service.product_id
                previous_lot = service.prodlot_id.id
                previous_lot_name = service.prodlot_id.name
                service.write({'prodlot_id': prodlot_id,
                               'name': wizard.prodlot_id.name})
                break
        else:
            raise orm.except_orm(
                _('Error'), _('Product with serial not found'))

        self._move_to_scrap(cr, uid,
                            contract_br, product_br, previous_lot,
                            context=context)
        self._move_to_client(cr, uid,
                             contract_br, product_br, prodlot_id,
                             context=context)
        contract_br.message_post(
            _("Exchanged {product} serial {old} for {serial}").format(
                product=product_br.name,
                serial=wizard.prodlot_id.name,
                old=previous_lot_name,
            ),
            context=context,
        )
        return {}

    def do_return(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context=context)
        contract_br = wizard.contract_id
        for service in contract_br.contract_service_ids:
            if all((service.product_id.id == wizard.product_id.id,
                    service.prodlot_id,
                    )):
                product_br = service.product_id
                previous_lot = service.prodlot_id.id
                previous_lot_name = service.prodlot_id.name
                service.write({'prodlot_id': False,
                               'name': ''})
                break
        else:
            raise orm.except_orm(
                _('Error'), _('Product with serial not found'))

        self._move_to_stock(cr, uid,
                            contract_br, product_br, previous_lot,
                            context=context)
        contract_br.message_post(
            _("Returned {product} serial {old}").format(
                product=product_br.name,
                old=previous_lot_name,
            ),
            context=context,
        )
        return {}
