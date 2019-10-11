# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, models


class AgreementServiceProfile(models.Model):
    _inherit = ['agreement.serviceprofile']

    @api.multi
    def write(self, vals):
        # If equipment was empty and now set to managed equipment
        if vals.get('equipment_id', False) and not self.equipment_id:
            new = self.env['maintenance.equipment'].\
                browse(vals.get('equipment_id'))
            new._connect('add_service', serviceprofiles=self)
            self.message_post(body=_('Added Service'))
        # If SP is changed but not the managed equipment
        if 'equipment_id' not in vals and self.equipment_id.managed:
            self.equipment_id._connect('update_service',
                                       serviceprofiles=self)
            self.message_post(body=_('Updated Service'))
        # If SP state is changed to In Progress and equipment is managed
        if (vals.get('stage_id', False) == self.env.
                ref('contract.servpro_stage_progress').id and
                self.equipment_id.managed):
            self.equipment_id._connect('activate_service',
                                       serviceprofiles=self)
            self.message_post(body=_('Activated Service'))
        # If SP state is changed to Suspend and equipment is managed
        if (vals.get('stage_id', False) == self.env.
                ref('contract.servpro_stage_suspend').id and
                self.equipment_id.managed):
            self.equipment_id._connect('suspend_service',
                                       serviceprofiles=self)
            self.message_post(body=_('Suspended Service'))
        # If equipment was a managed equipment and is changed to False
        if 'equipment_id' in vals and self.equipment_id.managed:
            if not vals['equipment_id']:
                self.equipment_id._connect('remove_service',
                                           serviceprofiles=self)
                self.message_post(body=_('Removed Service'))
        # If equipment is changed to another equipment
        if vals.get('equipment_id', False) and self.equipment_id:
            # If previous equipment is managed
            if self.equipment_id.managed:
                # SP is Active (or going to be)
                if ((self.stage_id.id == self.env.
                        ref('contract.servpro_stage_progress').id and
                        not vals.get('stage_id', False))
                        or vals.get('stage_id', False) == self.env.
                        ref('contract.servpro_stage_progress').id):
                    self.equipment_id._connect('suspend_service',
                                               serviceprofiles=self)
                    self.message_post(body=_('Previous Service Suspended'))
                else:
                    self.equipment_id._connect('remove_service',
                                               serviceprofiles=self)
                    self.message_post(body=_('Previous Service Removed'))
            # If new equipment is managed and SP is Active (or going to be)
            new = self.env['maintenance.equipment'].\
                browse(vals.get('equipment_id'))
            if new.managed:
                # SP is Active (or going to be)
                if ((self.stage_id.id == self.env.
                        ref('contract.servpro_stage_progress').id and
                        not vals.get('stage_id', False))
                        or vals.get('stage_id', False) == self.env.
                        ref('contract.servpro_stage_progress').id):
                    new._connect('activate_service', serviceprofiles=self)
                    self.message_post(body=_('New Service Activated'))
                else:
                    new._connect('add_service', serviceprofiles=self)
                    self.message_post(body=_('New Service Added'))
        return super().write(vals)
