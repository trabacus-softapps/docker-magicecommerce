from osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import amount_to_text_softapps
from lxml import etree
from openerp.osv.orm import setup_modifiers


class sale_order(osv.osv):
#     _name = 'sale.order'
    _inherit = 'sale.order'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        
        user = self.pool.get('res.users').browse(cr,uid,uid)
        
        if context is None:
            context = {}
        res = super(sale_order, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        doc = etree.XML(res['arch'])
        
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
        return res
    
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
            }
    
    
    _defaults = {
             'order_policy': 'picking',
             'sent_portal': False,
             }
    
    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        stock_obj = self.pool.get("stock.picking.out")
        invoice_vals =  super(sale_order,self)._prepare_invoice(cr, uid, order, lines, context)
        pick_ids = stock_obj.search(cr, uid,[('sale_id','=',order.id)])
        for pick in stock_obj.browse(cr, uid, pick_ids):
            invoice_vals.update({
                'transport'      : pick.carrier_tracking_ref or '',
                'vehicle'        : pick.vehicle or '',
                'dc_ref'         : pick.name or '',
            })
        return invoice_vals
    # On select of customer pop up contact person
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        partner_obj = self.pool.get("res.partner")
        partner_vals = super(sale_order,self).onchange_partner_id(cr, uid, ids, part, context=None)
        cont = partner_obj.search(cr, uid, [('parent_id','=',part)], limit=1)
        partner_vals['value'].update({
           'contact_id' : cont and cont[0] or False, 
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
        if not context:
            context = {}
        partner_obj = self.pool.get("res.partner")
        shop_obj = self.pool.get('sale.shop')
        if vals.get('shop_id',False):
            shop = shop_obj.browse(cr, uid, vals.get('shop_id'))
            #to select sub company shop
            if not shop.company_id.parent_id:
                raise osv.except_osv(_('User Error'), _('You must select sub company sale shop !'))
#         pricelist_id = False
#         res = self.onchange_partner_id(cr, uid, [], vals.get("partner_id", False), context=context)
#         pricelist_id = res['value']['pricelist_id'] 
#         if pricelist_id:
#         if not vals.get('pricelist_id'):
        partner_id = vals.get('partner_id',False)
        partner = partner_obj.browse(cr, uid, partner_id)
        vals.update({'pricelist_id':partner.property_product_pricelist.id})
        return super(sale_order, self).create(cr, uid, vals, context = context)
    
    def write(self, cr, uid, ids, vals, context = None):
        if not context:
            context = {}
        partner_obj = self.pool.get("res.partner")
        shop_obj = self.pool.get('sale.shop')
        case = self.browse(cr, uid, ids[0])
        if vals.get('shop_id',case.shop_id.id):
            shop = shop_obj.browse(cr, uid, vals.get('shop_id',case.shop_id.id))
            if not shop.company_id.parent_id:
                raise osv.except_osv(_('User Error'), _('You must select sub company sale shop !'))
        if vals.get('partner_id'):
            partner_id = vals.get('partner_id', case.partner_id.id)
            partner = partner_obj.browse(cr, uid, partner_id)
            vals.update({'pricelist_id':partner.property_product_pricelist.id})
        return super(sale_order, self).write(cr, uid, ids, vals, context = context)
    
    #inherited
    def action_button_confirm(self, cr, uid, ids, context=None):
        case = self.browse(cr, uid, ids[0])
        for ln in case.order_line:
            for t in ln.tax_id:
                if t.company_id.id != case.company_id.id :
                    raise osv.except_osv(_('Configuration Error!'),_('Please define the taxes which is related to the company \n "%s" !')%(case.company_id.name))
        return super(sale_order,self).action_button_confirm(cr, uid, ids, context)
     

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
    
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {'price_total':0.0,'price_subtotal':0.0}
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur, taxes['total'])
            
            # for price total
            amount = taxes['total']
            for t in taxes.get('taxes',False):
                amount += t['amount']
            res[line.id]['price_total'] = cur_obj.round(cr, uid, cur, amount)
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
                }
    _order = 'id asc'
        
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line,self)._prepare_order_line_invoice_line(cr, uid, line, account_id, context=context)
        if res:
            res.update({'reference': line.reference})
        return res
    
    #inherited
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,context=None):
        res = super(sale_order_line,self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, context)
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
        if 'shop' in context:  # shop is nothing but company_id
            shop_id = context.get('shop')
            shop = self.pool.get("sale.shop").browse(cr, uid, shop_id)
            comp_id = shop.company_id.id
            location_ids = loc_obj.search(cr, uid,[('company_id','=',comp_id ),('name','=','Stock')])
            if location_ids:
                location_ids = location_ids[0]
        if product:
            available_qty = move_obj.get_qty(cr, uid, product, location_ids)
        
        # if pricelist is Publick then unit price should be discounted from Sales Price base on the Discount%
#         if pricelist_id.name =="Public Pricelist"  and product:
#             prod =  prod_obj.browse(cr, uid,product)
#             if prod.discount >0.00:
#                 disc = prod.discount
#                 disc = (disc/100)
#                 disc_amt = (disc * prod.list_price)
#                 unit_amt = prod.list_price - disc_amt
#                 res['value']['price_unit'] = unit_amt
#                 res['value']['sale_mrp'] = prod.list_price
#                 res['value']['product_image'] = prod.image_medium
#                 res['value']['available_qty'] = available_qty
#                 res['value']['discount'] = prod.discount
#             else:
#                 res['value']['price_unit'] = prod.list_price
#                 res['value']['sale_mrp'] = prod.list_price
#                 res['value']['product_image'] = prod.image_medium
#                 res['value']['available_qty'] = available_qty
#                 res['value']['discount'] = prod.discount
#                 
#         else:
#         if pricelist_id and product:
#             res['value']['price_unit'] = res['value'][].get('price_unit')
#             res['value']['sale_mrp'] = prod.list_price
#             res['value']['product_image'] = prod.image_medium
#             res['value']['available_qty'] = available_qty
#             res['value']['discount'] = prod.discount

        if not res['value'].get('price_unit') and product:
            if prod.discount >0.00:
                disc = prod.discount
                disc = (disc/100)
                disc_amt = (disc * prod.list_price)
                unit_amt = prod.list_price - disc_amt
            
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
            res['value']['discount'] = prod.discount
        return res
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        loc_obj = self.pool.get("stock.location")
        move_obj = self.pool.get("stock.move")
        sale_obj = self.pool.get("sale.order")
        ids = vals.get('order_id')
        case = sale_obj.browse(cr, uid,ids )
        company_id = case.shop_id.company_id.id
        
        if vals.get('price_unit', False) <= 0:
            raise osv.except_osv(_('Warning'), _('Please Enter The Unit Price For \'%s\'.') % (vals['name'],))
        location_ids = loc_obj.search(cr, uid,[('company_id','=', company_id),('name','=','Stock')])
        if location_ids:
            location_ids = location_ids[0]
        available_qty = move_obj.get_qty(cr, uid, vals.get('product_id'), location_ids)
        vals.update({
                     'available_qty' : available_qty
                     })
        return super(sale_order_line, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        loc_obj = self.pool.get("stock.location")
        move_obj = self.pool.get("stock.move")
        case = self.browse(cr, uid, ids[0])
        if vals.get('price_unit',case.price_unit)<= 0.0:
            raise osv.except_osv(_('Warning'), _('Please Enter The Unit Price For \'%s\'.') % (case.name))
        location_ids = loc_obj.search(cr, uid,[('company_id','=', case.company_id.id),('name','=','Stock')])
        if location_ids:
            location_ids = location_ids[0]
        available_qty = move_obj.get_qty(cr, uid, case.product_id.id, location_ids)
        vals.update({
                     'available_qty' : available_qty
                     })
        return super(sale_order_line, self).write(cr, uid, ids, vals, context=context)
     
    
sale_order_line()
    
