
from openerp.osv import fields, osv 
from openerp.tools.translate import _
from ast import literal_eval

ROLES = [('magicemart_group_user','Magic User')
       , ('magicemart_group_manager','Magic Manager')
       , ('magicemart_portal_user', 'Customer Portal User')
       , ('magicemart_portal_manager', 'Customer Portal Manager')
       , ('magicemart_supplier_portal', 'Supplier Portal Manager')
           
        ] 


class res_users(osv.osv):
    _inherit = 'res.users' 
    
    _columns = {
                'location_id' : fields.many2one("stock.location",'Location',help='Customer Stock Location ...Ex:-Partner Locations/Customers/MagiceMart/Stock'),
                'user_roles'         : fields.selection(ROLES, 'Roles'),
                #Overriden to Remove Required
                'partner_id': fields.many2one('res.partner', required=False,
                                string='Related Partner', ondelete='restrict',
                                help='Partner-related data of the user'),
               }

    _description = "MagicEMart Users"
    

    # Overridden:
    def _signup_create_user(self, cr, uid, values, context=None):
        """ create a new user from the template user """
        print "its me"
        ctx = dict(context or {})
        ctx.update({'portal_user': True})
        ir_config_parameter = self.pool.get('ir.config_parameter')
        template_user_id = literal_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.template_user_id', 'False'))
        assert template_user_id and self.exists(cr, uid, template_user_id, context=context), 'Signup: invalid template user'
 
        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if not literal_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.allow_uninvited', 'False')):
                raise SignupError('Signup is not allowed for uninvited users')
 
        assert values.get('login'), "Signup: no login given for new user"
        assert values.get('partner_id') or values.get('name'), "Signup: no name or partner given for new user"
 
        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        context = dict(context or {}, no_reset_password=True)
        try:
            with cr.savepoint():
                return self.copy(cr, uid, template_user_id, values, context=ctx)
        except Exception, e:
            # copy may failed if asked login is not available.
            raise SignupError(ustr(e))
        
    def _get_belongingGroups(self, cr, uid, belongto, context=None):
        data_obj = self.pool.get('ir.model.data') 
        result = super(res_users, self)._get_group(cr, uid, context)
        try:  
            # Magic User
            dummy, mUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_user')
            dummy, soMgrid = data_obj.get_object_reference(cr, 1, 'base', 'group_sale_manager')
            dummy, stMgrid = data_obj.get_object_reference(cr, 1, 'stock', 'group_stock_manager')
            dummy, prMgrid = data_obj.get_object_reference(cr, 1, 'purchase', 'group_purchase_user')
            dummy, hrEmpid = data_obj.get_object_reference(cr, 1, 'base', 'group_user')
            
            # Magic Manager
            dummy, mMgrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_manager')
            dummy, pjMgrid = data_obj.get_object_reference(cr, 1, 'project', 'group_project_manager')
            dummy, accMgrid = data_obj.get_object_reference(cr, 1, 'account', 'group_account_manager')
            dummy, hrMgrid = data_obj.get_object_reference(cr, 1, 'base', 'group_hr_manager')
            
            # Customer Portal User
            dummy, ptUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_user')
            
            # Customer Portal Manager   
            dummy, ptMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_manager')     
            
            # Supplier Portal Manager
            dummy, supMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_supplier_portal')
            
            if belongto == 'magicemart_group_user':
                result.extend([mUsrid, soMgrid, stMgrid, prMgrid, hrEmpid])
           
            elif belongto == 'magicemart_group_manager':
                result.extend([mMgrid, soMgrid, pjMgrid, stMgrid, accMgrid, prMgrid, hrMgrid])
                    
            elif belongto == 'magicemart_portal_user':
                result.extend([ptUsrid,hrEmpid])
#                 if hrEmpid in result:
#                     result.remove(hrEmpid)
               
            elif belongto == 'magicemart_portal_manager':
                result.extend([ptMgr])
            
            elif belongto == 'magicemart_supplier_portal':
                result.extend([supMgr,hrEmpid])
                
        except ValueError:
            # If these groups does not exists anymore
            pass
        return result

    def create(self, cr, uid, values, context=None):
        part_obj = self.pool.get("res.partner")
        data_obj = self.pool.get('ir.model.data')
        
        if not 'lang' in context:
            context.update({'lang': 'en_US','search_default_no_share' : 1, 'tz':'Asia/Kolkata', 'uid':1 })
#         Users Create context {'lang': 'en_US', 'params': {'action': 78}, 'search_default_no_share': 1, 'tz': 'Asia/Kolkata', 'uid': 1}
        
        dummy, ptUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_user')
        dummy, ptMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_manager')
        dummy, mUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_user')
        dummy, mMgrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_manager')
        dummy, accMgrid = data_obj.get_object_reference(cr, 1, 'account', 'group_account_manager')
        dummy, accinvid = data_obj.get_object_reference(cr, 1, 'account', 'group_account_invoice')
        dummy, accacnt = data_obj.get_object_reference(cr, 1, 'account', 'group_account_user')
        dummy, stUser = data_obj.get_object_reference(cr, 1, 'stock', 'group_stock_user')
        dummy, stMgrid = data_obj.get_object_reference(cr, 1, 'stock', 'group_stock_manager')
        dummy, hrEmpid = data_obj.get_object_reference(cr, 1, 'base', 'group_user')
        dummy, supMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_supplier_portal')
        values.update({'active'  : True,})
        
        
        # Portal: Deletinf Standard Groups
        if context.get('portal_user', False):
            del values['groups_id']
            
        user_roles = values.get('user_roles', False)
                                
        if user_roles:
        
            if user_roles:  # Here we are checking the field 'usr_roels' adn value for 'usr_Roles' present 
                groupids = self._get_belongingGroups(cr, uid, values['user_roles'], context)
                for fl in groupids:
                    values['in_group_' + str(fl)] = True
                    
            if user_roles == 'magicemart_portal_manager':
                if not values.get("location_id"):
                    raise osv.except_osv(_('Warning'),_('Please select the Customer Stock Location '))

                        
            # To Make Magic User & Manager as False for Potal Group    
            if user_roles in( 'magicemart_group_user','magicemart_group_manager'):
                values.update(
                            {'sel_groups_'+ str(ptUsrid)+'_' + str(ptMgr) : False,
                             'sel_groups_'+str(supMgr):False,
                             'location_id': False,
                              }
                            )
            # To Make portal User & Manager as False for Magic Group
            if user_roles == 'magicemart_portal_user' or 'magicemart_portal_manager':
                values.update({
                            'sel_groups_'+ str(mUsrid)+'_' + str(mMgrid) : False,
                            'sel_groups_'+str(supMgr):False, 
                            })    
            if user_roles == 'magicemart_supplier_portal':
                values.update({
                            'sel_groups_'+ str(mUsrid)+'_' + str(mMgrid) : False,
                            'sel_groups_'+str(ptUsrid)+'_'+str(ptMgr):False,
                              })
                                
            if user_roles in ('magicemart_portal_user','magicemart_portal_manager','magicemart_supplier_portal'):
                part = values.get('partner_id')
                if part:
                    partner_id = part_obj.browse(cr, uid,part)
                    
                    values.update({
                                   'name':partner_id.name or False,
                                   
                                   })
            
                
        print "Create Last ___________________________", values.get('login', False), values.get('groups_id', False)
        return super(res_users, self).create(cr, uid, values, context=context) 

    def clear_allgroups(self, cr, uid, ids, context=None):
        clear = {}
        data_obj = self.pool.get('ir.model.data')
        dummy, ptUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_user')
        dummy, ptMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_manager')
        
        dummy, mUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_user')
        dummy, mMgrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_manager')
        
        dummy, supMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_supplier_portal')
        
        #Stock
        dummy, stUser = data_obj.get_object_reference(cr, 1, 'stock', 'group_stock_user')
        dummy, stMgrid = data_obj.get_object_reference(cr, 1, 'stock', 'group_stock_manager')

       
       # Account
        dummy, accinvid = data_obj.get_object_reference(cr, 1, 'account', 'group_account_invoice')
        dummy, accacnt = data_obj.get_object_reference(cr, 1, 'account', 'group_account_user')
        dummy, accMgrid = data_obj.get_object_reference(cr, 1, 'account', 'group_account_manager')
        
        # Sale Order
        dummy, soAlledsid = data_obj.get_object_reference(cr, 1, 'base', 'group_sale_salesman_all_leads')
        dummy, soMgrid = data_obj.get_object_reference(cr, 1, 'base', 'group_sale_manager')
        dummy, soOwnid = data_obj.get_object_reference(cr, 1, 'base', 'group_sale_salesman')
        
       # HR
        dummy, hrEmpid = data_obj.get_object_reference(cr, 1, 'base', 'group_user')
        dummy, hrMgrid = data_obj.get_object_reference(cr, 1, 'base', 'group_hr_manager')
        dummy, hrOfrid = data_obj.get_object_reference(cr, 1, 'base', 'group_hr_user')
        
        # Project
        dummy, prgMgrid = data_obj.get_object_reference(cr, 1, 'project', 'group_project_manager')
        dummy, prgUsrid = data_obj.get_object_reference(cr, 1, 'project', 'group_project_user')
        
        # Knowledge
        dummy, knowUsrid = data_obj.get_object_reference(cr, 1, 'base', 'group_document_user')
        
        # Purchase 
        dummy, prchUsrid = data_obj.get_object_reference(cr, 1, 'purchase', 'group_purchase_user')
        dummy, prchMgrid = data_obj.get_object_reference(cr, 1, 'purchase', 'group_purchase_manager')
        
        # Marketing
        dummy, mrkUsrid = data_obj.get_object_reference(cr, 1, 'marketing', 'group_marketing_user')
        dummy, mrkMgrid = data_obj.get_object_reference(cr, 1, 'marketing', 'group_marketing_manager')
        
        # Fleet
        dummy, fltUsrid = data_obj.get_object_reference(cr, 1, 'fleet', 'group_fleet_user')
        dummy, fltMgrid = data_obj.get_object_reference(cr, 1, 'fleet', 'group_fleet_manager')
        
        # Share
#         dummy, shrUsrid = data_obj.get_object_reference(cr, 1, 'share', 'group_share_user')
        # Purchase Requisition
        dummy, prqUsrid = data_obj.get_object_reference(cr, 1, 'purchase_requisition', 'group_purchase_requisition_user')
        dummy, prqMgrid = data_obj.get_object_reference(cr, 1, 'purchase_requisition', 'group_purchase_requisition_manager')
        
        # Administrator
        dummy, adminaccessid = data_obj.get_object_reference(cr, 1, 'base', 'group_erp_manager')
        dummy, settingid = data_obj.get_object_reference(cr, 1, 'base', 'group_system')
        
        # Extra Tools
#         dummy, extrusrid = data_obj.get_object_reference(cr, 1, 'base', 'group_tool_user')
#         dummy, extrmgrid = data_obj.get_object_reference(cr, 1, 'base', 'group_tool_manager')
        
        # Sharing
#         dummy, shareuserid = data_obj.get_object_reference(cr, 1, 'share', 'group_share_user')
        
        # Fleet
        dummy, fleetusrid = data_obj.get_object_reference(cr, 1, 'fleet', 'group_fleet_user')
        dummy, fleetmgrid = data_obj.get_object_reference(cr, 1, 'fleet', 'group_fleet_manager')
        
        # Marketing
        dummy, marketuserid = data_obj.get_object_reference(cr, 1, 'marketing', 'group_marketing_user')
        dummy, marketmgrid = data_obj.get_object_reference(cr, 1, 'marketing', 'group_marketing_manager')
        
        clear.update({
                         'sel_groups_'+ str(ptUsrid)+ '_'+str(ptMgr): False,
                         'sel_groups_'+ str(mUsrid)+ '_'+str(mMgrid): False,
                         'sel_groups_'+ str(stUser)+ '_'+str(stMgrid): False,
                         'sel_groups_'+ str(accinvid)+ '_'+str(accacnt)+ '_' +str(accMgrid): False,     
                         'sel_groups_'+str(soOwnid)+'_' + str(soAlledsid)+'_'+str(soMgrid) : False,
                         'sel_groups_'+ str(hrOfrid)+'_'+str(hrMgrid) : False,
                         'sel_groups_'+str(prgUsrid)+'_' +str(prgMgrid):False,
                         'sel_groups_'+str(knowUsrid):False,
                         'sel_groups_'+str(prchUsrid)+'_' +str(prchMgrid):False,
                         'sel_groups_'+str(mrkUsrid)+'_' +str(mrkMgrid):False,
                         'sel_groups_'+str(fltUsrid)+'_' +str(fltMgrid):False,
#                          'sel_groups_'+str(shrUsrid):False,
                         'sel_groups_'+str(prqUsrid)+'_' +str(prqMgrid):False,
                         'sel_groups_'+str(supMgr):False,
                         'sel_groups_'+str(adminaccessid)+'_' +str(settingid):False,
#                          'sel_groups_'+str(extrusrid)+'_' +str(extrmgrid):False,
#                          'sel_groups_'+str(shareuserid):False,
                         'sel_groups_'+str(fleetusrid)+'_' +str(fleetmgrid):False,
                         'sel_groups_'+str(marketuserid)+'_' +str(marketmgrid):False,
                       })
        return clear

    def write(self, cr, uid, ids, vals, context=None):
        
        data_obj = self.pool.get('ir.model.data')
        part_obj = self.pool.get("res.partner")
        
        dummy, ptUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_user')
        dummy, ptMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_portal_manager')
        
        dummy, mUsrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_user')
        dummy, mMgrid = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_group_manager')
        dummy, supMgr = data_obj.get_object_reference(cr, 1, 'magicemart', 'magicemart_supplier_portal')
        
        dummy, hrEmpid = data_obj.get_object_reference(cr, 1, 'base', 'group_user')

        if ids and isinstance(ids, int):
           ids = [ids] 
        
        for case in self.browse(cr, uid, ids, context=context):
            user_roles =  vals.get("user_roles", case.user_roles)
            
            if user_roles:
                if user_roles not in ('magicemart_group_user','magicemart_group_manager'):
                    clear = self.clear_allgroups(cr, uid, ids, context=context)
                    vals.update(clear)
                    groupids = self._get_belongingGroups(cr, uid, vals.get('user_roles', case.user_roles), context)
                    for fl in groupids:
                        vals['in_group_' + str(fl)] = True
                
                
            if vals.get('user_roles'):
                clear = self.clear_allgroups(cr, uid, ids, context=context)
                vals.update(clear)
                groupids = self._get_belongingGroups(cr, uid, vals.get('user_roles'), context)
                for fl in groupids:
                    vals['in_group_' + str(fl)] = True
                    
                    
            if user_roles == 'magicemart_portal_manager':
                if not vals.get("location_id",case.location_id):
                    raise osv.except_osv(_('Warning'),_('Please select the Customer Stock Location '))
                
                
            # To Make Magic User & Manager as False for Potal Group    
            elif user_roles in ('magicemart_group_user','magicemart_group_manager'):
                vals.update(
                            {'sel_groups_'+ str(ptUsrid)+'_' + str(ptMgr) : False, 
                             'sel_groups_'+str(supMgr):False,
                             'location_id':False, }
                                    )
                    
            elif user_roles in ('magicemart_portal_user','magicemart_portal_manager','magicemart_supplier_portal'):
                part = part_obj.browse(cr,uid,vals.get('partner_id',case.partner_id.id))
                if part:
                    vals.update({'name':part.name or False,})       

        return super(res_users, self).write(cr, uid, ids, vals, context=context)
        
res_users()