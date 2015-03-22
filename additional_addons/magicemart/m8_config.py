# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import math
import re
import time


from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp import tools
from lxml import etree
from openerp.osv.orm import setup_modifiers
import time
import openerp.addons.decimal_precision as dp
from openerp.osv import osv, fields, expression

class product_template(osv.osv):
    _inherit = "product.template"
    
    # TO show Untax amount , Tax Name in Product Tree view
    def _amount_calculation(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        tax_obj = self.pool.get("account.tax")
        comp_obj = self.pool.get("res.company")
        user_obj = self.pool.get("res.users")
        product_obj = self.pool.get("product.product")
        acc_tx_obj = self.pool.get("account.tax")
         
#         for p in product_obj.browse(cr, uid, ids):
        user = user_obj.browse(cr, uid, uid)
        comp_id = []
        prod_ids =  product_obj.search(cr, uid, [('product_tmpl_id', 'in', ids)])
        for prod in product_obj.browse(cr, uid, prod_ids):
            res[prod.product_tmpl_id.id] = {
                        'untax_amt' : 0.0,
                        'tax_name'   : '',
                      }
               
            if prod.taxes_id:
               cr.execute("select tax_id from product_taxes_rel where prod_id =%s"%(prod.id))
               tax_id = [x[0] for x in cr.fetchall()]
               
               """ through cr.execute fetches all the records irrespective of company so need 
               pass this to ORM search method then it will not throw denied warning"""
               
               tax_ids = tax_obj.search(cr, uid, [('id','in',tax_id)])
               
               if tax_ids:
                   for tax in tax_obj.browse(cr, uid, tax_ids):
                       if not user.company_id.parent_id : 
                           comp_id = comp_obj.search(cr, uid, [('name','ilike','%bangalore%')]) 
                           if comp_id:
                               comp_id = comp_id[0]
                           
                       if user.company_id.id == tax.company_id.id or comp_id == tax.company_id.id:
                       
                           if tax.price_include == True:
                               if prod.discount:
                                   tax_amt = acc_tx_obj.compute_all(cr, uid, [tax], prod.discount_amt, 1, prod.id, None, None)
                                   res[prod.product_tmpl_id.id]['untax_amt'] = prod.discount_amt - tax_amt["taxes"][0]["amount"]
                                   
                               else :
                                   
                                   tax_amt = acc_tx_obj.compute_all(cr, uid, [tax], prod.product_tmpl_id.list_price, 1, prod.id, None, None)
                                   res[prod.product_tmpl_id.id]['untax_amt'] = prod.product_tmpl_id.list_price - tax_amt["taxes"][0]["amount"]
                               res[prod.product_tmpl_id.id]['tax_name'] = tax.name
                               
                           else:
                               res[prod.product_tmpl_id.id]['untax_amt'] = prod.discount_amt or prod.product_tmpl_id.list_price
                               res[prod.product_tmpl_id.id]['tax_name'] = tax.name   
        return res
               
    def _pricelist_amount(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        sale_obj = self.pool.get("sale.order")
        user_obj = self.pool.get("res.users")
        sale_line_obj = self.pool.get("sale.order.line")
#         user_obj = self.pool.get("res.users")
#         u_id = context.get("uid",uid)
        user = user_obj.browse(cr, uid, context.get("uid",uid))
        part = user.partner_id
        object_name = self._name + ',' + str(part.id)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
         
        for case in self.browse(cr, uid, ids):
            amount = sale_line_obj.product_id_change(cr, uid, [], pricelist, case.id, qty=0,
                    uom=False, qty_uos=0, uos=False, name='', partner_id=False,
                    lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=context)
            if 'value' in amount and  'price_unit' in amount['value']:
                res[case.id] = amount['value']['price_unit']
            else:
                res[case.id] = case.list_price
        return res
#     
    _columns = {
                'discount'       :   fields.float("Discount", digits=(16,2)),
                'discount_amt'   :   fields.float("Price After Discount", digits=(16,2)),
                'untax_amt'      :   fields.function(_amount_calculation, string='Untax Amount',store=False, type = 'float', multi='all'),
                'tax_name'       :   fields.function(_amount_calculation, string='Tax Percentage',store=False, type ='char',size=100, multi='all'),
                
                # Pricelist Amount
                'pricelist_amt'   :   fields.function(_pricelist_amount, string ="Amount", store=False, type = "float" )
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
    
    #inheritted
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        condition = ''
        ids =[]
        user = self.pool.get('res.users').browse(cr, uid, uid)
        context =  context and dict(context) or {}
        
        # customised product split search
        if context.get('custom_search',False):
            for argu in args:
                if isinstance(argu, (list)):
                    if isinstance(argu[2], (str,unicode)):
                        for name in argu[2].split(' '):
                            if condition:
                                condition += 'and'
                            condition = "name ilike '%"+name+"%' "
                        
                        cr.execute('select id from product_template where '+condition)
                        
                        ids = [x[0] for x in cr.fetchall()]
                        args.append(['id','in',ids])
                        args.remove(argu)
            
        return super(product_template, self).search(cr, uid, args, offset, limit, order, context, count)


    
    
product_template()

class product_product(osv.osv):
    _inherit = "product.product"

    # Overriden Searching all the string in product name
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        temp = []
        
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = []
            
            if operator in positive_operators:
                ids = self.search(cr, user, [('default_code','=',name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('barcode','=',name)]+ args, limit=limit, context=context)
                    
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = set(self.search(cr, user, args + [('default_code', operator, name)], limit=limit, context=context))
                
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    # Searching all the strings in product name
                    name.split(' ')
                    
                    for i in name.split(' '):
                        temp.append(('name', operator, i))
                    ids.update(self.search(cr, user, args + temp, limit=limit2, context=context))
                        
                ids = list(ids)
                
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', ('default_code', operator, name), ('name', operator, name)], limit=limit, context=context)
                
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
                    
        else:
            
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        
        return result



    # Overriden (No Changes)
    def _search_product_quantity(self, cr, uid, obj, name, domain, context):
        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty'), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
            assert isinstance(value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            product_ids = self.search(cr, uid, [], context=context)
            ids = []
            if product_ids:
                #TODO: use a query instead of this browse record which is probably making the too much requests, but don't forget
                #the context that can be set with a location, an owner...
                for element in self.browse(cr, uid, product_ids, context=context):
                    if eval(str(element[field]) + operator + str(value)):
                        ids.append(element.id)
            res.append(('id', 'in', ids))
        return res

    # Overriden to get the products qty based on location id there means else getting all warehouse qty
    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        if not context:
            context = {}
        context = dict(context)
        location_ids = []
        res = {}
#       Getting stock location of customer
        cr.execute("""select source_location_id from res_partner where id = (select partner_id from res_users where id = """+str(uid)+""")""")
        loc_ids = cr.fetchone()
        
        if loc_ids and loc_ids[0]:
            location_ids = loc_ids
            
        if location_ids:
            context.update({'location':location_ids})
            
        field_names = field_names or []

        domain_products = [('product_id', 'in', ids)]
        domain_quant, domain_move_in, domain_move_out = self._get_domain_locations(cr, uid, ids, context=context)
        domain_move_in += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel'))] + domain_products
        domain_move_out += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel'))] + domain_products
        domain_quant += domain_products
        
        if context.get('lot_id') or context.get('owner_id') or context.get('package_id'):
            if context.get('lot_id'):
                domain_quant.append(('lot_id', '=', context['lot_id']))
                
            if context.get('owner_id'):
                domain_quant.append(('owner_id', '=', context['owner_id']))
                
            if context.get('package_id'):
                domain_quant.append(('package_id', '=', context['package_id']))
            moves_in = []
            moves_out = []
            
        else:
            moves_in = self.pool.get('stock.move').read_group(cr, uid, domain_move_in, ['product_id', 'product_qty'], ['product_id'], context=context)
            moves_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_out, ['product_id', 'product_qty'], ['product_id'], context=context)

        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))
        res = {}
        
        for id in ids:
            res[id] = {
                'qty_available': quants.get(id, 0.0),
                'incoming_qty': moves_in.get(id, 0.0),
                'outgoing_qty': moves_out.get(id, 0.0),
                'virtual_available': quants.get(id, 0.0) + moves_in.get(id, 0.0) - moves_out.get(id, 0.0),
            }

        return res


    
    _columns = {
#                 'discount'       :   fields.float("Discount", digits=(16,2)),
#                 'discount_amt'   :   fields.float("Price After Discount", digits=(16,2)),
                #for email_template
                'create_uid'     :  fields.many2one('res.users','Create_uid'),
                'list_price_old' :  fields.float('Old Mrp'),
                'prod_qty'       :  fields.float('Quantity'),
                
                
                'qty_available': fields.function(_product_available, multi='qty_available',
                    type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
                    string='Quantity On Hand',
                    fnct_search=_search_product_quantity,
                    help="Current quantity of products.\n"
                         "In a context with a single Stock Location, this includes "
                         "goods stored at this Location, or any of its children.\n"
                         "In a context with a single Warehouse, this includes "
                         "goods stored in the Stock Location of this Warehouse, or any "
                         "of its children.\n"
                         "stored in the Stock Location of the Warehouse of this Shop, "
                         "or any of its children.\n"
                         "Otherwise, this includes goods stored in any Stock Location "
                         "with 'internal' type."),
                'virtual_available': fields.function(_product_available, multi='qty_available',
                    type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
                    string='Forecast Quantity',
                    fnct_search=_search_product_quantity,
                    help="Forecast quantity (computed as Quantity On Hand "
                         "- Outgoing + Incoming)\n"
                         "In a context with a single Stock Location, this includes "
                         "goods stored in this location, or any of its children.\n"
                         "In a context with a single Warehouse, this includes "
                         "goods stored in the Stock Location of this Warehouse, or any "
                         "of its children.\n"
                         "Otherwise, this includes goods stored in any Stock Location "
                         "with 'internal' type."),
                'incoming_qty': fields.function(_product_available, multi='qty_available',
                    type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
                    string='Incoming',
                    fnct_search=_search_product_quantity,
                    help="Quantity of products that are planned to arrive.\n"
                         "In a context with a single Stock Location, this includes "
                         "goods arriving to this Location, or any of its children.\n"
                         "In a context with a single Warehouse, this includes "
                         "goods arriving to the Stock Location of this Warehouse, or "
                         "any of its children.\n"
                         "Otherwise, this includes goods arriving to any Stock "
                         "Location with 'internal' type."),
                'outgoing_qty': fields.function(_product_available, multi='qty_available',
                    type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
                    string='Outgoing',
                    fnct_search=_search_product_quantity,
                    help="Quantity of products that are planned to leave.\n"
                         "In a context with a single Stock Location, this includes "
                         "goods leaving this Location, or any of its children.\n"
                         "In a context with a single Warehouse, this includes "
                         "goods leaving the Stock Location of this Warehouse, or "
                         "any of its children.\n"
                         "Otherwise, this includes goods leaving any Stock "
                         "Location with 'internal' type."),
                        
                     
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
    

    

    """ TO BE UNCOMENT"""  
#     def _stock_move_count(self, cr, uid, ids, field_name, arg, context=None):
#         res = dict([(id, {'reception_count': 0, 'delivery_count': 0}) for id in ids])
#         move_pool=self.pool.get('stock.move')
#         moves = move_pool.read_group(cr, uid, [
#             ('product_id', 'in', ids),
#             ('picking_id.type', '=', 'in'),
#             ('state','in',('confirmed','assigned','pending'))
#         ], ['product_id'], ['product_id'])
#         for move in moves:
#             product_id = move['product_id'][0]
#             res[product_id]['reception_count'] = move['product_id_count']
#         moves = move_pool.read_group(cr, uid, [
#             ('product_id', 'in', ids),
#             ('picking_id.type', '=', 'out'),
#             ('state','in',('confirmed','assigned','pending'))
#         ], ['product_id'], ['product_id'])
#         for move in moves:
#             product_id = move['product_id'][0]
#             res[product_id]['delivery_count'] = move['product_id_count']
#         return res
      
     
    
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
        
    
    def product_filter(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        cr.execute("""
                     
                        select p.id 
                        from 
                        (    select distinct(a.product) as product_id
                            from(
                                select sl.product_id as product from  sale_order_line sl 
                                inner join sale_order s on s.id = sl.order_id 
                                inner join res_partner p on p.id = s.partner_id 
                                inner join res_users u on u.partner_id = p.id
                                where u.id = """ + str(context.get("uid",uid)) + """
                         
                                union all 
                                 
                                (   select pr.product_id as product from res_partner_prod_rel pr inner join res_partner p on p.id=pr.partner_id
                                    where p.id = (select partner_id from res_users where id = """ + str(context.get("uid",uid)) + """)
                                )
                         
                            )a
                         
                        ) b
                        inner join product_product p on b.product_id = p.id
                        inner join product_template pt on pt.id = p.product_tmpl_id
                        where pt.company_id is null or pt.company_id = (select u.company_id from res_users u where u.id = """ + str(context.get("uid",uid)) + """)
                         
                    """)
        prod_ids = cr.fetchall()
         
        return prod_ids 
         
        
#     ********* Overridden Rule For Product**********
    def domain_get(self, cr, uid, model_name, mode='read', context=None):
        # _where_calc is called as superuser. This means that rules can
        # involve objects on which the real uid has no acces rights.
        # This means also there is no implicit restriction (e.g. an object
        # references another object the user can't see).
        " This function is to set the rule domain for product_product object based on the user permissions"
        if not context:
            context = {}
        newdom = []
         
        dom = self._compute_domain(cr, uid, model_name, mode) or []
        cr.execute("""select uid from res_groups_users_rel where gid in (select id  from res_groups where name in ('User', 'Manager') and  
                      category_id in (select id from ir_module_category where name = 'Customer Portal'))""")
        custgrp_ids = [x[0] for x in cr.fetchall()]
                 
        if uid in custgrp_ids or context.get("uid") in custgrp_ids:
#             if dom:
            if model_name == 'product.product':
                cr.execute("""select source_location_id from res_partner where id = (select partner_id from res_users where id = """+str(context.get("uid",uid))+""")""")
                loc_ids = cr.fetchone()
                
                if loc_ids and loc_ids[0]:
                    cr.execute("""
                    
                        select p.id 
                        from 
                        (    select distinct(a.product) as product_id
                            from(
                                select sl.product_id as product from  sale_order_line sl 
                                inner join sale_order s on s.id = sl.order_id 
                                inner join res_partner p on p.id = s.partner_id 
                                inner join res_users u on u.partner_id = p.id
                                where u.id = """ + str(context.get("uid",uid)) + """
                        
                                union all 
                                
                                (   select pr.product_id as product from res_partner_prod_rel pr inner join res_partner p on p.id=pr.partner_id
                                    where p.id = (select partner_id from res_users where id = """ + str(context.get("uid",uid)) + """)
                                )
                        
                            )a
                        
                        ) b
                        inner join product_product p on b.product_id = p.id
                        inner join product_template pt on pt.id = p.product_tmpl_id
                        where pt.company_id is null or pt.company_id = (select u.company_id from res_users u where u.id = """ + str(context.get("uid",uid)) + """)
                        
                    """)
                    prod_ids = cr.fetchall()
                    print"Count Prod_id--------",len(prod_ids)
                    
                    
                    if prod_ids:
                        newdom = [('id', 'in', [x[0] for x in prod_ids])]
                        
                    else:   
                        newdom = [('id', '=',1)]
                        
                    if len(dom):
                        domain = list((['&'] + dom + newdom))
                        
                    else:
                        domain = list(newdom)
                    
                    query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, domain, active_test=False)
                    return query.where_clause, query.where_clause_params, query.tables
#             return [], [], ['"' + self.pool[model_name]._table + '"']
           
        cr.execute("""select distinct(uid) from res_groups_users_rel 
                        where gid in (select id  from res_groups where name in ('Supplier Manager') and  
                        category_id in (select id from ir_module_category where name = 'Supplier Portal'))""")
        supgrp_ids = [z[0] for z in cr.fetchall()]
        
        if uid in supgrp_ids:
#             if dom:
           if model_name == 'product.product':
               cr.execute("""
                    select p.id 
                        from 
                        (    select distinct(a.product) as product_id
                            from(
                               select m.product_id as product
                               from stock_move m
                               inner join stock_picking sp on sp.id = m.picking_id
                               inner join res_partner rp on rp.id = sp.partner_id
                               inner join res_users u on u.partner_id = rp.id
                               left outer join stock_picking_type spt on spt.id = sp.picking_type_id
                               where m.state='done' and spt.code='incoming' and u.id = """ + str(context.get("uid",uid)) + """
                        
                                union all 
                                
                                    (    select pr.product_id as product from res_partner_prod_rel pr inner join res_partner p on p.id=pr.partner_id
                                         where p.id = (select partner_id from res_users where id = """ + str(context.get("uid",uid)) + """
                                    )
                                )
                        )a
                        
                        ) b
                        inner join product_product p on b.product_id = p.id
                        inner join product_template pt on pt.id = p.product_tmpl_id
                        where pt.company_id is null or pt.company_id = (select u.company_id from res_users u where u.id = """ + str(context.get("uid",uid)) + """)


                             """)
               prod_ids = cr.fetchall()
               
               if prod_ids:
                   newdom = [('id', 'in', [x[0] for x in prod_ids])]
               else:   
                   newdom = [('id', '=',1)]
                    
               if len(dom):
                   domain = list((['&'] + dom + newdom))
               else:
                   domain = list(newdom)
               query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, domain, active_test=False)
               return query.where_clause, query.where_clause_params, query.tables
                
# If above both conditions not satisfies means, standard should work
        if model_name == 'product.product':
            if uid not in custgrp_ids and uid not in  supgrp_ids: 
                if dom:
                    query = self.pool[model_name]._where_calc(cr, SUPERUSER_ID, dom, active_test=False)
                    return query.where_clause, query.where_clause_params, query.tables
        else:
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
            vals.update(po_obj.onchange_picking_type_id(cr, uid, ids, vals.get('picking_type_id',False),context=context)['value'])
            vals.update(po_obj.onchange_pricelist(cr, uid, ids, vals.get('pricelist_id',False), context=context))
            
        vals.update({'partner_id': user.partner_id.id})
        return vals
    
    def create_orders(self, cr, uid, ids, context=None):
        """ To create Sales Order from products """
        
        user = self.pool.get('res.users').browse(cr, uid, uid)
        sale_obj = self.pool.get('sale.order')
        lines = []
        today = time.strftime('%Y-%m-%d %H:%M:%S')
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


            
                