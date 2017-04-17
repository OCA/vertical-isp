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

from openerp import models, fields, api

class ProductDependency(models.Model):
    _name = 'product.dependency'

    name = fields.Char('Name')
    ptype = fields.Selection([('product', 'Product'),
                              ('category', 'Category')], string='Type',
                             default='product')
    product_id = fields.Many2one('product.product',
                                 string='Product Dependency')
    category_id = fields.Many2one('product.category',
                                  string='Category Dependency')
    auto = fields.Boolean(string='Automatically added')

    @api.onchange('ptype')
    def onchange_type(self):
        values = {'value': {}}
        if self.ptype == 'product':
            values['value']['category_id'] = None
        elif self.ptype == 'category_id':
            values['value']['product_id'] = None
        values['name'] = ''
        return values

    @api.onchange('product_id')
    def onchange_product_id(self):
        values = {'value': {'name': None}}
        if self.product_id:
            product = self.env['product.product']
            name = product.name
            values['value']['name'] = '%s (Product)' % name
        return values

    @api.onchange('category_id')
    def onchange_category_id(self):
        values = {'value': {'name': None}}
        if self.category_id:
            category = self.env['product.category']
            name = category.name
            values['value']['name'] = '%s (Category)' % name
        return values


class ProductProduct(models.Model):
    _inherit = 'product.product'

    dependency_ids = fields.Many2many(comodel_name='product.dependency',
                                      relation='product_product_'
                                      'dependency_rel',
                                      column1='dependency_id',
                                      column2='product_id',
                                      string='Dependencies')
