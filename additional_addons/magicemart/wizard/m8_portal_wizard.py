# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

import logging
import random

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import email_re
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

class wizard_user(osv.osv_memory):
    _inherit = 'portal.wizard.user'
    _description = 'Portal User Config'

    _columns = {
                    
                    }


    def action_apply(self, cr, uid, ids, context=None):
        for wizard_user in self.browse(cr, SUPERUSER_ID, ids, context):
            portal = wizard_user.wizard_id.portal_id
            user = self._retrieve_user(cr, SUPERUSER_ID, wizard_user, context)
            if wizard_user.in_portal:
                # create a user if necessary, and make sure it is in the portal group
                if not user:
                    user = self._create_user(cr, SUPERUSER_ID, wizard_user, context)
                if (not user.active) or (portal not in user.groups_id):
                    user.write({'active': True})
                    # prepare for the signup process
                    user.partner_id.signup_prepare()
                    wizard_user = self.browse(cr, SUPERUSER_ID, wizard_user.id, context)
                    self._send_email(cr, uid, wizard_user, context)
            else:
                # remove the user (if it exists) from the portal group
                if user and (portal in user.groups_id):
                    # if user belongs to portal only, deactivate it
                    if len(user.groups_id) <= 1:
                        user.write({'groups_id': [(3, portal.id)], 'active': False})
                    else:
                        user.write({'groups_id': [(3, portal.id)]})


wizard_user()

class stock_invoice_onshipping(osv.osv_memory):
    _inherit = 'stock.invoice.onshipping'
    
    # Inherited
    # Updating Wizard id 
    def open_invoice(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context.update({'wiz_id':ids})
        
        return super(stock_invoice_onshipping, self).open_invoice(cr, uid, ids, context=context)
        
stock_invoice_onshipping()
