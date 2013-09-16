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

from openerp.osv import orm, fields
from openerp.tools.translate import _


class contract_service_configurator_line(orm.TransientModel):
    _name = 'contract.service.configurator.line'

    #def _get_stock_production_lot_available(self, cr, uid, )
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
        if isinstance(ids, list):
            ids = ids[0]
        line = self.browse(cr, uid, ids, context=context)
        if line.state == 'message':
            if line.product_id.type == 'product' and line.product_id.qty_available > 0.0:
                state = 'serial'
            else:
                state = 'stock'
        elif line.state in ('serial', 'stock'):
            state = 'done'

        line.write({'state': state})

        return line.configurator_id.router(data={})

    def onchange_product_id(self, cr, uid, ids, product_id, context):
        ret = {}
        product_product_obj = self.pool.get('product.product')

        if product_product_obj.browse(cr, uid, product_id, context).description:
            ret['warning'] = {
                'title': _('Information'),
                'message': product_product_obj.browse(cr, uid, product_id, context).description
            }
        return ret


class contract_service_configurator_dependency_line(orm.TransientModel):
    _name = 'contract.service.configurator.dependency.line'
    _inherit = 'contract.service.configurator.line'


class contract_service_serial(orm.TransientModel):
    _name = 'contract.service.serial'

    _columns = {
        'name': fields.char('Serial Number'),
        'product_id': fields.many2one('product.product', 'Product'),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production Lot')
    }


class contract_service_configurator(orm.TransientModel):
    _name = 'contract.service.configurator'

    def _get_default_category(self, cr, uid, context=None):
        res_company_obj = self.pool.get("res.company")
        company_id = res_company_obj._company_default_get(cr, uid, context)
        res_company = res_company_obj.browse(cr, uid, company_id,
                                             context=context)
        return res_company.default_product_category and res_company.default_product_category.id

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
        'dependency_ids': fields.many2many('contract.service.configurator.dependency.line',
                                           'contract_service_configurator_dependency_rel',
                                           'configurator_id',
                                           'dependency_id',
                                           'Dependencies'),
        'root_category_id': fields.many2one('product.category', 'Category'),
        'product_category_id': fields.many2one('product.category', 'Category'),
        'serial': fields.many2one('contract.service.serial', 'Serial Number'),
    }

    _defaults = {
        'state': 'draft',
        'product_category_id': lambda s, cr, uid, ctx: s._get_default_category(cr, uid, ctx),
        'root_category_id': lambda s, cr, uid, ctx: s._get_default_category(cr, uid, ctx)
    }

    def onchange_contract_id(self, cr, uid, ids, contract_id, root_category_id, context=None):
        product_category_obj = self.pool.get('product.category')
        if root_category_id:
            return {'domain': {'product_category_id': [('id', 'child_of', [int(root_category_id)])]}}
        else:
            return {}

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        ret = {}
        product_product_obj = self.pool.get('product.product')
        if product_id and product_product_obj.browse(cr, uid, product_id, context=context).type == 'product':
            contract_service_serial = self.pool.get('contract.service.serial')
            location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1]
            stock_move_obj = self.pool.get('stock.move')
            stock_production_lot_obj = self.pool.get('stock.production.lot')

            clean_ids = contract_service_serial.search(cr, uid, [('product_id', '=', product_id)], context=context)
            contract_service_serial.unlink(cr, uid, clean_ids, context=context)

            query = [
                ('product_id', '=', product_id),
                ('stock_available', '>', 0.0)
            ]
            serial_ids = stock_production_lot_obj.search(cr, uid, query, context=context)
            #stock_move_ids = stock_move_obj.search(cr, uid, query, context=context)
            if serial_ids and product_product_obj.browse(cr, uid, product_id, context=context).qty_available > 0:
                if isinstance(serial_ids, int):
                    serial_ids = [serial_ids]

                for line in stock_production_lot_obj.browse(cr, uid, serial_ids, context=context):
                    if line.stock_available > 0.0:
                        record = {
                            'name': line.name,
                            'product_id': line.product_id.id,
                            'prodlot_id': line.id
                        }
                        contract_service_serial.create(cr, uid, record, context=context)
            else:
                ret['warning'] = {
                    'title': _('Information'),
                    'message': _("We don't have this product in stock at the moment!")
                }
                # ret['domain'] = {'product_category_id': [('id', 'child_of', [int(root_category_id)])]}
        return ret

    def do_next(self, cr, uid, ids, context=None):
        contract_service_configurator_line_obj = self.pool.get('contract.service.configurator.line')
        contract_service_configurator_dependency_line_obj = self.pool.get('contract.service.configurator.dependency.line')
        product_product_obj = self.pool.get('product.product')

        wizard = self.browse(cr, uid, ids[0], context=context)

        for line in wizard.dependency_ids:
            if line.configurator_id.id == ids[0]:
                if line.product_id.description:
                    state = 'message'
                elif line.product_id.type == 'product':
                    state = 'serial'
                else:
                    state = 'done'

                l = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'configurator_id': wizard.id,
                    'handle_dependency': line.product_id.dependency_ids and True or False,
                    'message': line.product_id.description,
                    'state': state
                }
                contract_service_configurator_line_obj.create(cr, uid, l, context=context)

        query = [('configurator_id', '=', wizard.id)]
        ids_to_unlink = contract_service_configurator_dependency_line_obj.search(cr,
                                                                                 uid,
                                                                                 query,
                                                                                 context=context)
        if ids_to_unlink:
            contract_service_configurator_dependency_line_obj.unlink(cr, uid,
                                                                     ids_to_unlink,
                                                                     context)

        loop_deps = False
        for line in wizard.line_ids:
            if line.handle_dependency:
                loop_deps = True
                for dep in line.product_id.dependency_ids:
                    if dep.type == 'product':
                        if line.product_id.description:
                            state = 'message'
                        elif line.product_id.type == 'product':
                            state = 'serial'
                        else:
                            state = 'done'

                        wl = {
                            'name': dep.product_id.name,
                            'product_id': dep.product_id.id,
                            'configurator_id': wizard.id,
                            'parent_id': line.id,
                            'message': line.product_id.description,
                            'state': state
                        }
                        contract_service_configurator_dependency_line_obj.create(cr, uid, wl,
                                                                                 context=context)

                    elif dep.type == 'category':
                        query = [('categ_id', '=', dep.category_id.id)]
                        product_ids = product_product_obj.search(cr, uid,
                                                                 query,
                                                                 context=context)
                        for product in product_product_obj.browse(cr, uid, product_ids, context=context):
                            if line.product_id.description:
                                state = 'message'
                            elif line.product_id.type == 'product':
                                state = 'serial'
                            else:
                                state = 'done'

                            wl = {
                                'name': product.name,
                                'product_id': product.id,
                                'configurator_id': wizard.id,
                                'parent_id': line.id,
                                'message': product.description,
                                'state': state
                            }
                            contract_service_configurator_dependency_line_obj.create(cr, uid, wl,
                                                                                     context=context)
                line.write({'handle_dependency': False})
                break

        if loop_deps:
            record = {
                'state': 'dependency',
                'must_go_to_dependencies': False,
            }
            wizard.write(record)
            return self.router(cr, uid, ids, {}, context=context)

        else:
            record = {
                'state': 'product',
                'must_go_to_dependencies': False,
                'current_product_id': None,
                'dependency_ids': [(5)],
            }
            wizard.write(record)

            query = [('configurator_id', '=', wizard.id)]
            ids_to_unlink = contract_service_configurator_dependency_line_obj.search(cr,
                                                                                     uid,
                                                                                     query,
                                                                                     context=context)
            return self.router(cr, uid, ids, {}, context=context)

    def do_add_current_product_id(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        deps = 0
        wizard = self.browse(cr, uid, ids[0], context)
        contract_service_configurator_line_obj = self.pool.get('contract.service.configurator.line')
        contract_service_configurator_dependency_line_obj = self.pool.get('contract.service.configurator.dependency.line')
        product_product_obj = self.pool.get('product.product')
        contract_service_serial_obj = self.pool.get('contract.service.serial')
        ir_model_data_obj = self.pool.get('ir.model.data')

        if wizard.current_product_id:
            if wizard.current_product_id.description:
                state = 'message'
            elif wizard.current_product_id.type == 'product':
                state = 'serial'
            else:
                state = 'done'

            record = {
                'name': wizard.current_product_id.name,
                'product_id': wizard.current_product_id.id,
                'configurator_id': wizard.id,
                'serial': wizard.serial and wizard.serial.id or None,
                'message': wizard.current_product_id.description,
                'state': 'done'
            }
            new_line = contract_service_configurator_line_obj.create(cr, uid,
                                                                     record,
                                                                     context=context)

            for dep in wizard.current_product_id.dependency_ids:
                deps += 1
                if dep.type == 'product':
                    if dep.product_id.description:
                        state = 'message'
                    elif dep.product_id.type == 'product':
                        state = 'serial'
                    else:
                        state = 'done'

                    wl = {
                        'name': dep.product_id.name,
                        'product_id': dep.product_id.id,
                        'configurator_id': wizard.id,
                        'parent_id': new_line,
                        'message': dep.product_id.description,
                        'state': state
                    }
                    new_dep = contract_service_configurator_dependency_line_obj.create(cr, uid, wl,
                                                                                       context=context)

                    if dep.auto:
                        wizard.write({'dependency_ids': [(4, new_dep)]})

                elif dep.type == 'category':
                    query = [('categ_id', '=', dep.category_id.id)]
                    product_ids = product_product_obj.search(cr, uid, query,
                                                             context=context)
                    for product in product_product_obj.browse(cr, uid,
                                                              product_ids,
                                                              context=context):
                        if product.description:
                            state = 'message'
                        elif product.type == 'product':
                            state = 'serial'
                        else:
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
                        contract_service_configurator_dependency_line_obj.create(cr, uid,
                                                                                 record,
                                                                                 context=context)

            record = {
                'current_product_id': None,
                'serial': None,
                'product_category_id': self._get_default_category(cr, uid, context),
                'state': deps and 'dependency' or 'product'
            }

            wizard.write(record)

            return wizard.router({})

    def do_done(self, cr, uid, ids, context=None):
        account_analytic_account_obj = self.pool.get('account.analytic.account')
        contract_service_obj = self.pool.get('contract.service')
        stock_move_obj = self.pool.get('stock.move')
        contract_service_serial_obj = self.pool.get('contract.service.serial')
        ret = self.write(cr, uid, ids, {'state': 'done'}, context=context)
        wizard = self.browse(cr, uid, ids[0], context=context)
        for line in wizard.line_ids:
            l = {
                'account_id': wizard.contract_id.id,
                'product_id': line.product_id.id,
                'analytic_line_type': line.product_id.analytic_line_type,
                'require_activation': line.product_id.require_activation
            }
            contract_service_obj.create(cr, uid, l, context=context)
            if line.product_id.type == 'product':
                location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1]
                location_dest_id = wizard.contract_id.partner_id.property_stock_customer.id
                move = {
                    'name': line.product_id and line.product_id.name or '',
                    'product_id': line.product_id and line.product_id.id,
                    'product_uom': line.product_id and line.product_id.uom_id and line.product_id.uom_id.id or None,
                    'prodlot_id': line.serial and line.serial.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    'partner_id': wizard.contract_id.partner_id.id,
                    'type': 'out'
                }
                stock_move_id = stock_move_obj.create(cr, uid, move, context=context)
                stock_move_obj.action_confirm(cr, uid, [stock_move_id], context=context)
                stock_move_obj.action_done(cr, uid, [stock_move_id], context=context)

        ids_to_unlink = contract_service_serial_obj.search(cr, uid, [], context=context)
        contract_service_serial_obj.unlink(cr, uid, ids_to_unlink, context=context)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.account',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': wizard.contract_id.id,
            'context': context
        }
        #return True

    def router(self, cr, uid, ids, data=None, context=None):
        if isinstance(ids, list):
            ids = ids[0]
        wizard = self.browse(cr, uid, ids, context=context)
        for line in wizard.line_ids:
            if line.state in ('message', 'serial', 'stock'):
                if line.state == 'serial':
                    stock_production_lot_obj = self.pool.get('stock.production.lot')
                    product_product_obj = self.pool.get('product.product')

                    query = [
                        ('product_id', '=', line.product_id.id),
                        ('stock_available', '>', 0)
                    ]

                    serial_ids = stock_production_lot_obj.search(cr, uid, query, context=context)

                    if not serial_ids:
                        line.write({'state': 'stock'})

                return {
                    'name': _('Product Details') + ': ' + line.name,
                    'type': 'ir.actions.act_window',
                    'res_model': 'contract.service.configurator.line',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'res_id': line.id,
                    'nodestroy': True,
                    'context': context
                }

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
