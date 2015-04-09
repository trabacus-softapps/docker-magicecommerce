from osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp import tools
from lxml import etree
from openerp.osv.orm import setup_modifiers
import time

class product_product(osv.osv):
    _inherit = "product.product"
    
    _columns = {
                'discount'       :   fields.float("Discount", digits=(16,2)),
                'discount_amt'   :   fields.float("Price After Discount", digits=(16,2)),
                #for email_template
                'create_uid'     :  fields.many2one('res.users','Create_uid'),
                'list_price_old' :  fields.float('Old Mrp'),
                'prod_qty'       :  fields.float('Quantity'),
                }
    
    
    def onchange_discper(self,cr, uid, ids, discount, list_price):
        res = {}
        if discount >0.00:
            disc_amt = (float(discount/100.0) * list_price)
            unit_amt = list_price - disc_amt
            res['discount_amt'] = unit_amt
        if discount == 0.00:
            res['discount_amt'] = list_price
        return {'value':res }
    
    
    def _stock_move_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict([(id, {'reception_count': 0, 'delivery_count': 0}) for id in ids])
        move_pool=self.pool.get('stock.move')
        moves = move_pool.read_group(cr, uid, [
            ('product_id', 'in', ids),
            ('picking_id.type', '=', 'in'),
            ('state','in',('confirmed','assigned','pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['reception_count'] = move['product_id_count']
        moves = move_pool.read_group(cr, uid, [
            ('product_id', 'in', ids),
            ('picking_id.type', '=', 'out'),
            ('state','in',('confirmed','assigned','pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['delivery_count'] = move['product_id_count']
        return res
     
    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}
         
        move_obj = self.pool.get('stock.move')
        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        shop_obj = self.pool.get('sale.shop')
        user_obj = self.pool.get('res.users')
        partner_obj = self.pool.get('res.partner')
          
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        if not ids:
            return res
        if context.get('shop', False):
            if context.get('shop', False)== 1:
                raise osv.except_osv(_('Warning'), _('Please Select Branch Company Shop in the main Form.'))
            warehouse_id = shop_obj.read(cr, uid, int(context['shop']), ['warehouse_id'])['warehouse_id'][0]
            if warehouse_id:
                context['warehouse'] = warehouse_id
 
        if context.get('warehouse', False):
            lot_id = warehouse_obj.read(cr, uid, int(context['warehouse']), ['lot_stock_id'])['lot_stock_id'][0]
            if lot_id:
                context['location'] = lot_id
 
        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = location_obj.search(cr, uid, [('name','ilike',context['location'])], context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
#             Getting stock location of customer
            cr.execute("""select source_location_id,dest_location_id from res_partner where id = (select partner_id from res_users where id = """+str(uid)+""")""")
            loc_ids = cr.fetchone()
            if loc_ids and loc_ids[0]:
                location_ids = loc_ids
            else:
                wids = warehouse_obj.search(cr, uid, [], context=context)
                if not wids:
                    return res
                for w in warehouse_obj.browse(cr, uid, wids, context=context):
                    location_ids.append(w.lot_stock_id.id)
        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = location_obj.search(cr, uid, [('location_id', 'child_of', location_ids)])
            location_ids = child_location_ids or location_ids
         
        # this will be a dictionary of the product UoM by product id
        product2uom = {}
        uom_ids = []
        for product in self.read(cr, uid, ids, ['uom_id'], context=context):
            product2uom[product['id']] = product['uom_id'][0]
            uom_ids.append(product['uom_id'][0])
        # this will be a dictionary of the UoM resources we need for conversion purposes, by UoM id
        uoms_o = {}
        for uom in self.pool.get('product.uom').browse(cr, uid, uom_ids, context=context):
            uoms_o[uom.id] = uom
 
        results = []
        results2 = []
 
        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = [tuple(location_ids),tuple(location_ids),tuple(ids),tuple(states)]
        if from_date and to_date:
            date_str = "date>=%s and date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "date>=%s"
            date_values = [from_date]
        elif to_date:
            date_str = "date<=%s"
            date_values = [to_date]
        if date_values:
            where.append(tuple(date_values))
 
        prodlot_id = context.get('prodlot_id', False)
        prodlot_clause = ''
        if prodlot_id:
            prodlot_clause = ' and prodlot_id = %s '
            where += [prodlot_id]
            
        if 'in' in what:
            cr.execute(
                            'select sum(product_qty), product_id, product_uom '\
                            'from stock_move '\
                            'where location_id NOT IN %s '\
                            'and location_dest_id IN %s '\
                            'and product_id IN %s '\
                            'and state IN %s ' + (date_str and 'and '+date_str+' ' or '') +' '\
                            + prodlot_clause + 
                            'group by product_id,product_uom',tuple(where))
            results = cr.fetchall()
        if 'out' in what:
            # all moves from a location in the set to a location out of the set
            cr.execute("""select source_location_id,dest_location_id from res_partner where id = (select partner_id from res_users where id = """+str(uid)+""")""")
            loc_ids = cr.fetchone()
            if loc_ids and loc_ids[0]:
                cr.execute(
                                'select sum(product_qty), product_id, product_uom '\
                                'from stock_move '\
                                'where location_id IN %s '\
                                'and location_dest_id IN %s '\
                                'and product_id  IN %s '\
                                'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
                                + prodlot_clause + 
                                'group by product_id,product_uom',tuple(where))
            else:
                cr.execute(
                                'select sum(product_qty), product_id, product_uom '\
                                'from stock_move '\
                                'where location_id IN %s '\
                                'and location_dest_id NOT IN %s '\
                                'and product_id  IN %s '\
                                'and state in %s ' + (date_str and 'and '+date_str+' ' or '') + ' '\
                                + prodlot_clause + 
                                'group by product_id,product_uom',tuple(where))
            results2 = cr.fetchall()
             
        # Get the missing UoM resources
        uom_obj = self.pool.get('product.uom')
        uoms = map(lambda x: x[2], results) + map(lambda x: x[2], results2)
        if context.get('uom', False):
            uoms += [context['uom']]
        uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
        if uoms:
            uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
            for o in uoms:
                uoms_o[o.id] = o
                 
        #TOCHECK: before change uom of product, stock move line are in old uom.
        context.update({'raise-exception': False})
        # Count the incoming quantities
        for amount, prod_id, prod_uom in results:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                     uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] += amount
        # Count the outgoing quantities
        for amount, prod_id, prod_uom in results2:
            amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                    uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
            res[prod_id] -= amount
        return res

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        """ Finds the incoming and outgoing quantity of product.
        @return: Dictionary of values
        """
        if not field_names:
            field_names = []
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        for f in field_names:
            c = context.copy()
            if f == 'qty_available':
                c.update({ 'states': ('done',), 'what': ('in', 'out') })
            if f == 'virtual_available':
                c.update({ 'states': ('confirmed','waiting','assigned','done'), 'what': ('in', 'out') })
            if f == 'incoming_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('in',) })
            if f == 'outgoing_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('out',) })
            stock = self.get_product_available(cr, uid, ids, context=c)
            for id in ids:
                res[id][f] = stock.get(id, 0.0)
        return res
     
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:context = {}
          
        res = super(product_product, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        cr.execute("""select uid from res_groups_users_rel where gid=
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Customer Portal' ) and name = 'Manager') and uid = """+str(uid))
        portal_user = cr.fetchone() 
        portal_group = portal_user and portal_user[0]
        doc = etree.XML(res['arch'])
        if uid == portal_group:
                for node in doc.xpath("//form[@string='Product']"):
                        node.set('create', _('false'))
                        node.set('edit', _('false'))
                for node in doc.xpath("//tree[@string='Products']"):
                    node.set('create', _('false'))                
                for node in doc.xpath("//kanban"):
                        node.set('create', _('false'))        
                res['arch'] = etree.tostring(doc)    
        return res
    
    def send_mail(self,cr, uid, ids, context=None):
        """ To send emails for customer when the mrp of product is getting changed"""
        
        to_emails = ''
        partner_ids = []
        case = self.browse(cr, uid, ids)[0]
        mail_obj = self.pool.get("mail.mail")
        partner_obj = self.pool.get("res.partner")
        email_obj = self.pool.get('email.template')
        wiz_obj = self.pool.get('mail.compose.message')
        
        if context is None:
            context = {}
        vals = {}
        
        #to get all customers who are mapped to this product
        cr.execute("select partner_id from res_partner_prod_rel where product_id =%s"%(case.id))
        partner_ids = [x[0] for x in cr.fetchall()]
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'magicemart', 'email_template_mrp_rule')
        vals.update(wiz_obj.onchange_template_id(cr, uid, [], template.id, 'comment', 'product.product',case.id,context=context)['value'])
        vals.update({
                'template_id' : template.id,
                'partner_ids' : [(6,0,partner_ids)],
                'model'       : 'product.product',
                'res_id'      : case.id
                })
        context.update({
                        'active_id' : case.id,
                        'active_model' : 'product.product'
                        })
        wiz_id = wiz_obj.create(cr, uid, vals, context=context)
        wiz_obj.send_mail(cr, uid, [wiz_id], context=context)
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        #TO Send mails for customers
        for case in self.browse(cr, uid, ids):
            if vals.get('list_price'):
                vals.update({'list_price_old':case.list_price})
        res = super(product_product,self).write(cr, uid, ids, vals, context=context)
#         if vals.get('list_price'):
#             self.send_mail(cr, uid, ids, context=None)
        return res
    
product_product()

class ir_rule(osv.osv):
    _inherit= 'ir.rule'
     
#     ********* Overridden Rule For Product**********
    def domain_get(self, cr, uid, model_name, mode='read', context=None):
        # _where_calc is called as superuser. This means that rules can
        # involve objects on which the real uid has no acces rights.
        # This means also there is no implicit restriction (e.g. an object
        # references another object the user can't see).
        " This function is to set the rule domain for product_product object based on the user permissions"
#         print "Model Name", model_name
        dom = self._compute_domain(cr, uid, model_name, mode)
        cr.execute("""select uid from res_groups_users_rel where gid in (select id  from res_groups where name in ('User', 'Manager') and  
                      category_id in (select id from ir_module_category where name = 'Customer Portal'))""")
        custgrp_ids = [x[0] for x in cr.fetchall()]
             
        if uid in custgrp_ids:
            if dom:
                if context and model_name == 'product.template':
                    cr.execute("""select source_location_id,dest_location_id from res_partner where id = (select partner_id from res_users where id = """+str(uid)+""")""")
                    loc_ids = cr.fetchone()
                    if loc_ids and loc_ids[0]:
                        cr.execute("""
                                    select distinct(a.product) 
                                    from(
                                      select sl.product_id as product from  sale_order_line sl 
                                      inner join sale_order s on s.id = sl.order_id 
                                      inner join res_partner p on p.id = s.partner_id 
                                      inner join res_users u on u.partner_id = p.id
                                      where u.id= """+str(uid)+"""
                                      union all 
                                      select pr.product_id as product from res_partner_prod_rel pr inner join res_partner p on p.id=pr.partner_id
                                      where p.id = (select partner_id from res_users where id = """+str(uid)+"""))a""")
                        user_ids = cr.fetchall()
                        dom = ['&'] + dom + [('id', 'in', [x[0] for x in user_ids])]
                query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, dom, active_test=False)
                return query.where_clause, query.where_clause_params, query.tables
            return [], [], ['"' + self.pool[model_name]._table + '"']
      
        cr.execute("""select distinct(uid) from res_groups_users_rel 
                        where gid in (select id  from res_groups where name in ('Supplier Manager') and  
                        category_id in (select id from ir_module_category where name = 'Supplier Portal'))""")
        supgrp_ids = [z[0] for z in cr.fetchall()]
        if uid in supgrp_ids:
            if dom:
               if context and model_name == 'product.template':
#                    cr.execute("""select source_location_id,dest_location_id from res_partner where id = (select partner_id from res_users where id = """+str(uid)+""")""")
#                    loc_ids = cr.fetchone()
#                    if loc_ids and loc_ids[0]:
                       cr.execute("""
                                   select distinct(a.product) 
                                   from(
                                     select m.product_id as product
                                     from stock_move m
                                     inner join stock_picking sp on sp.id = m.picking_id
                                     inner join res_partner rp on rp.id = sp.partner_id
                                     inner join res_users u on u.partner_id = rp.id
                                     where m.state='done' and sp.type='in' and u.id ="""+str(uid)+"""
                                     union all 
                                     select pr.product_id as product from res_partner_prod_rel pr inner join res_partner p on p.id=pr.partner_id
                                     where p.id = (select partner_id from res_users where id = """+str(uid)+"""))a""")
                       user_ids = cr.fetchall()
                       dom = ['&'] + dom + [('id', 'in', [x[0] for x in user_ids])]
               query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, dom, active_test=False)
               return query.where_clause, query.where_clause_params, query.tables
           
# If above both conditions not satisfies means, standard should work
        if uid not in custgrp_ids and uid not in  supgrp_ids:
            if dom:
                query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, dom, active_test=False)
                return query.where_clause, query.where_clause_params, query.tables
        return [], [], ['"' + self.pool[model_name]._table + '"']
ir_rule()     

# Partner Ledger Report
class account_partner_ledger(osv.osv_memory):
    _inherit='account.partner.ledger'
    _columns={'partner_id':fields.many2one('res.partner','Partner',domain="[('parent_id','=',False)]"),
              }
    _defaults={'filter':'filter_date',
                'result_selection': 'customer_supplier',}
    
    def onchange_filter(self, cr, uid, ids, filter='filter_date', fiscalyear_id=False, context=None):
        res = super(account_partner_ledger, self).onchange_filter(cr, uid, ids, filter=filter, fiscalyear_id=fiscalyear_id, context=context)
        if filter in ['filter_date']:
            fiscal_obj = self.pool.get('account.fiscalyear')
            fiscalyear=False
            if fiscalyear_id:
                fiscalyear = fiscal_obj.browse(cr,uid,fiscalyear_id)                
            res['value'].update({'period_from': False, 'period_to': False, 'date_from':fiscalyear and fiscalyear.date_start or False  ,'date_to': fiscalyear and fiscalyear.date_stop or False})
        return res
        
    def pre_print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data['form'].update(self.read(cr, uid, ids, ['result_selection'], context=context)[0])
        data['form'].update(self.read(cr, uid, ids, ['partner_id'], context=context)[0])
        return data

account_partner_ledger()

class res_company(osv.osv):
    _inherit = "res.company"

    _columns={
              'sign'    :   fields.binary('Signature'),
              
              }

res_company()


class order_product(osv.osv_memory):
    _name = 'order.product'
    _columns = {
                'order_id'     : fields.many2one('order.product.wiz','Order'),
                'product_id'   : fields.many2one('product.product','Product'),
                'image'        : fields.binary('Image'),
                'prod_qty'     : fields.float('Quantity')
                }
order_product() 
                


class order_product_wiz(osv.osv_memory):
    _name = 'order.product.wiz'
    _description = " Order Products"
    _columns = {
                'product_ids'   : fields.one2many('order.product', 'order_id', 'Product')
                }
    
    def default_get(self, cr, uid, fields, context=None):
        prod_obj = self.pool.get('product.product')
        val = []
        if context is None: context = {}
        res = super(order_product_wiz, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        for case in prod_obj.browse(cr, uid, active_ids):
            val.append({
                        'product_id':case.id,
                        'prod_qty' : 1.0,
                        'image'    : case.image
                        })
        res.update(product_ids=val)
        return res
    
    def prepare_order(self, cr, uid, ids, context=None):
        """ Return Sales order for customer or Purchase Order for supplier"""
        
        sale_obj = self.pool.get('sale.order')
        po_obj = self.pool.get('purchase.order')
        user = self.pool.get('res.users').browse(cr, uid, uid)
        
        if user.partner_id.customer :
            vals = sale_obj.onchange_partner_id(cr, uid, ids, user.partner_id.id, context=context)['value']
        else:
            vals = po_obj.onchange_partner_id(cr, uid, ids, user.partner_id.id)['value']
            vals.update(po_obj.onchange_company_id(cr, uid, ids, user.company_id.id, context=context)['value'])
            vals.update(po_obj.onchange_warehouse_id(cr, uid, ids, vals.get('warehouse_id',False))['value'])
            vals.update(po_obj.onchange_pricelist(cr, uid, ids, vals.get('pricelist_id',False), context=context))
            
        vals.update({'partner_id': user.partner_id.id})
        return vals
    
    def create_orders(self, cr, uid, ids, context=None):
        """ To create Sales Order from products """
        
        user = self.pool.get('res.users').browse(cr, uid, uid)
        sale_obj = self.pool.get('sale.order')
        lines = []
        today = time.strftime('%Y-%m-%d')
        user = self.pool.get('res.users').browse(cr, uid, uid)
        prod_obj = self.pool.get('product.product')
        line_obj = self.pool.get('sale.order.line')
        po_obj = self.pool.get('purchase.order')
        poline_obj = self.pool.get('purchase.order.line')
        
        res_id = False
        name = model = ''
        
        #preparing Order (Sale Order/ Purchase Order)
        order_vals = self.prepare_order(cr, uid, ids, context=context)
        for case in self.browse(cr, uid, ids):
            if user.partner_id.customer :
                for p in case.product_ids:
                    # preparing sales order Lines
                    vals = line_obj.product_id_change(cr, uid, ids, order_vals['pricelist_id'], p.product_id.id, p.prod_qty,
                                               False, p.prod_qty, False, '', user.partner_id.id,
                                               False, True, today, False, False, False, context=context)['value']
                    vals.update({
                                 'product_id':p.product_id.id,
                                 'product_uom_qty':p.prod_qty,
                                 'tax_id' : [(6, 0, [x for x in vals['tax_id']])]
                                 })
                    
                    lines.append(vals)
                order_lines = map(lambda x: (0, 0, x), lines)
                order_vals.update({'order_line':order_lines})
                sale_id = sale_obj.create(cr, uid, order_vals, context=context)
            
            else :
                vals = {}
                order_lines = {}
                lines = []
                for p in case.product_ids:
                    # preparing purchase order Lines
                    vals = poline_obj.onchange_product_id(cr, uid, ids, order_vals['pricelist_id'], p.product_id.id, p.prod_qty, False,
                                            user.partner_id.id, today, False, False,False, False, context=context)['value']
                    vals.update({
                                 'product_id':p.product_id.id,
                                 'product_qty':p.prod_qty,
                                 'taxes_id' : [(6, 0, [x for x in vals['taxes_id']])]
                                 })
                    lines.append(vals)
                order_lines = map(lambda x: (0, 0, x), lines)
                order_vals.update({'order_line':order_lines})
                po_id = po_obj.create(cr, uid, order_vals, context=context)
            
        
        if user.partner_id.customer:
            view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'view_order_form')
            res_id = sale_id
            name = 'Sales Order'
            model = 'sale.order'
            
        else:
            view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
            res_id = po_id
            name = 'Purchase Order'
            model = 'purchase.order'
        
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _(name),
            'res_model': model,
            'res_id': res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }
    
order_product_wiz()


            
                
