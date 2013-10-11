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
        if line.state == 'message':
            if line.product_id.type == 'product' and \
                    line.product_id.qty_available > 0.0:
                state = 'serial'
            else:
                state = 'stock'
        elif line.state in ('serial', 'stock'):
            stock_move_obj = self.pool.get('stock.move')
            location_id = self.pool.get('ir.model.data').get_object_reference(
                cr, uid, 'stock', 'stock_location_stock')[1]
            location_dest_id = line.configurator_id.contract_id.partner_id.property_stock_customer.id
            move = {
                'name': line.product_id and line.product_id.name or '',
                'product_id': line.product_id and line.product_id.id,
                'product_uom': line.product_id and line.product_id.uom_id and line.product_id.uom_id.id or None,
                'prodlot_id': line.serial and line.serial.id or None,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'partner_id': line.configurator_id.contract_id.partner_id.id,
                'type': 'out'
            }
            stock_move_id = stock_move_obj.create(
                cr, uid, move, context=context)
            stock_move_obj.action_confirm(
                cr, uid, [stock_move_id], context=context)
            stock_move_obj.action_done(
                cr, uid, [stock_move_id], context=context)

            state = 'done'

        line.write({'state': state, 'stock_move_id': stock_move_id})

        return line.configurator_id.router(data={})

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, int):
            ids = [ids]

        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id.type == 'product' and line.stock_move_id:
                stock_move_obj = self.pool.get('stock.move')
                move = {
                    'name': ' '.join([_('Cancel'), line.product_id and line.product_id.name or '']),
                    'product_id': line.product_id and line.product_id.id,
                    'product_uom': line.product_id and line.product_id.uom_id and line.product_id.uom_id.id or None,
                    'prodlot_id': line.serial and line.serial.id or None,
                    'location_id': line.stock_move_id.location_dest_id.id,
                    'location_dest_id': line.stock_move_id.location_id.id,
                    'partner_id': line.configurator_id.contract_id.partner_id.id,
                    'type': 'in'
                }
                stock_move_id = stock_move_obj.create(
                    cr, uid, move, context=context)
                stock_move_obj.action_confirm(
                    cr, uid, [stock_move_id], context=context)
                stock_move_obj.action_done(
                    cr, uid, [stock_move_id], context=context)

        return super(contract_service_configurator_line, self).unlink(
            cr, uid, ids, context=context)

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
        res_groups_obj = self.pool.get('res.groups')
        res_user = self.pool.get('res.users').browse(
            cr, uid, uid, context={})
        group_agent_n2_id = ir_model_data_obj.get_object_reference(
            cr, uid, 'contract_isp', 'group_isp_agent2')[1]
        group_agent_n2 = res_groups_obj.browse(
            cr, uid, group_agent_n2_id, context={})

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
        'dependency_ids': fields.many2many('contract.service.configurator.dependency.line',
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
        'product_category_id': lambda s, cr, uid, ctx: s._get_default_category(cr, uid, ctx),
        'root_category_id': lambda s, cr, uid, ctx: s._get_default_category(cr, uid, ctx),
        'is_level2': lambda s, cr, uid, ctx: s._get_is_level2(cr, uid, ctx)
    }

    def onchange_product_category_id(self, cr, uid, ids,
                                     product_category_id, is_level2):
        domain = [('categ_id', '=', product_category_id)]
        ret = {
            'domain': {'current_product_id': None}}

        if not is_level2:
            domain.append(('list_price', '>=', 0))

        ret['domain']['current_product_id'] = domain

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
                        if not wizard.is_level2 and dep.list_price < 0:
                            continue

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
                        new_dep = contract_service_configurator_dependency_line_obj.create(
                            cr, uid, wl, context=context)

                        if dep.auto:
                            wizard.write({'dependency_ids': [(4, new_dep)]})

                    elif dep.type == 'category':
                        query = [('categ_id', '=', dep.category_id.id)]
                        product_ids = product_product_obj.search(cr, uid,
                                                                 query,
                                                                 context=context)
                        for product in product_product_obj.browse(cr, uid, product_ids, context=context):
                            if not wizard.is_level2 and dep.list_price < 0:
                                continue

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
            ids_to_unlink = contract_service_configurator_dependency_line_obj.search(cr,
                                                                                     uid,
                                                                                     query,
                                                                                     context=context)
            return self.router(cr, uid, ids, {}, context=context)

    def do_add_current_product_id(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        deps = 0
        wizard = self.browse(cr, uid, ids[0], context=context)
        contract_service_configurator_line_obj = self.pool.get(
            'contract.service.configurator.line')
        contract_service_configurator_dependency_line_obj = self.pool.get(
            'contract.service.configurator.dependency.line')
        product_product_obj = self.pool.get('product.product')
        contract_service_serial_obj = self.pool.get('contract.service.serial')

        if wizard.current_product_id:
            #if group_agent_n2_id not in res_user.groups_id and \
            #        wizard.current_product_id.type == 'product' and \
            #        wizard.current_product_id.qty_available <= 0:
            #    raise orm.except_orm(_('Error!'), _('Product not available!'))

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

                    if dep.product_id.description:
                        state = 'message'
                    elif dep.product_id.type == 'product':
                        state = 'serial'
                    else:
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
                        if not wizard.is_level2 and dep.product_id.list_price < 0:
                            continue

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
                        contract_service_configurator_dependency_line_obj.create(
                            cr, uid, record, context=context)

            record = {
                'current_product_id': None,
                'product_category_id': self._get_default_category(cr, uid, context),
                'state': deps and 'dependency' or 'product'
            }

            wizard.write(record)

            return wizard.router({})
        raise orm.except_orm(_('Error'), _('Product not found!'))

    def do_done(self, cr, uid, ids, context=None):
        account_analytic_account_obj = self.pool.get('account.analytic.account')
        contract_service_obj = self.pool.get('contract.service')
        stock_move_obj = self.pool.get('stock.move')
        contract_service_serial_obj = self.pool.get('contract.service.serial')
        ret = self.write(cr, uid, ids, {'state': 'done'}, context=context)
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

    def do_cancel(self, cr, uid, ids, context=None):
        if isinstance(ids, int):
            ids = [ids]

        for line in self.browse(cr, uid, ids[0], context=context).line_ids:
            if line.product_id.type == 'product' and line.stock_move_id:
                stock_move_obj = self.pool.get('stock.move')
                move = {
                    'name': ' '.join([_('Cancel'), line.product_id and line.product_id.name or '']),
                    'product_id': line.product_id and line.product_id.id,
                    'product_uom': line.product_id and line.product_id.uom_id and line.product_id.uom_id.id or None,
                    'prodlot_id': line.serial and line.serial.id or None,
                    'location_id': line.stock_move_id.location_dest_id.id,
                    'location_dest_id': line.stock_move_id.location_id.id,
                    'partner_id': line.configurator_id.contract_id.partner_id.id,
                    'type': 'in'
                }
                stock_move_id = stock_move_obj.create(
                    cr, uid, move, context=context)
                stock_move_obj.action_confirm(
                    cr, uid, [stock_move_id], context=context)
                stock_move_obj.action_done(
                    cr, uid, [stock_move_id], context=context)

        return True

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
