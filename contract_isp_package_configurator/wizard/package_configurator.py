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

from openerp.tools.translate import _
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class contract_service_configurator_line(models.TransientModel):
    _name = 'contract.service.configurator.line'

#   def _get_stock_production_lot_available(self, cr, uid,)
    name = fields.Char('Name')
    product_id = fields.Many2one('product.product', 'Product')
    configurator_id = fields.Many2one('contract.service.configurator',
                                      'Package Configurator')
    parent_id = fields.Many2one('contract.service.configurator.line',
                                'Parent')
    serial = fields.Many2one('stock.production.lot', 'Serial Number')
    message = fields.Text('Message')
    handle_dependency = fields.Boolean('Handle dependencies')
    stock_move_id = fields.Many2one('stock.move', 'Stock Move')
    state = fields.Selection((('draft', _('Added')),
                              ('message', _('Information')),
                              ('serial', _('Select serial number')),
                              ('stock', ('No Stock')),
                              ('done', _('Done'))), 'State', default='draft')

    @api.multi
    def router(self, data=None):
        stock_move_id = None
        if isinstance(self._ids, list):
            ids = self._ids[0]
        if self.state == 'message':
            if self.product_id.type == 'product' and \
                    self.product_id.qty_available > 0.0:
                state = 'serial'
            else:
                state = 'stock'
        elif self.state in ('serial', 'stock'):
            stock_move_obj = self.env['stock.move']
            location_id = self.env['ir.model.data'].get_object_reference
            ('stock', 'stock_location_stock')[1]
            location_dest_id = self.configurator_id.contract_id.partner_id.\
            property_stock_customer.id
            move = {
                'name': self.product_id and self.product_id.name or '',
                'product_id': self.product_id and self.product_id.id,
                'product_uom': self.product_id and self.product_id.uom_id and
                self.product_id.uom_id.id or None,
                'prodlot_id': self.serial and self.serial.id or None,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'partner_id': self.configurator_id.contract_id.partner_id.id,
                'type': 'out'
            }
            stock_move_id = stock_move_obj.create(move)
            stock_move_id.action_confirm()
            stock_move_id.action_done()
            state = 'done'
        self.write({'state': state, 'stock_move_id': stock_move_id and
                    stock_move_id.id})

        return self.configurator_id.router(data={})

    @api.multi
    def unlink(self):
        if isinstance(self.ids, int):
            ids = [ids]

        for line in self:
            if line.product_id.type == 'product' and line.stock_move_id:
                stock_move_obj = self.env['stock.move']
                move = {
                    'name': ' '.join([_('Cancel'), line.product_id and
                                      line.product_id.name or '']),
                    'product_id': line.product_id and line.product_id.id,
                    'product_uom': line.product_id and line.product_id.uom_id
                    and line.product_id.uom_id.id or None,
                    'prodlot_id': line.serial and line.serial.id or None,
                    'location_id': line.stock_move_id.location_dest_id.id,
                    'location_dest_id': line.stock_move_id.location_id.id,
                    'partner_id': line.configurator_id.contract_id.
                    partner_id.id,
                    'type': 'in'
                }
                stock_move_id = stock_move_obj.create(move)
                stock_move_id.action_confirm()
                stock_move_id.action_done()

        return super(contract_service_configurator_line, self).unlink()

    @api.onchange('product_id')
    def onchange_product_id(self):
        ret = {}
        product_product_obj = self.env['product.product']
        if product_product_obj.browse(self.product_id).description:
            ret['warning'] = {
                'title': _('Information'),
                'message': product_product_obj.browse(self.product_id)
                .description
            }
        return ret


class contract_service_configurator_dependency_line(models.TransientModel):
    _inherit = 'contract.service.configurator.line'


class contract_service_configurator(models.TransientModel):
    _name = 'contract.service.configurator'

    @api.multi
    def _get_default_category(self):
        res_company_obj = self.env["res.company"]
        company_id = res_company_obj._company_default_get()
        res_company = res_company_obj.browse(company_id)
        return res_company.default_product_category and \
            res_company.default_product_category.id

    @api.one
    def _get_is_level2(self):
        ir_model_data_obj = self.env['ir.model.data']
        res_groups_obj = self.env['res.groups']
        res_user = self.env['res.users'].browse(self._uid)
        group_agent_n2_id = ir_model_data_obj.get_object_reference
        ('contract_isp', 'group_isp_agent2')[1]
        group_agent_n2 = res_groups_obj.browse(group_agent_n2_id)

        groups_id = [i.id for i in res_user.groups_id]
        if group_agent_n2_id not in groups_id:
            return False
        else:
            return True

    contract_id = fields.Many2one('account.analytic.account', 'Contract')
    state = fields.Selection((('draft', _('Start')),
                              ('product', _('Select product')),
                              ('dependency', _('Select components')),
                              ('done', _('Done'))), 'State', default='draft')
    line_ids = fields.One2many('contract.service.configurator.line',
                               'configurator_id',
                               'Line')
    current_product_id = fields.Many2one('product.product',
                                         'Add Product')
    dependency_ids = fields.Many2many('contract.service.configurator.'
                                      'dependency.line',
                                      'contract_service_configurator_'
                                      'dependency_rel',
                                      'configurator_id',
                                      'dependency_id',
                                      'Dependencies')
    root_category_id = fields.Many2one('product.category', 'Category')
    product_category_id = fields.Many2one('product.category', 'Category',
                                          default=lambda s: s.
                                          _get_default_category())
    is_level2 = fields.Boolean('Is level 2',
                               default=lambda s: s._get_is_level2())

    @api.onchange('product_id', 'is_level2', 'product_category_id')
    def onchange_product_category_id(self):
        ret = {}
        if self.product_category_id:
            domain = [('categ_id', '=', self.product_category_id.id)]
            ret = {'domain': {'current_product_id': None}}
            if not self.is_level2:
                domain.append(('list_price', '>=', 0))
            ret['domain']['current_product_id'] = domain
        return ret

    @api.multi
    def do_next(self):
        contract_service_configurator_line_obj = \
        self.env['contract.service.configurator.line']
        contract_service_configurator_dependency_line_obj = \
        self.env['contract.service.configurator.dependency.line']
        product_product_obj = self.env['product.product']

        for line in self.dependency_ids:
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
                    'configurator_id': self.id,
                    'handle_dependency': line.product_id.dependency_ids
                    and True or False,
                    'message': line.product_id.description,
                    'state': state
                }
                contract_service_configurator_line_obj.create(l)

        query = [('configurator_id', '=', self.ids)]
        ids_to_unlink = contract_service_configurator_dependency_line_obj \
        .search(query)
        if ids_to_unlink:
            contract_service_configurator_dependency_line_obj \
            .unlink(ids_to_unlink)

        loop_deps = False
        for line in self.line_ids:
            if line.handle_dependency:
                loop_deps = True
                for dep in line.product_id.dependency_ids:
                    if dep.type == 'product':
                        if not self.is_level2 and dep.list_price < 0:
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
                            'configurator_id': self.id,
                            'parent_id': line.id,
                            'message': line.product_id.description,
                            'state': state
                        }
                        new_dep = contract_service_configurator_dependency_line_obj.create(wl)

                        if dep.auto:
                            self.write({'dependency_ids': [(4, new_dep)]})

                    elif dep.type == 'category':
                        query = [('categ_id', '=', dep.category_id.id)]
                        product_ids = product_product_obj.search(query)
                        for product in product_ids:
                            if not self.is_level2 and dep.list_price < 0:
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
                                'configurator_id': self.id,
                                'parent_id': line.id,
                                'message': product.description,
                                'state': state
                            }
                            contract_service_configurator_dependency_line_obj \
                            .create(wl)
                line.write({'handle_dependency': False})
                break

        if loop_deps:
            record = {
                'state': 'dependency',
            }
            self.write(record)
            return self.router({})

        else:
            record = {
                'state': 'product',
                'current_product_id': None,
                'dependency_ids': [(5)],
            }
            self.write(record)

            query = [('configurator_id', '=', self.id)]
            ids_to_unlink = contract_service_configurator_dependency_line_obj \
            .search(query)
            return self.router({})

    @api.multi
    def do_add_current_product_id(self):
        if self._context is None:
            context = {}
        deps = 0
        contract_service_configurator_line_obj = \
        self.env['contract.service.configurator.line']
        contract_service_configurator_dependency_line_obj = self.env[
            'contract.service.configurator.dependency.line']
        product_product_obj = self.env['product.product']
#        contract_service_serial_obj = self.env['contract.service.serial']

        if self.current_product_id:
            #  if group_agent_n2_id not in res_user.groups_id and \
            #        self.current_product_id.type == 'product' and \
            #        self.current_product_id.qty_available <= 0:
            #    raise orm.except_orm(_('Error!'), _('Product not available!'))

            if self.current_product_id.description:
                state = 'message'
            elif self.current_product_id.type == 'product':
                state = 'serial'
            else:
                state = 'done'

            record = {
                'name': self.current_product_id.name,
                'product_id': self.current_product_id.id,
                'configurator_id': self.id,
                'message': self.current_product_id.description,
                'state': state
            }
            new_line = contract_service_configurator_line_obj.create(record)
            for dep in new_line.product_id.dependency_ids:
                if dep.type == 'product':
                    if not self.is_level2 and dep.product_id.list_price < 0:
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
                        'configurator_id': self.id,
                        'parent_id': new_line,
                        'message': dep.product_id.description,
                        'state': state
                    }
                    new_dep = contract_service_configurator_dependency_line_obj.create(wl)

                    if dep.auto:
                        self.write({'dependency_ids': [(4, new_dep)]})

                elif dep.type == 'category':
                    query = [('categ_id', '=', dep.category_id.id)]
                    product_ids = product_product_obj.search(query)
                    for product in product_ids:
                        if not self.is_level2 and dep.product_id. \
                        list_price < 0:
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
                            'configurator_id': self.id,
                            'parent_id': new_line,
                            'message': product.description,
                            'state': state
                        }
                        contract_service_configurator_dependency_line_obj\
                        .create(record)

            record = {
                'current_product_id': None,
                'product_category_id': self._get_default_category(),
                'state': deps and 'dependency' or 'product'
            }

            self.write(record)

            return self.router({})
        raise Warning(_('Error'), _('Product not found!'))

    @api.multi
    def do_done(self):
        account_analytic_account_obj = self.env['account.analytic.account']
        contract_service_obj = self.env['contract.service']
        stock_move_obj = self.env['stock.move']
#        contract_service_serial_obj = self.env['contract.service.serial']
        ret = self.write({'state': 'done'})
        for line in self.line_ids:
            l = {
                'name': line.serial and line.serial.name or '',
                'account_id': self.contract_id.id,
                'product_id': line.product_id.id,
                'category_id': line.product_id.categ_id.id,
                'analytic_line_type': line.product_id.analytic_line_type,
                'require_activation': line.product_id.require_activation
            }
            contract_service_obj.create(l)

            if line.product_id.type == 'product' and line.stock_move_id:
                line.write({'stock_move_id': None})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.account',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.contract_id.id,
            'context': self._context
        }

    @api.multi
    def do_cancel(self):
        if isinstance(self.ids, int):
            ids = [self.ids]

        for line in self.line_ids:
            if line.product_id.type == 'product' and line.stock_move_id:
                stock_move_obj = self.env('stock.move')
                move = {
                    'name': ' '.join([_('Cancel'), line.product_id
                                      and line.product_id.name or '']),
                    'product_id': line.product_id and line.product_id.id,
                    'product_uom': line.product_id and line.product_id.uom_id
                    and line.product_id.uom_id.id or None,
                    'prodlot_id': line.serial and line.serial.id or None,
                    'location_id': line.stock_move_id.location_dest_id.id,
                    'location_dest_id': line.stock_move_id.location_id.id,
                    'partner_id': line.configurator_id.contract_id.
                    partner_id.id,
                    'type': 'in'
                }
                stock_move_id = stock_move_obj.create(move)
                stock_move_obj.action_confirm([stock_move_id])
                stock_move_obj.action_done([stock_move_id])

        return True

    @api.multi
    def router(self, data=None):
        if isinstance(self.ids, list):
            ids = self.ids[0]
        for line in self.line_ids:
            if line.state in ('message', 'serial', 'stock'):
                if line.state == 'serial':
                    stock_production_lot_obj = self.env['stock.production.lot']
                    product_product_obj = self.env['product.product']

                    query = [
                        ('product_id', '=', line.product_id.id),
                        ('quant_ids', '>', 0)
                    ]

                    serial_ids = stock_production_lot_obj.search(query)

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
                    'context': self._context
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
            'context': self._context
        }
