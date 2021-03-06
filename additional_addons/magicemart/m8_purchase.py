# -*- coding: utf-8 -*-

from openerp.osv import fields,osv
from datetime import datetime
import time
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from lxml import etree
import amount_to_text_softapps
from openerp.osv.orm import setup_modifiers


class purchase_order(osv.osv):
    _inherit = "purchase.order"
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        
        user = self.pool.get('res.users').browse(cr,uid,uid)
        
        if context is None:
            context = {}
        res = super(purchase_order, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        doc = etree.XML(res['arch'])
        
        cr.execute("""select uid from res_groups_users_rel where gid in
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Supplier Portal' ) ) and uid = """+str(uid))
        sup_portal = cr.fetchone() 
        if sup_portal:
            if view_type == 'form':
                for node in doc.xpath("//field[@name='partner_id']"):
                    node.set('options', '{"no_open":True}')
                    node.set('readonly','1')
                    setup_modifiers(node,res['fields']['partner_id'])
                    res['arch'] = etree.tostring(doc)
                    
        return res
    
    
    # Overriden
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
          res = {}
          txt=''
          cur_obj=self.pool.get('res.currency')
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
                 for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id, order.partner_id)['taxes']:
                      val += c.get('amount', 0.0)
              res[order.id]['amount_tax']=cur_obj.round(cr, uid, cur, val)
              res[order.id]['amount_untaxed']=cur_obj.round(cr, uid, cur, val1)
              res[order.id]['amount_total']=round(res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'])
        
          return res
    # Overriden
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    
    # Funtion To Convert Amount to Text
    def _amt_in_words(self, cr, uid, ids, fields_name, args, context):
        res = {}
        for case in self.browse(cr, uid, ids):
            txt = ''
            if case.amount_total:
                txt += amount_to_text_softapps._100000000_to_text(int(round(case.amount_total)))        
                res[case.id] = txt     
        return res
     
        
    def _get_partner(self, cr, uid, ids, context=None):
        user_obj = self.pool.get("res.users")
        partner_id = False
        user = user_obj.browse(cr, uid, [uid] )
        if user:
            user = user[0]
        if user.user_roles == "magicemart_supplier_portal":
            partner_id = user.partner_id.id
        return partner_id    
      
    def _get_groups(self, cr, uid, ids, field_name, args, context):
        res = {}
        for case in self.browse(cr, uid, ids):
            cr.execute("""select uid from res_groups_users_rel where gid in
                          (select id  from res_groups where category_id in 
                          ( select id from ir_module_category where name = 'Supplier Portal' ) and name in ('Supplier Manager')) and uid = """+str(uid))
            supl_mgr = cr.fetchone() 
            if supl_mgr:
                res[case.id] =  True
            else:
                res[case.id] = False
        return res
        
    def _get_picking_in(self, cr, uid, context=None):
        res=super(purchase_order, self)._get_picking_in(cr, uid, context=context)
        company = []
        spt_ids = []
        picking_company=False
        picking_type_obj = self.pool.get('stock.picking.type')
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        for x in user_obj.company_ids:
            company.append(x.id)        
        if res:
            picking_type = picking_type_obj.browse(cr,uid,res)
            try:
                picking_company = picking_type.warehouse_id.company_id.id
                return res
            except:
                cr.execute("select spt.id from stock_picking_type spt inner join stock_warehouse sw on sw.id = spt.warehouse_id where sw.company_id in %s",(tuple(company),))
                spt_ids=[x[0] for x in cr.fetchall()]
                spt_id=picking_type_obj.search(cr,uid,[('id','in',spt_ids)])
                if spt_id:
                    print spt_id
                    return spt_id[0]
                else:
                    return []
     
     
    _columns={
              
            
              'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 20),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
              
          'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 20),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total',
            store={
                'purchase.order.line': (_get_order, None, 20),
            }, multi="sums",help="The total amount"),
              
        'amount_in_words'     :   fields.function(_amt_in_words, method=True, string="Amount in Words", type="text",
                store={
                'purchase.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 20),
                'purchase.order.line': (_get_order, ['order_id'], 20), # To Update the Lines Changes.
            } ),
              
        'invoice_method': fields.selection([('manual','Based on Purchase Order lines'),('order','Based on generated draft invoice'),('picking','Based on incoming shipments')], 'Invoicing Control', required=True,
                            readonly=True, 
                            help="Based on Purchase Order lines: place individual lines in 'Invoice Control > Based on P.O. lines' from where you can selectively create an invoice.\n" \
                                "Based on generated invoice: create a draft invoice you can validate later.\n" \
                                "Bases on incoming shipments: let you create an invoice when receptions are validated."
                        ),
         'date_from'    : fields.function(lambda *a,**k:{}, method=True, type='date',string="From"),
         'date_to'      : fields.function(lambda *a,**k:{}, method=True, type='date',string="To"),
         'terms'                : fields.text("Terms And Condition"),
         
        'hide_field'    :   fields.function(_get_groups, string="Get Group", type="boolean", store=False),
        
        # override for old Records
#         'in_name' : fields.char("Incoming Shipment No", size=25),
            
        }
    _defaults={
               'invoice_method'     :  'picking',
                'picking_type_id': _get_picking_in,
                'partner_id'         :   _get_partner
               }
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(purchase_order,self).default_get(cr, uid, fields, context)
        res.update({'invoice_method': 'picking'})
        return res
    
    
    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        stockware_obj = self.pool.get("stock.warehouse")
        picking_type_obj = self.pool.get("stock.picking.type")
        res={}
        warehouse_ids = stockware_obj.search(cr, uid, [('company_id','=', company_id)])
        if warehouse_ids:
            spt_id=picking_type_obj.search(cr,uid,[('warehouse_id','in',warehouse_ids)])
            if spt_id:
                res['picking_type_id'] =spt_id[0]  
        return {'value': res}
      
    # inherit updating Payment Term in Notes field  
    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        partner_obj = self.pool.get('res.partner')
        res={}
        res = super(purchase_order,self).onchange_partner_id(cr, uid, ids, partner_id, context)
        if res:
            part = partner_obj.browse(cr, uid, [partner_id])
            if part:
                res['value'].update({
                                     'notes' : part.property_supplier_payment_term.name or ''
                                     })
        return res
        
    
    
    def print_quotation(self, cr, uid, ids, context=None):
        return True
    
    def create(self, cr, uid, vals, context = None):
        comp_obj = self.pool.get('res.company')
        if vals.get('company_id', False):
            print "sda",vals.get('company_id', False)
            for c in comp_obj.browse(cr, uid, [vals.get('company_id', False)]):
                if not c.parent_id:
                    raise osv.except_osv(_('User Error'), _('You must select sub company sale shop !'))
#         if vals.get('name', '/') == '/':
#             raise osv.except_osv(_('Warrning'), _('You must Enter the Purchase Order Number!'))
        return super(purchase_order,self).create(cr, uid, vals, context)
    
    def wkf_confirm_order(self, cr, uid, ids, context=None):
        case = self.browse(cr, uid, ids[0])
        for ln in case.order_line:
            for t in ln.taxes_id:
                if t.company_id.id != case.company_id.id :
                    raise osv.except_osv(_('Configuration Error!'),_('Please define the taxes which is related to the company \n "%s" !')%(case.company_id.name))
        return super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)
     
#     TO BE UNCOMMENT
      
#     def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, context=None):
#         if not context:
#             context = {}
#         context= dict(context)
#         stckloc_obj = self.pool.get("stock.location")
#         loc_id = stckloc_obj.search(cr, uid, [('complete_name','=','Partner Locations / Suppliers / Stock')]) 
#         if loc_id:
#             loc_id =loc_id[0]
#         res = super(purchase_order,self)._prepare_order_line_move(cr, uid, order, order_line, picking_id, context=context)
#          
#         res.update ({
#                       
#             'location_id': loc_id,
# #             'location_dest_id': order.location_id.id,
#              
#                   })
#         return res
#     
    # Send by Mail For Supplier Portal
#     def wkf_send_rfq(self, cr, uid, ids, context=None):
#         '''
#         This function opens a window to compose an email, with the edi purchase template message loaded by default
#         '''
#         ir_model_data = self.pool.get('ir.model.data')
#         cr.execute("""select uid from res_groups_users_rel where gid=
#               (select id  from res_groups where category_id in 
#               ( select id from ir_module_category where name = 'Supplier Portal' ) and name = 'Supplier Manager') and uid = """+str(uid))
#         portal_user = cr.fetchone() 
#         portal_group = portal_user and portal_user[0]
#         
#         if uid == portal_group:
#             try:
#                 template_id = ir_model_data.get_object_reference(cr, uid, 'magicemart', 'email_template_supplier_quotation')[1]
#             except ValueError:
#                 template_id = False
#             try:
#                 compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
#             except ValueError:
#                 compose_form_id = False 
#             ctx = dict(context)
#             ctx.update({
#                 'default_model': 'purchase.order',
#                 'default_res_id': ids[0],
#                 'default_use_template': bool(template_id),
#                 'default_template_id': template_id,
#                 'default_composition_mode': 'comment',
#             })
#         else:
#                
#             try:
#                 template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase')[1]
#             except ValueError:
#                 template_id = False
#             try:
#                 compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
#             except ValueError:
#                 compose_form_id = False 
#             ctx = dict(context)
#             ctx.update({
#                 'default_model': 'purchase.order',
#                 'default_res_id': ids[0],
#                 'default_use_template': bool(template_id),
#                 'default_template_id': template_id,
#                 'default_composition_mode': 'comment',
#             })
#         return {
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'mail.compose.message',
#             'views': [(compose_form_id, 'form')],
#             'view_id': compose_form_id,
#             'target': 'new',
#             'context': ctx,
#         }
#     
# Overriden Updating PO company ID to incommingshipment
    # Overriden for updating in_name from PO (for Old Records)
    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id': order.dest_address_id.id or order.partner_id.id,
                'date': max([l.date_planned for l in order.order_line]),
                'origin': order.name,
                'company_id' : order.company_id.id,
                    # Overriden for updating in_name from PO (for Old Records)
#                 'name' : order.in_name
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
    
    
purchase_order()

 
class purchase_order_line(osv.osv):
    _inherit='purchase.order.line'
      
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:context = {}
           
        res = super(purchase_order_line, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        cr.execute("""select uid from res_groups_users_rel where gid=
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Supplier Portal' )) and uid = """+str(uid))
        portal_user = cr.fetchone() 
        portal_group = portal_user and portal_user[0]
        doc = etree.XML(res['arch'])
        if uid == portal_group:
                for node in doc.xpath("//field[@name='product_id']"):
                        node.set('options', "{'no_create':True}")
                for node in doc.xpath("//field[@name='product_uom']"):
                        node.set('options', "{'no_create':True}")
                for node in doc.xpath("//field[@name='taxes_id']"):
                        node.set('options', "{'no_create':True}")
                res['arch'] = etree.tostring(doc)    
        return res
      
      
    # Overriden
    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        cur_obj=self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids):
            amount = 0.0
            res[line.id] = {'price_subtotal1':0.0,'price_subtotal':0.0}
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id, line.order_id.partner_id)
            if line.order_id:
                cur = line.order_id.pricelist_id.currency_id
                res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur,taxes['total'])
                 
                #for Price_subtotal1
                amount = taxes['total']
                for t in taxes.get('taxes',False):
                    amount += t['amount'] 
                res[line.id]['price_subtotal1'] = cur_obj.round(cr, uid, cur, amount)
        return res 

    _columns={
              # price_subtotal1 is after tax amount field.
              'price_subtotal1'      :   fields.function(_amount_line, string='Subtotal1', digits_compute= dp.get_precision('Account'), store=True, multi="all"),
              'price_subtotal'      :   fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account'), store=True, multi="all"),
            }
purchase_order_line()



