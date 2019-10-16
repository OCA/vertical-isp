# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import time
from odoo.tests.common import TransactionCase


class ConnectorEquipment(TransactionCase):

    def setUp(self):
        super(ConnectorEquipment, self).setUp()
        self.backend_equipment = self.env['backend.equipment']
        self.maintenance_equipment = self.env['maintenance.equipment']

    def test_maintenance_equipment_create(self):
        """ Test creating new workorders, and test following functions,
            - _compute_duration() in hrs
            - _compute_request_late()
            - Set scheduled_date_start using request_early w/o time
            - scheduled_date_end = scheduled_date_start + duration (hrs)
        """

        backend_01 = self.env['backend.equipment'].create({
            'name': 'Test Equipment',
            'host': 'Test Host',
            'port': 'Test Port',
            'user': 'Test User',
            'password': 'Test Password',
            'protocol': 'rest'
        })
        equipment_01 = self.env['maintenance.equipment'].create({
            'name': 'Samsung Monitor "15',
            'category_id': self.ref('maintenance.equipment_monitor'),
            'technician_user_id': self.ref('base.user_root'),
            'assign_date': time.strftime('%Y-%m-%d'),
            'serial_no': 'MT/127/18291015',
            'model': 'NP355E5X',
            'color': 3,
            'backend_id': backend_01.id,
            'managed': True

        })

        self.assertEqual(equipment_01.update_config(), True)
