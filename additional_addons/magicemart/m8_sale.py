# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from datetime import datetime, timedelta
import time
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import amount_to_text_softapps
from lxml import etree
from openerp.osv.orm import setup_modifiers
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class sale_order(osv.osv):
    _inherit = 'sale.order'
    
    # Many2one Arrow button should not come for Customer Portal User and Manager
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
         
        user = self.pool.get('res.users').browse(cr,uid,uid)
         
        if context is None:
            context = {}
        res = super(sale_order, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        doc = etree.XML(res['arch'])
# #         print 'res[',res['arch']
#         if view_type == 'form' :
#             print res['fields']['warehouse_id']
#             res['fields']['order_line']['views']['form']['fields']['price_unit'].update({'readonly' : False, 'states' : {}})
#             doc1 = etree.XML(res['fields']['order_line']['views']['form']['arch'])
         
        cr.execute("""select uid from res_groups_users_rel where gid in
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Customer Portal' ) and name in ('User','Manager')) and uid = """+str(uid))
        portal_user = cr.fetchone() 
         
        if portal_user:
            if view_type == 'form':
                for node in doc.xpath("//field[@name='pricelist_id']"):
                    node.set('options', '{"no_open":True}')
                    node.set('readonly','1')
                    setup_modifiers(node,res['fields']['pricelist_id'])
                    res['arch'] = etree.tostring(doc)
                     
                for node in doc.xpath("//field[@name='partner_id']"):
                    node.set('options', "{'no_open' : true}")
                    node.set('options', "{'no_create' : true}")
                    setup_modifiers(node, res['fields']['partner_id'])
                    res['arch'] = etree.tostring(doc)
                    
                for node in doc.xpath("//field[@name='contact_id']"):
                    node.set('options', "{'no_open' : true}")
                    setup_modifiers(node, res['fields']['contact_id'])
                    res['arch'] = etree.tostring(doc)
                                        
                     
                for node in doc.xpath("//field[@name='partner_invoice_id']"):
                    node.set('options', "{'no_open' : true}")
                    setup_modifiers(node, res['fields']['partner_invoice_id'])
                    res['arch'] = etree.tostring(doc)
                     
                for node in doc.xpath("//field[@name='partner_shipping_id']"):
                    node.set('options', "{'no_open' : true}")
                    setup_modifiers(node, res['fields']['partner_shipping_id'])
                    res['arch'] = etree.tostring(doc)
                 
                for node in doc.xpath("//field[@name='warehouse_id']"):
                    node.set('options', "{'no_open' : true}")
                    setup_modifiers(node, res['fields']['warehouse_id'])
                    res['arch'] = etree.tostring(doc)
                    
        return res
    
   
    def _get_default_warehouse(self, cr, uid, context=None):
        if not context:
            context = {}
        company_id = self.pool.get('res.users')._get_company(cr, context.get('uid',uid), context=context)
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', company_id)], context=context)
        
        if not warehouse_ids:
            return False
        return warehouse_ids[0]
    
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(sale_order,self).default_get(cr, uid, fields, context)
        user = self.pool.get('res.users').browse(cr, uid, uid)
        cr.execute("""select uid from res_groups_users_rel where gid=
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Customer Portal' ) and name = 'Manager') and uid = """+str(uid))
        portal_user = cr.fetchone() 
        portal_group = portal_user and portal_user[0]
  
        if uid == portal_group:
             res['partner_id'] = user.partner_id.id
         
        res.update({'order_policy': 'picking'})
        return res
    
    def _get_portal(self, cr, uid, ids, fields, args, context=None):
        res = {}
        
        cr.execute("""select uid from res_groups_users_rel where gid=
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Customer Portal' ) and name = 'Manager') and uid = """+str(uid))
        portal_user = cr.fetchone() 
        portal_group = portal_user and portal_user[0]
        
        for case in self.browse(cr, uid, ids):
            res[case.id] = {'lock_it': False}
            lock_flag = False            
            
            if case.state not in ('sent', 'draft'):
                lock_flag = True
                        
            if uid == portal_group:
                if case.state in ('sent', 'draft') and case.sent_portal:
                    lock_flag = True
                        
            res[case.id]= lock_flag
        return res
    
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    
    # Overriden Discount is not considering in tax(Removing Discount in this function)
    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty, line.product_id, line.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val
    
    
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = round(res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'])
            
        return res
    
        
    # Funtion To Convert Amount to Text
    def _amt_in_words(self, cr, uid, ids, field_name, args, context=None):
        res={}
        
        for case in self.browse(cr, uid, ids):
            txt=''
            if case.amount_total:
                txt += amount_to_text_softapps._100000000_to_text(int(round(case.amount_total)))        
                res[case.id] = txt     
        return res
    

    _columns ={
               
                'order_policy': fields.selection([
                ('manual', 'On Demand'),
                ('picking', 'On Delivery Order'),
                ('prepaid', 'Before Delivery'),
            ], 'Create Invoice', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""On demand: A draft invoice can be created from the sales order when needed. \nOn delivery order: A draft invoice can be created from the delivery order when the products have been delivered. \nBefore delivery: A draft invoice is created from the sales order and must be paid before the products can be delivered."""),
               
               'contact_id'          : fields.many2one('res.partner','Contact Person'),
               
               #inherited
               'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                store={
                    'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                    'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','order_id'], 20),
                },
                multi='sums', help="The amount without tax.", track_visibility='always'),
            'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
                store={
                    'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                    'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','order_id'], 20),
                },
                multi='sums', help="The tax amount."),
            'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                store={
                    'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                    'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','order_id'], 20),
                },
                multi='sums', help="The total amount."),
               
            'amt_in_words'        : fields.function(_amt_in_words, method=True, string="Amount in Words", type="text",
                store={
                    'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                    'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty','order_id'], 20),
                },
                     help="Amount in Words.", track_visibility='always'),
               
           'date_from'    : fields.function(lambda *a,**k:{}, method=True, type='date',string="From"),
           'date_to'      : fields.function(lambda *a,**k:{}, method=True, type='date',string="To"),
           'terms'                : fields.text("Terms And Condition"),     
           'lock_it'      : fields.function(_get_portal, type='boolean', string='Lock it'),
           'sent_portal'  : fields.boolean('Qtn Sent by Portal'),  
           'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
             
             # Overriden for old Records
#             'name': fields.char('Order Reference', required=True, copy=False,
#                                 readonly=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, select=True),
#                                  
#              'do_name' : fields.char("Delivery Order No", size=25),
             
            }
    
    
    _defaults = {
             'order_policy': 'picking',
             'sent_portal': False,
             'warehouse_id':_get_default_warehouse
             }
    
    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        stock_obj = self.pool.get("stock.picking.out")
        invoice_vals =  super(sale_order,self)._prepare_invoice(cr, uid, order, lines, context)
        pick_ids = stock_obj.search(cr, uid,[('sale_id','=',order.id)])
        
        for pick in stock_obj.browse(cr, uid, pick_ids):
            invoice_vals.update({
                'transport'      : pick.cust_po_ref or '',
                'vehicle'        : pick.vehicle or '',
                'dc_ref'         : pick.name or '',
            })
            
        return invoice_vals
    # On select of customer pop up contact person
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not context:
            context = {}
        
        partner_obj = self.pool.get("res.partner")
        partner_vals = super(sale_order,self).onchange_partner_id(cr, uid, ids, part, context=context)
        
        if part:
            partner = partner_obj.browse(cr, uid, part)
            cont = partner_obj.search(cr, uid, [('parent_id','=',part)], limit=1)
            partner_vals['value'].update({
                                          'contact_id' : cont and cont[0] or False, 
                                          'pricelist_id': partner.property_product_pricelist.id
            })
            
        return partner_vals
     
    
    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = super(sale_order,self)._prepare_order_picking(cr, uid, order, context)
        res.update({
                    'contact_id' : order.contact_id and order.contact_id.id or False
                    }) 
        return res

    def quotation(self, cr, uid, ids, context=None):
        case = self.browse(cr, uid, ids[0])
        datas = {
                 'model': 'sale.order',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {
                'type': 'ir.actions.report.xml', 
                'report_name': 'Sales Quotation',
                'name'   : case.name and 'Sales Quotation - ' + case.name  or 'Sales Quotation',
                'datas': datas,
                 'nodestroy': True
                 }
    
    def action_quotation_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        cr.execute("""select uid from res_groups_users_rel where gid=
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Customer Portal' ) and name = 'Manager') and uid = """+str(uid))
        portal_user = cr.fetchone() 
        portal_group = portal_user and portal_user[0]
        
        if uid == portal_group:
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'magicemart', 'email_template_send_quotation')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = dict(context)
            ctx.update({
                'default_model': 'sale.order',
                'default_res_id': ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True
            })
        else:
            try:
                template_id = ir_model_data.get_object_reference(cr, uid, 'sale', 'email_template_edi_sale')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False 
            ctx = dict(context)
            ctx.update({
                'default_model': 'sale.order',
                'default_res_id': ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True
            })
            
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }        
        
    def create(self, cr, uid, vals, context = None):
        print "sale",uid, context.get("uid") 
        print "Sale COntext",context
        if not context:
            context = {}
        print "Create Wbsite Sale Order......",vals
        partner_obj = self.pool.get("res.partner")
        warehouse_obj = self.pool.get('stock.warehouse')
        uid = context.get("uid",uid)
        team_id = vals.get('team_id',False)
        if team_id !=3: 
            if vals.get('warehouse_id',False):
                warehouse = warehouse_obj.browse(cr, uid, vals.get('warehouse_id'))
                 
                #to select sub company shop
                if not warehouse.company_id.parent_id:
                    raise osv.except_osv(_('User Error'), _('You must select sub company sale warehouse !'))
                partner_id = vals.get('partner_id',False)
                partner = partner_obj.browse(cr, uid, partner_id)
                vals.update({
    #                          'pricelist_id':partner.property_product_pricelist.id,
                             'company_id':warehouse.company_id.id,
                            })
         
        return super(sale_order, self).create(cr, uid, vals, context = context)
      
    def write(self, cr, uid, ids, vals, context = None):
        if not context:
            context = {}
        print "Create Wbsite Sale Order Line......",vals
        partner_obj = self.pool.get("res.partner")
        warehouse_obj = self.pool.get('stock.warehouse')
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return []
        
        case = self.browse(cr, uid, ids[0])
        if uid != 1: 
            if vals.get('warehouse_id',case.warehouse_id.id):
                warehouse = warehouse_obj.browse(cr, uid, vals.get('warehouse_id',case.warehouse_id.id))
                if not warehouse.company_id.parent_id:
                    raise osv.except_osv(_('User Error'), _('You must select sub company sale Warehouse !'))
                 
            if vals.get('partner_id', case.partner_id):
                partner_id = vals.get('partner_id', case.partner_id.id)
                partner = partner_obj.browse(cr, uid, partner_id)
                vals.update({
    #                          'pricelist_id':partner.property_product_pricelist.id,
                             'company_id':warehouse.company_id.id,
                             })
 
        return super(sale_order, self).write(cr, uid, ids, vals, context = context)
     
    #inherited
    def action_button_confirm(self, cr, uid, ids, context=None):
        case = self.browse(cr, uid, ids[0])
        
        for ln in case.order_line:
            for t in ln.tax_id:
                if t.company_id.id != case.company_id.id :
                    raise osv.except_osv(_('Configuration Error!'),_('Please define the taxes which is related to the company \n "%s" !')%(case.company_id.name))
                
        return super(sale_order,self).action_button_confirm(cr, uid, ids, context)
     
# Inheriting action_ship_create Method to update Sale ID in Delivery Order
    def action_ship_create(self, cr, uid, ids, context=None):
        if not context:
            context={}
        pick_ids=[]
        
#         context.get('active_ids').sort()
        res=super(sale_order, self).action_ship_create(cr, uid, ids,context)
        pick=self.pool.get('stock.picking')
        
        for case in self.browse(cr,uid,ids):
            pick_ids=pick.search(cr,uid,[('group_id','=',case.procurement_group_id.id)])
            pick.write(cr,uid,pick_ids,{
                                        'sale_id'    :  case.id,
                                        'company_id' :  case.company_id.id,
                                        })
            
        return res
     
     

sale_order()



class sale_order_line(osv.osv):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'
    _description = 'Sales Order Line'
    
    
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    
    def _get_price_reduce(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0.0)
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.price_subtotal / line.product_uom_qty
        return res

    
    
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
            
        if context.get("uid"):
            if uid != context.get("uid",False):
                uid = context.get("uid")
                
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {'price_total':0.0,'price_subtotal':0.0}
            price = line.price_unit  #* (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
#             print "Taxes......", taxes
            cur = line.order_id.pricelist_id.currency_id
            res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur, taxes['total'])
            
            # for price total
            amount = taxes['total']
            for t in taxes.get('taxes',False):
                amount += t['amount']
            res[line.id]['price_total'] = cur_obj.round(cr, uid, cur, amount)
            
        return res

    # Overriden, to remove the discount calculation(coz, discount is already considered in unit price.)
    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 0
            
            if line.product_id:
                if line.purchase_price:
                    res[line.id] = round((line.price_unit*line.product_uos_qty ) -(line.purchase_price*line.product_uos_qty), 2)
                else:
                    res[line.id] = round((line.price_unit*line.product_uos_qty ) -(line.product_id.standard_price*line.product_uos_qty), 2)
        return res


    
    _columns = {
                'price_total'   : fields.function(_amount_line, string='Subtotal1', digits_compute= dp.get_precision('Account'), store=True, multi="all"),
                'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'), multi="all",store=True),
                'reference'     : fields.char("Reference(BOP)", size=20),  
#                 'mrp'           : fields.related('product_id','list_price', type="float", string="MRP", store=True),
#                 'available_qty' : fields.related('product_id','qty_available', type="float", string="Available Quantity", store=True ),
                'product_image' : fields.binary('Product Image'),
                'sale_mrp'      : fields.float('MRP', digits=(16,2)),
                'available_qty' : fields.integer("Available Quantity"),
                
                # Overriden,to remove the discount calculation(coz, discount is already considered in unit price.)
                'margin': fields.function(_product_margin, string='Margin',
                                          store = True),
                
                'price_reduce': fields.function(_get_price_reduce, type='float', string='Price Reduce', digits_compute=dp.get_precision('Product Price')),
                
                }
    _order = 'id asc'
        
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line,self)._prepare_order_line_invoice_line(cr, uid, line, account_id, context=context)
        if res:
            res.update({'reference': line.reference})
        return res
    
    # Overriden
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        part_obj = self.pool.get("res.partner")
        
        if context.get("uid"):
            if context and uid != context.get("uid",False):
                uid = context.get("uid")
        user_obj = self.pool.get("res.users")
        user = user_obj.browse(cr, uid, [context.get("uid",uid)])
        partner = part_obj.browse(cr, uid, [user.partner_id.id])
        
        partner_id = partner.id
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
#         lang = context.get("lang",False)
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}
    
    #inherited
    """  TO BE UNCOMENT  """
    
    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, context=None):
        
        if not context:
            context= {}
        context = dict(context)
        res = super(sale_order_line,self).product_id_change_with_wh(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id,context)
        #if the product changes and product not in price_list then it will take the sale price
        location_ids =[]
        unit_amt = 0.00
        move_obj = self.pool.get("stock.move")
        loc_obj = self.pool.get("stock.location")
        case = self.browse(cr, uid, ids)
        prod_obj =self.pool.get("product.product")
        prod =  prod_obj.browse(cr, uid,product)
        pricelist_obj = self.pool.get("product.pricelist")
        pricelist_id  = pricelist_obj.browse(cr, uid, pricelist)
        
        if warehouse_id:  # shop is nothing but company_id
            context.update({'warehouse':warehouse_id})
#             warehouse_id = context.get('warehouse_id')
#             warehouse = self.pool.get("stock.warehouse").browse(cr, uid, warehouse_id)
#             comp_id = warehouse.company_id.id
#             location_ids = loc_obj.search(cr, uid,[('company_id','=',comp_id ),('name','=','Stock')])
#             if location_ids:
#                 location_ids = location_ids[0]

        if product:
            available_qty = prod_obj._product_available(cr, uid, [product], None, False, context)
            available_qty = available_qty[product].get('qty_available',0)
            # Commented for Pricelist Concept
            if pricelist_id.name == 'Public Pricelist' or not res['value'].get('price_unit'):
                unit_amt = prod.discount and prod.list_price - ((prod.discount/100) *  prod.list_price) or prod.list_price
                res['value']['discount'] = prod.discount
         
        if not res['value'].get('price_unit') and product:
            res['value']['price_unit'] = unit_amt and unit_amt or prod.list_price
            warn_msg = _('No Product in The Current Pricelist, It Will Pick The Sales Price')
            warning_msgs = _("No Pricelist ! : ") + warn_msg +"\n\n"\
     
            res['warning'] = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        if product:
            res['value']['sale_mrp'] = prod.list_price
            res['value']['product_image'] = prod.image_medium
            res['value']['available_qty'] = available_qty
            res['value']['purchase_price'] = prod.standard_price or 0.00
             
        # Commented for Pricelist Concept 
        if unit_amt :
            res['value']['price_unit'] = unit_amt
            
        return res
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
            
        if context.get("uid"):    
            if uid != context.get("uid",False):
                uid = context.get("uid")
        
        context = dict(context)
        loc_obj = self.pool.get("stock.location")
        move_obj = self.pool.get("stock.move")
        sale_obj = self.pool.get("sale.order")
        prod_obj = self.pool.get("product.product")
        tax_obj = self.pool.get("account.tax")
        order_id = vals.get('order_id')
        case = sale_obj.browse(cr, uid,order_id )
        company_id = case.warehouse_id.company_id.id
        
        res = self.product_id_change_with_wh(cr, uid, [], case.pricelist_id.id,vals.get('product_id',False),vals.get('qty',0), vals.get('uom',False), vals.get('qty_uos',0),
                                      vals.get('uos',False), vals.get('name',''), case.partner_id.id, vals.get('lang',False), vals.get('update_tax',True), vals.get('date_order',False), 
                                      vals.get('packaging',False), vals.get('fiscal_position',False), vals.get('flag',False),warehouse_id=case.warehouse_id.id,context=context)['value']
                                      
        if case.warehouse_id:  # shop is nothing but company_id
            context.update({'warehouse':case.warehouse_id.id})
        # Commented for Pricelist Concept   
        if res.get('discount'):
            vals.update({
                    'discount' : res.get('discount') and res.get('discount') or 0.00, 
                     })
             
        if res.get('price_unit'):
            vals.update({
                    'price_unit' : res.get('price_unit') and res.get('price_unit') or 0.00, 
                     })
        if res.get("price_unit"):
            vals.update({'price_unit':res.get("price_unit")})
            if not vals.get('price_unit')or not res.get('price_unit'):
                raise osv.except_osv(_('Warning'), _('Please Enter The Unit Price For \'%s\'.') % (vals['name'],))
            
        location_ids = loc_obj.search(cr, uid,[('company_id','=', company_id),('name','=','Stock')])
        
        comp_id = vals.get("company_id",case.company_id)
        if res.get("tax_id"):
            tax = tax_obj.browse(cr, uid, res.get("tax_id"))
            for t in tax:
                if t.company_id.id == comp_id.id:
                    vals.update({
                                 'tax_id' : [(6, 0, [t.id])],
                                 
                                 })
        if location_ids:
            location_ids = location_ids[0]
        product = vals.get('product_id', False)
        available_qty = prod_obj._product_available(cr, uid, [product], None, False, context)
        
        available_qty = available_qty[product].get('qty_available',0)
        prod = prod_obj.browse(cr, uid, vals.get("product_id",False))
        vals.update({'available_qty' : available_qty and available_qty or 0,
                     'product_image':prod.image_medium})

        return super(sale_order_line, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        
        if context and uid != context.get("uid",False):
            uid = context.get("uid")
        if not uid:
            uid = SUPERUSER_ID
        context = dict(context)
        prodtemp_obj = self.pool.get("product.template")
        loc_obj = self.pool.get("stock.location")
        move_obj = self.pool.get("stock.move")
        prod_obj = self.pool.get("product.product")
        tax_obj = self.pool.get("account.tax")
        user_obj = self.pool.get("res.users")
        
        for case in self.browse(cr, uid, ids):
            price_unit = vals.get('price_unit')
            prod_id = vals.get("product_id", case.product_id.id)
            prod = prod_obj.browse(cr, uid, [prod_id])
#             prodtemp_id = prod_obj.browse(cr, uid,[prod.product_tmpl_id.id] )
            
            pricelist_id = case.order_id.pricelist_id.id
             
            context.update({'quantity':case.product_uom_qty or 1.0 })
            context.update({'pricelist': pricelist_id or False})
            context.update({'partner': case.order_id.partner_id.id or False})
             
            # Calling This method update price_unit as Pricelist Price or Price After Discount or Sales Price 
            prodtemp = prodtemp_obj._product_template_price(cr, uid, [prod.product_tmpl_id.id], 'price', False, context=context)
            price_unit = prodtemp[prod.product_tmpl_id.id]
            if price_unit <=0.00:
                raise osv.except_osv(_('Warning'), _('Please Enter The Unit Price For \'%s\'.') % (case.name))
            if not price_unit:
                price_unit = case.price_unit
                if price_unit <= 0.00:
                    raise osv.except_osv(_('Warning'), _('Please Enter The Unit Price For \'%s\'.') % (case.name))
             
            if price_unit:
                vals.update({
                             'price_unit':price_unit
                             })    
                
#             location_ids = loc_obj.search(cr, uid,[('company_id','=', case.company_id.id or False),('name','=','Stock')])
#             
#             if location_ids:
#                 location_ids = location_ids[0]
#           
#             user_ids = user_obj.search(cr, uid, [('login','=', 'public')])
            cr.execute("select id from res_users where login = '" +str('public')+"'")
            user_id = cr.fetchone()
            if user_id != uid:
                
                if vals.get('warehouse_id',case.order_id.warehouse_id.id):  # shop is nothing but company_id
                    context.update({'warehouse':vals.get('warehouse_id',case.order_id.warehouse_id.id)})
                product = vals.get('product_id', case.product_id.id)
                available_qty = prod_obj._product_available(cr, uid, [product], None, False, context)
                available_qty = available_qty[product].get('qty_available',0)
                prod = prod_obj.browse(cr, uid,[product])
                
                vals.update({
                             'available_qty' : available_qty,
                             'product_image':prod.image_medium
                             })
                   
                res = self.product_id_change_with_wh(cr, uid, [], case.order_id.pricelist_id.id,vals.get('product_id',case.product_id.id),vals.get('qty',0), vals.get('uom',False), vals.get('qty_uos',0),
                                              vals.get('uos',False), vals.get('name',''), case.order_id.partner_id.id, vals.get('lang',False), vals.get('update_tax',True), vals.get('date_order',False), 
                                              vals.get('packaging',False), vals.get('fiscal_position',False), vals.get('flag',False),warehouse_id=case.order_id.warehouse_id.id,context=context)['value']
                vals.update({
                             'available_qty' : available_qty,
                             # Commented for Pricelist Concept
                            'discount' : res.get('discount') and res.get('discount')  or 0,
                            'price_unit': res.get("price_unit") and res.get("price_unit") or 1
                              
                             })
                if res.get("tax_id"):
                    comp_id = vals.get("company_id",case.company_id)
                    tax = tax_obj.browse(cr, uid, res.get("tax_id"))
                    for t in tax:
                        if t.company_id.id == comp_id.id:
                            vals.update({
                                         'tax_id' : [(6, 0, [t.id])],
                                         
                                         })
            return super(sale_order_line, self).write(cr, uid, [case.id], vals, context=context)
     
    
sale_order_line()
    
