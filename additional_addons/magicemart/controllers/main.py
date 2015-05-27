# -*- coding: utf-8 -*-
import werkzeug

from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
import openerp
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug
import openerp.addons.website_sale.controllers.main as WSmain



PPG = 20 # Products Per Page
PPR = 4  # Products Per Row


class website_sale(openerp.addons.website_sale.controllers.main.website_sale):
 
    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        cr, uid, context  = request.cr, request.uid, request.context
          
        res = super(website_sale,self).product(product, category, search, **kwargs)
 
         
        if res:
            if not product.product_variant_ids:
                cr.execute("select id from product_product where product_tmpl_id = "+str(product.id)+" order by id limit 1")
                variant_ids = cr.fetchone()
                 
                print "variant_ids.......",variant_ids,variant_ids[0]
                if variant_ids:
                    variant_ids =variant_ids[0]
                    res.qcontext.update({'variants' : variant_ids}) 
                    print "RES,,,,,,",res.qcontext
        return res
     
 
    @http.route(['/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
         
        ir_rule_obj = request.registry("ir.rule")
        user_obj = request.registry("res.users")
        prod_ids = ir_rule_obj.product_filter(cr, uid, [], context=context)
          
        newdom = []
#         dom = ir_rule_obj._compute_domain(cr, uid, self.name, 'read') or []
 
        domain = request.website.sale_product_domain()
        dom = [] 
        u_id = context.get("uid",uid)
        user = user_obj.browse(cr, uid, [u_id])
        if user.user_roles in ('magicemart_portal_user','magicemart_portal_manager','magicemart_supplier_portal'): 
            if prod_ids:
                newdom = [('id', 'in', [x[0] for x in prod_ids])]
                 
            else:   
                newdom = [('id', '=',1)]
                 
            if len(dom):
                domain = list((['&'] + dom + newdom))
                 
            else:
                domain = list(newdom)
                
  
         
        if search:
            for srch in search.split(" "):
                domain += ['|', '|', '|', ('name', 'ilike', srch), ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch)]
        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]
  
        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
  
        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]
  
        keep = WSmain.QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)
  
        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)
  
        product_obj = pool.get('product.template')
  
        url = "/shop"
        product_count = product_obj.search_count(cr, uid, domain, context=context)
        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)
            url = "/shop/category/%s" % slug(category)
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
  
        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)
  
        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)
  
        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids, context=context)
  
        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
  
        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'bins': WSmain.table_compute().process(products),
            'rows': PPR,
            'styles': styles,
            'categories': categs,
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],
            'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib',i) for i in attribs]),
        }
        return request.website.render("website_sale.products", values)
    
    # Overriden Pass pricelist_id
    @http.route(['/shop/get_unit_price'], type='json', auth="public", methods=['POST'], website=True)
    def get_unit_price(self, product_ids, add_qty, **kw):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        products = pool['product.product'].browse(cr, uid, product_ids, context=context)
        partner = pool['res.users'].browse(cr, uid, uid, context=context).partner_id
        pricelist_id = request.session.get('sale_order_code_pricelist_id') or partner.property_product_pricelist.id
        prices = pool['product.pricelist'].price_rule_get_multi(cr, uid, pricelist_id, [(product, add_qty, partner) for product in products], context=context)
        return {product_id: prices[product_id][pricelist_id][0] for product_id in product_ids}
    
   
    # Overriden to pass Warehouse
    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']
        warehouse_obj = pool['stock.warehouse']
         
        warehouse_ids = warehouse_obj.search(cr, uid, [('code','!=', 'MAIN')])
        warehouse = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
               
          
        context.update(active_id=product.id)
         
        if category:
            category = category_obj.browse(cr, uid, int(category), context=context)
 
        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [map(int,v.split("-")) for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
 
        keep = WSmain.QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)
 
        category_ids = category_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
        categs = category_obj.browse(cr, uid, category_ids, context=context)
 
        pricelist = self.get_pricelist()
 
        from_currency = pool.get('product.price.type')._get_field_currency(cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(cr, uid, from_currency, to_currency, price, context=context)
 
        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, int(product), context=context)
 
        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': categs,
            'main_object': product,
            'warehouse': warehouse,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids
        }
        return request.website.render("website_sale.product", values)
   
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        print "KW",kw
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        sline_obj = pool['sale.order.line']
        warehouse_obj = pool['stock.warehouse']
        sale_obj = pool['sale.order']
        
        sale_order_id = request.session.get('sale_order_id')
        
        if not sale_order_id:
#             if kw.get('Warehouse') == 'Select City':
#                     raise Warning(" Please Select The City")
            
            warehouse_id = int(kw.get('Warehouse', False))
            context.update({"Warehouse":warehouse_id})
            warehouse = warehouse_obj.browse(cr, uid, warehouse_id) 
             
#             if not warehouse_id:
#                 raise osv.except_osv(_('Warning'),_('Please Select The City!'))
              
            # Creating Sale order
            sale = request.website.sale_get_order(force_create=1, context=context)
            request.session['sale_order_id'] = sale.id
             
            # Creating Sale order Line
            sale._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
            if sale.id:
                cr.execute("update sale_order set warehouse_id="+str(warehouse_id)+"where id="+str(sale.id))
                cr.execute("update sale_order set company_id="+str(warehouse.company_id.id)+"where id ="+str(sale.id))
                
        else:
            request.website.sale_get_order(force_create=0)._cart_update(product_id=int(product_id), add_qty=float(add_qty), set_qty=float(set_qty))
            
        return request.redirect("/shop/cart")
     
     
    
    