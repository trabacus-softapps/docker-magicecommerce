# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from openerp.osv import fields,osv
from lxml import etree
from openerp.osv.orm import setup_modifiers

class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    
    def part_address(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for case in self.browse(cr, uid, ids):
                res[case.id] = str(case.street and case.street or '') + str(case.street2 and case.street2 or '') + str(case.city and case.city or '') + str(case.state_id and case.state_id.name or '')  + str(case.zip and case.zip or '')
        return res
    
    _columns = {
            'seq_num'       :   fields.char("Reference", size=20),
            'source_location_id'    :   fields.many2one("stock.location",'Source Location'),
            'dest_location_id'      :   fields.many2one("stock.location",'Destination Location') ,              
            'product_ids'           :   fields.many2many('product.product', 'res_partner_prod_rel', 'partner_id', 'product_id', 'Products'),
            
            'address'               :   fields.function(part_address, string ="Address", store=False, type = "char"),
            
            'code'                  :   fields.char("Code", size=50),                
           }
    
    
    # sales Pricelist Read only for Portal Customer & Supplier
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
              
        user = self.pool.get('res.users').browse(cr,uid,uid)
              
        if context is None:
            context = {}
        res = super(res_partner, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        doc = etree.XML(res['arch'])
              
        cr.execute("select id from res_users where user_roles in ('magicemart_portal_user','magicemart_portal_manager','magicemart_supplier_portal') and  id=" +str(uid))
        portal_user = cr.fetchone() 
        if portal_user:
            if view_type == 'form':
                for node in doc.xpath("//field[@name='property_product_pricelist']"):
                    node.set('options', '{"no_open":True}')
                    node.set('readonly','1')
                    setup_modifiers(node,res['fields']['property_product_pricelist'])
                    res['arch'] = etree.tostring(doc)
                    
        return res
    
    
    # On creation of Partner creating 2 locations
    def create(self, cr, uid, vals, context=None):
        m_ac_obj = self.pool.get("account.account")
        comp_obj = self.pool.get("res.company")
        c_parent_id=False
        s_parent_id=False
        print vals,"vals"
        comp_ids = comp_obj.search(cr, uid,[('parent_id','=', False)])     
        if comp_ids:
            comp_ids=comp_ids[0]
        partner_id = vals.get('id') 
        cr.execute("""select id from stock_location where complete_name = 'Partner Locations / Customers / Stock'""")
        cust_loc = cr.fetchone()
        partner_loc = cust_loc and cust_loc[0] or 0
       
        loc_obj = self.pool.get('stock.location')
        new_id = super(res_partner, self).create(cr, uid, vals, context) 
        if vals.get('customer', False) == True:
            stkvals = {}
            if vals.get('seq_num'):
                stkvals['name'] = vals.get('seq_num') + ' - ' + 'Stock'
                stkvals['location_id'] = partner_loc
                stkvals['usage'] = 'customer'
                stkvals['chained_location_type'] = 'none'
                stkvals['chained_auto_packing'] = 'manual'
                stkvals['company_id'] = vals.get('company_id', False)
                stkvals['partner_id'] = new_id
                if vals.get('is_company',False) == True:
                    source=loc_obj.create(cr,uid, stkvals, context=context)
                    vals['source_location_id']=source
                    self.write(cr, uid, [new_id], {'source_location_id' :source }, context)
#         cr.execute("""select concat(split_part(name, ' ', 1),'/Consumed') from res_partner id =""" +str(partner_id))
#         cust_loc2 = cr.fetchone()
        if vals.get('customer', False) == True:
            stvals = {}
            if vals.get('seq_num'):
                stvals['name'] =  vals.get('seq_num') + ' - ' + 'Consumed'
                stvals['location_id'] = partner_loc
                stvals['usage'] = 'customer'
                stvals['chained_location_type'] = 'none'
                stvals['chained_auto_packing'] = 'manual'
                stvals['company_id'] = vals.get('company_id', False)
                stvals['partner_id'] = new_id
                if vals.get('is_company',False) == True:
                    dest=loc_obj.create(cr,uid, stvals, context=context)
                    vals['dest_location_id']=dest
                    self.write(cr, uid, [new_id], {'dest_location_id' :dest }, context)
                    
        return new_id        
    # Updating Reference with locations in stock location    
    def write(self, cr, uid, ids, vals, context=None):
        m_ac_obj = self.pool.get("account.account")
        comp_obj = self.pool.get("res.company")
        partner_obj = self.pool.get("res.partner")
        c_parent_id=False
        s_parent_id=False
        comp_ids = comp_obj.search(cr, uid,[('parent_id','=', False)])     
        if comp_ids:
            comp_ids=comp_ids[0]
        if not isinstance(ids,list):
            ids = [ids]
        for case in self.browse(cr, uid, ids):
            
            partner_id = vals.get('id') 
            cr.execute("""select id from stock_location where location_id = (select id from stock_location where complete_name = 'Partner Locations / Customers')""")
            cust_loc = cr.fetchone()
            partner_loc = cust_loc and cust_loc[0] or 0
            
            loc_obj = self.pool.get('stock.location')
            parent_id=loc_obj.search(cr,uid,[('complete_name','=','Partner Locations / Customers')])
            if parent_id:
                parent_id = parent_id[0]
            if vals.get('seq_num', '') or vals.get('is_company',''):
                stkvals = {}
                stkvals['name'] = vals.get('seq_num',case.seq_num ) + ' - ' + 'Stock' 
                stkvals['location_id'] = parent_id
                stkvals['usage'] = 'customer'
                stkvals['chained_location_type'] = 'none'
                stkvals['chained_auto_packing'] = 'manual'
                stkvals['company_id'] = vals.get('company_id',case.company_id.id)
                stkvals['partner_id'] = case.id
                if not case.source_location_id: 
#                     for part_id in partner_obj.browse(cr, uid, ids):
                        if vals.get('is_company',case.is_company) == True:
                            source=loc_obj.create(cr,uid, stkvals, context=context)
                            vals['source_location_id']=source
                if case.source_location_id:
                    source = loc_obj.write(cr,uid,[case.source_location_id.id], {'name': stkvals['name']}, context=context)
                
            if vals.get('seq_num','') or vals.get('is_company',''):
                stvals = {}
                stvals['name'] =  vals.get('seq_num', case.seq_num) + ' - ' + 'Consumed'
                stvals['location_id'] = parent_id
                stvals['usage'] = 'customer'
                stvals['chained_location_type'] = 'none'
                stvals['chained_auto_packing'] = 'manual'
                stvals['company_id'] = vals.get('company_id',case.company_id.id)
                stvals['partner_id'] = case.id
                if not case.dest_location_id:
#                     for part_id in partner_obj.browse(cr, uid, ids):
                        if vals.get('is_company',case.is_company) == True:
                            dest=loc_obj.create(cr,uid, stvals, context=context)
                            vals['dest_location_id']=dest
                if case.dest_location_id:
                    dest = loc_obj.write(cr,uid,[case.dest_location_id.id], {'name': stvals['name']}, context=context)
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)
        
   
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if context.get("show_contact", False):
                name =  "%s, %s" % (name,record.parent_id.name)
            else:
                
                if record.parent_id and not record.is_company:
                    name =  "%s, %s" % (record.parent_id.name, name)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
                name = name.replace('\n\n','\n')
                name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
#             res.append((record.id, name))
            if record.code:
                name = '[' + str(record.code) + ']' + str(record.name )
            else:
                name = record.name or ''
                
            res.append((record.id, name))
            
        return res
    
    
   
res_partner()