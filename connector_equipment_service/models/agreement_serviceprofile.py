# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import _, api, models


class AgreementServiceProfile(models.Model):
    _inherit = ['agreement.serviceprofile']

    @api.model
    def create(self, vals):
        # If SP is created with a managed equipment
        if vals.get('equipment_id', False):
            new = self.env['maintenance.equipment'].\
                browse(vals.get('equipment_id'))
            new._connect('add_service',
                         serviceprofiles=self)
        return super().create(vals)

    @api.multi
    def write(self, vals):
        equip_id = self.get_equip(vals)
        # Add Service
        # If equipment was empty and now set to managed or stage in draft
        if equip_id and (not self.equipment_id or self.
                         get_next_stage(vals) == 'draft'):
            equip_id._connect('add_service', serviceprofiles=self)
            self.message_post(body=_('Added Service'))

        # Update Service
        # If SP is changed but not the managed equipment
        # Don't call update if stage_id is all that is changed
        if (equip_id and (len(vals) > 1 or 'stage_id' not in vals)):
            # If equipment was changed, handle old equipment accordingly
            if vals.get('equipment_id', False):
                self.equip_changed(vals)
            self.equipment_id._connect('update_service',
                                       serviceprofiles=self)
            self.message_post(body=_('Updated Service'))

        # Activate Service (Provision?)
        # If SP state -> In Progress and equipment is managed
        if self.get_next_stage(vals) == 'in_progress' and equip_id:
            equip_id._connect('activate_service',
                              serviceprofiles=self)
            self.message_post(body=_('Activated Service'))

        # Suspend Service
        # If SP state -> Suspend and equipment is managed
        if self.get_next_stage(vals) == 'suspend' and equip_id:
            equip_id._connect('suspend_service',
                              serviceprofiles=self)
            self.message_post(body=_('Suspended Service'))

        # Suspend/Remove Service
        # If SP state -> Closed or Cancelled and equipment is managed
        if self.get_next_stage(vals) in ['close', 'cancel'] and equip_id:
            equip_id._connect('suspend_service',
                              serviceprofiles=self)
            equip_id._connect('remove_service',
                              serviceprofiles=self)
            self.message_post(body=_('Suspended Service'))
            self.message_post(body=_('Removed Service'))

        return super().write(vals)

    # This method handles the old equipment if it is changed
    def equip_changed(self, vals):
        # Was the old Equipment Managed?
        if self.equipment_id.managed:
            # Is the SP In Progress (or going to be)
            if self.get_stage(vals) in ['in_progress', 'to_renew']:
                # Suspend
                self.equipment_id._connect('suspend_service',
                                           serviceprofiles=self)
                self.message_post(body=_('Previous Service Suspended'))
            # SP is not In Progress (or going to be)
            else:
                # Remove
                self.equipment_id._connect('remove_service',
                                           serviceprofiles=self)
                self.message_post(body=_('Previous Service Removed'))

    # This method returns the final equipment on the form
    # If there is a managed equipment in vals, use it
    # If there is not, check self for managed equipment
    # If neither, return False
    def get_equip(self, vals):
        equip = vals.get('equipment_id', False)
        if equip:
            equip = self.env['maintenance.equipment'].\
                browse(vals.get('equipment_id'))
            if equip.managed:
                return equip
        else:
            if self.equipment_id.managed:
                return self.equipment_id
        return False

    # This method returns the appriopriate stage_id
    # If there is a stage in vals, use it
    # If there is no stage in vals, use the current stage
    def get_stage(self, vals):
        x = ''
        if ((vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_draft').id) or
                (not vals.get('stage_id', False) and
                 self.stage_id.id == self.env.
                 ref('agreement_serviceprofile.servpro_stage_draft').id)):
            x = 'draft'
        if ((vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_progress').id) or
                (not vals.get('stage_id', False) and
                 self.stage_id.id == self.env.
                 ref('agreement_serviceprofile.servpro_stage_progress').id)):
            x = 'in_progress'
        if ((vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_suspend').id) or
                (not vals.get('stage_id', False) and
                 self.stage_id.id == self.env.
                 ref('agreement_serviceprofile.servpro_stage_suspend').id)):
            x = 'suspend'
        if ((vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_renew').id) or
                (not vals.get('stage_id', False) and
                 self.stage_id.id == self.env.
                 ref('agreement_serviceprofile.servpro_stage_renew').id)):
            x = 'to_renew'
        if ((vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_close').id) or
                (not vals.get('stage_id', False) and
                 self.stage_id.id == self.env.
                 ref('agreement_serviceprofile.servpro_stage_close').id)):
            x = 'closed'
        if ((vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_cancel').id) or
                (not vals.get('stage_id', False) and
                 self.stage_id.id == self.env.
                 ref('agreement_serviceprofile.servpro_stage_cancel').id)):
            x = 'cancel'
        return x

    # Check to see if the stage is being changed
    def get_next_stage(self, vals):
        if (vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_draft').id):
            return 'draft'
        if (vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_progress').id):
            return 'in_progress'
        if (vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_suspend').id):
            return 'suspend'
        if (vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_renew').id):
            return 'renew'
        if (vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_close').id):
            return 'close'
        if (vals.get('stage_id', False) == self.env.
                ref('agreement_serviceprofile.servpro_stage_cancel').id):
            return 'cancel'
        return False
