# -*- coding: utf-8 -*-
import werkzeug


from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
import openerp
from openerp import tools
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug
import openerp.addons.website_sale.controllers.main as WSmain


from openerp.addons.auth_signup.res_users import SignupError


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
    
    
    # Passing Warehouse On click of Process Checkout
    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        warehouse_obj = pool["stock.warehouse"]
        user_obj = pool["res.users"]
        
        print "Checout Post.....",post
        order = request.website.sale_get_order(force_create=1, context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()
        
        user = user_obj.browse(cr, uid, uid)
        if user.login == 'public':  
            warehouse_ids = warehouse_obj.search(cr, uid, [('code','!=', 'MAIN')])
            warehouse = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
            values.update({
                           'warehouse':warehouse,
                           })
        print "Checkout....",values
        return request.website.render("website_sale.checkout", values)
    
    
    
    # While Confirming the Order Updating Warehouse and Company with respect to sale order
    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        warehouse_obj = pool["stock.warehouse"]
        sale_obj = pool["sale.order"]
        print "ConfirmPost.....",post
        
        warehouse_id = post.get("Warehouse")
        if warehouse_id:
            warehouse = warehouse_obj.browse(cr, uid, int(warehouse_id))
#             warehouse = int(warehouse)
        order = request.website.sale_get_order(context=context)
        if not order:
            return request.redirect("/shop")

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection
        
                
        if warehouse_id and order:
            
            print "Wraehouse...............",int(warehouse_id)
            
            cr.execute("update sale_order set warehouse_id="+str(warehouse_id)+"where id="+str(order.id))
            cr.execute("update sale_order set company_id="+str(warehouse.company_id.id)+"where id ="+str(order.id))
            
#             sale_obj.web_comp_tax(cr, uid, order.id, int(warehouse_id), warehouse.company_id.id, {})
            sale_obj.write(cr, uid, [order.id], {'company_id':warehouse.company_id.id})
            
            
        values = self.checkout_values(post)

        values["error"], values["error_message"] = self.checkout_form_validate(values["checkout"])
        if values["error"]:
            return request.website.render("website_sale.checkout", values)

        self.checkout_form_save(values["checkout"])

        request.session['sale_last_order_id'] = order.id
        

        request.website.sale_get_order(update_pricelist=True, context=context)
        
        
        return request.redirect("/shop/payment")
   

#     # To Display Error If Required fields are not set 
#     def checkout_form_validate(self, data):
#         cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
# 
#         error = dict()
#         error_message = []
#         
#         print "Data.....",data
# 
#         # Validation
#         for field_name in self.mandatory_billing_fields:
#             print "FIELD NAME",data.get(field_name)
#             if not data.get(field_name):
#                 error[field_name] = 'missing'
#             
#             if "Warehouse" not in data:
#                 error[field_name] = 'missing'
#             
#         # email validation
#         if data.get('email') and not tools.single_email_re.match(data.get('email')):
#             error["email"] = 'error'
#             error_message.append(_('Invalid Email! Please enter a valid email address.'))
# 
#         # vat validation
#         if data.get("vat") and hasattr(registry["res.partner"], "check_vat"):
#             if request.website.company_id.vat_check_vies:
#                 # force full VIES online check
#                 check_func = registry["res.partner"].vies_vat_check
#             else:
#                 # quick and partial off-line checksum validation
#                 check_func = registry["res.partner"].simple_vat_check
#             vat_country, vat_number = registry["res.partner"]._split_vat(data.get("vat"))
#             if not check_func(cr, uid, vat_country, vat_number, context=None): # simple_vat_check
#                 error["vat"] = 'error'
# 
#         if data.get("shipping_id") == -1:
#             for field_name in self.mandatory_shipping_fields:
#                 field_name = 'shipping_' + field_name
#                 if not data.get(field_name):
#                     error[field_name] = 'missing'
# 
#         # error message for empty required fields
#         if [err for err in error.values() if err == 'missing']:
#             error_message.append(_('Some required fields are empty.'))
# 
#         return error, error_message

    
    
class AuthSignupHome(openerp.addons.auth_signup.controllers.main.AuthSignupHome):    
    
    
    
    # Overriden to Create Company Field in Sign Up Page
    @http.route('/web/signup', type='http', auth='public', website=True)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        comp_obj = pool["res.company"]
         
        comp_ids = comp_obj.search(cr, uid, [('parent_id','!=',False)])
        
        company = comp_obj.browse(cr, uid, comp_ids)
        
        qcontext.update({'company_id':company})
        
        print "kw",kw
        if 'company' in kw:
            company_id = int(kw.get('company'))
            if company_id:
#                 company_id = (company_id)
#                 eval(field['selection'])
                qcontext.update({'company_id':company_id, 'company_ids': [(6, 0, [company_id])],})
            
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                return super(AuthSignupHome, self).web_login(*args, **kw)
            except (SignupError, AssertionError), e:
                qcontext['error'] = _(e.message)

        return request.render('auth_signup.signup', qcontext)
    
    # Overriden to pass only 1 company in company and allowed companies in Users
    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        loc_obj = pool["stock.location"]
        prod_obj = pool["product.product"]
        values = dict((key, qcontext.get(key)) for key in ('login', 'name', 'password','company_id','company_ids'))
        
        loc_ids = loc_obj.search(cr, uid, [('complete_name','=','Partner Locations / Customers / Stock')])
        prod_ids = prod_obj.search(cr, uid, []) 
        if loc_ids:
            loc_ids = loc_ids[0]
            values.update({
                           
                           'user_roles':'magicemart_portal_manager',
                           'location_id' : loc_ids,
                           'product_ids': [(6, 0, prod_ids)],
                           })
        
        assert any([k for k in values.values()]), "The form was not properly filled in."
        assert values.get('password') == qcontext.get('confirm_password'), "Passwords do not match; please retype them."
        self._signup_with_values(qcontext.get('token'), values)
        request.cr.commit()
    
