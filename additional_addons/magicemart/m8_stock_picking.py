# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf-8")


from openerp import netsvc
from openerp.osv import fields, osv
import time
import datetime
from lxml import etree
from datetime import datetime
from openerp.tools.translate import _
from openerp.osv.orm import setup_modifiers
from openerp import SUPERUSER_ID



class stock_picking(osv.osv):
#     _name = 'stock.picking'
    _inherit = 'stock.picking'
    
    # Hiding Partner_id field in Internal Moves Menu
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        
        if context is None:
            context = {}
        pick_type_obj = self.pool.get("stock.picking.type")
        res = super(stock_picking, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        doc = etree.XML(res['arch'])
        if context.get('default_picking_type_id',False):
            pick_type = pick_type_obj.browse(cr, uid,[context.get('default_picking_type_id')])
            if pick_type:
                if pick_type.code == 'internal':
                    if view_type == 'form':
                        for node in doc.xpath("//field[@name='partner_id']"):
                            node.set('invisible', '1')
                            setup_modifiers(node, res['fields']['partner_id'])
                            res['arch'] = etree.tostring(doc)
        else:
            cr.execute("""select uid from res_groups_users_rel where gid=
              (select id  from res_groups where category_id in 
              ( select id from ir_module_category where name = 'Customer Portal' ) and name = 'Manager') and uid = """+str(uid))
            portal_user = cr.fetchone() 
            portal_group = portal_user and portal_user[0]
            if uid == portal_group:
                for node in doc.xpath("//notebook/page[@string='Products']/field[@name='move_lines']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['move_lines'])
                    res['arch'] = etree.tostring(doc)
                    
                for node in doc.xpath("//field[@name='partner_id']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['partner_id'])
                    res['arch'] = etree.tostring(doc)
                    
                for node in doc.xpath("//field[@name='date']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['date'])
                    res['arch'] = etree.tostring(doc)
                    
                for node in doc.xpath("//field[@name='min_date']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['min_date'])
                    res['arch'] = etree.tostring(doc)

                for node in doc.xpath("//field[@name='origin']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['origin'])
                    res['arch'] = etree.tostring(doc)
               
                for node in doc.xpath("//field[@name='cust_po_ref']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['cust_po_ref'])
                    res['arch'] = etree.tostring(doc)     

                for node in doc.xpath("//field[@name='vehicle']"):
                    node.set('readonly','1')
                    setup_modifiers(node, res['fields']['vehicle'])
                    res['arch'] = etree.tostring(doc)     
                
                for node in doc.xpath("//field[@name='partner_id']"):
                    node.set('options', "{'no_open' : true}")
                    setup_modifiers(node, res['fields']['partner_id'])
                    res['arch'] = etree.tostring(doc)
                
        return res
    
    
    _columns = {
                'contact_id'       : fields.many2one('res.partner', 'Contact Person'),
                'vehicle'          : fields.char('Vehicle', size=15),
                'invoice_id'       : fields.many2one('account.invoice', 'Invoice'),
                'available_qty'    : fields.char("Available Quantity", size=15),
                'date_from'        : fields.function(lambda *a, **k:{}, method=True, type='date', string="From"),
                'date_to'          : fields.function(lambda *a, **k:{}, method=True, type='date', string="To"),
                'terms'            : fields.text("Terms And Condition"),
                'return_st'        : fields.boolean('Returned Delivery Order'),
                'cust_po_ref'      : fields.char("Customer PO Reference"), 
                'sale_id'          : fields.many2one('sale.order','Sale Order'),
                
#                 # Overriden for old records to update old numbers 
#                 'name': fields.char('Reference', select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, copy=False),
                
                }
    _order = 'name desc'
    
    _defaults = {
               'return_st'  :False,
            }
     
     # Overriden for update numbers(for Old Records)
#     def create(self, cr, user, vals, context=None):
#         print"vals......",vals
#         context = context or {}
#         if vals.get('do_name'):
#             vals.update({'name' : vals.get('do_name')})
#         if vals.get('in_name'):
#             vals.update({'name' : vals.get('in_name')})
#         return super(stock_picking, self).create(cr, user, vals, context)
        


    # for Old Records
#     def write(self, cr, uid, ids, vals, context=None):
#         move_obj = self.pool.get("stock.move")
#         case = self.browse(cr, uid, ids)
#         move_ids = move_obj.search(cr, uid, [('picking_id','in', ids)])
#         move_obj.write(cr, uid, move_ids, {'date':vals.get('date',case.date),
#                                            'date_expected' : vals.get('min_date', case.min_date)
#                                            }, context=context)
#         return super(stock_picking, self).write(cr, uid, ids, vals, context=context)
#          
    
    # Check Availability
    def action_assign(self, cr, uid, ids, *args):
        context = {}
        move_obj = self.pool.get("stock.move")
        prod_obj = self.pool.get("product.product")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            for op in move_obj.browse(cr, uid, move_ids):
#                 quantity_available = move_obj.get_qty(cr, uid, op.product_id.id, op.location_id.id)
                context.update({'warehouse':op.warehouse_id.id})
                quantity_available = prod_obj._product_available(cr, uid, [op.product_id.id], None, False, context)
                
                quantity_available = quantity_available[op.product_id.id].get('qty_available',0)
                if op.product_qty > quantity_available and pick.picking_type_id.code in ('outgoing'):
                   raise osv.except_osv(_('Warning'), _(str(op.product_id.name_template) + ' Quantity is greater than the Available Stock!!!'))
        return super(stock_picking, self).action_assign(cr, uid, ids, *args)
     
    
    """ Overriden, While Grouping more than 1 DO if product are same means sum up the quantity and create Invoice Lines""" 
    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoiceln_obj = self.pool.get('account.invoice.line')
        move_obj = self.pool.get('stock.move')
        stinvship_obj = self.pool.get("stock.invoice.onshipping")
        
        invoices = {}
        prod = {}
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)

            key = (partner, currency_id, company.id, user_id)

            if key not in invoices:
                # Get account and payment terms
                invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id

            
            if move.id in prod:
                prod[move.id]['qty'] = move.product_uom_qty + prod[move.id]['qty']
                prod[move.id]['product_id'] = move.product_id.id
            else:
                prod.update({move.id : {'qty': move.product_uom_qty , 'product_id_id': move.product_id.id}})
        for p in prod.keys():
            
            move1 =  move_obj.browse(cr, uid, p)
            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move1, partner, inv_type, context=context)
            if invoice_line_vals:
                invoice_line_vals['invoice_id'] = invoices[key]
                invoice_line_vals['origin'] = origin
                invln_id = move_obj._create_invoice_line_from_vals(cr, uid, move1, invoice_line_vals, context=context)
        wiz_id = context.get('wiz_id',False)
#             if wiz_id:
#                 wiz_id = wiz_id[0]
        wiz = stinvship_obj.browse(cr, uid, wiz_id)
        if wiz.group:
#                 if move.origin_returned_move_id:
            for mv in moves:
                mv_ids = move_obj.search(cr, uid, [("origin_returned_move_id", '=' ,mv.id),('location_id', 'child_of', move.location_dest_id.id)],context=context)
                if mv_ids:
                    raise osv.except_osv(_('Warning!'), _("You are not supposed to group, because some products are returned back.!")) 
                
                cr.execute("update account_invoice_line set quantity ="+str(prod[p]['qty'])+" where id = "+ str(invln_id))
            
        for move in moves:
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)
        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()
     
  
    
    """ TO BE UNCOMMENT"""
    
    # Inherit Creating Invoice
    
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, origin, context=None):
        if context is None:
            context = {}
#     def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        stock_obj = self.pool.get("stock.picking.out")
        accinv_obj = self.pool.get("account.invoice")
        journal_obj = self.pool.get("account.journal")
        account_obj = self.pool.get("account.account")
        period_obj = self.pool.get("account.period")
        invoice_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, origin, context)
        do_name = ''
        ctx = {}
        for pick in self.browse(cr, uid, context.get('active_ids', [])):
            if invoice_vals.get('partner_id', False) == pick.partner_id.id:
                do_name += pick.name + ', '
            if len(context.get('active_ids', [])) == 1:
                invoice_vals.update({
                                     'vehicle'     : pick.vehicle and pick.vehicle or False,
                                     'transport'   : pick.cust_po_ref or False,
#                                      'contact_id'  : pick.contact_id and pick.contact_id.id or False,
                                     'company_id'  : pick.company_id.id,
                                     })
  
              
            invoice_vals.update({
                'dc_ref'         : do_name and do_name[0:-2] or None,
                  
                                })
#         onchange_company = accinv_obj.onchange_company_id(cr, uid, pick.id, pick.company_id.id, partner, inv_type, [0,0,False],False)
        return invoice_vals
         
           
    """ Stock Internal Transfer"""
    
    def stock_internal_transfer(self, cr, uid, ids, context=None):
        for case in self.browse(cr, uid, ids):
            report_name = 'Stock Internal Transfer'
            data = {}
            data['ids'] = ids
            data['model'] = 'stock.move'
            data['output_type'] = 'xls'
                  
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': data,
            'context' :context
    }
     

               
stock_picking()

class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"

    _columns = {
        'invoice_date': fields.date('Invoiced date'),
    }

    _defaults = {
                 'invoice_date' : time.strftime('%Y-%m-%d')
                 }
    # updating invoice_ to invoice_id field in delivery order
    def create_invoice(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        context.get('active_ids').sort()
        pick_obj = self.pool.get("stock.picking")
        accinv_obj = self.pool.get("account.invoice")
        invoice_ids = super(stock_invoice_onshipping, self).create_invoice(cr, uid, ids, context)
        for inv in invoice_ids:
            for pick_id in context.get('active_ids', []):
                pick = pick_obj.browse(cr, uid, pick_id)
                pick_obj.write(cr, uid, [pick_id], {'invoice_id':inv})
                
                inv_browse = accinv_obj.browse(cr, uid, [inv])
                  
                onchange_company = accinv_obj.onchange_company_id(cr, uid, inv, pick.company_id.id, pick.partner_id.id, inv_browse.type, [0, 0, False], False)
                accinv_obj.write(cr, uid, inv, onchange_company['value'])
                
        return invoice_ids
    
stock_invoice_onshipping()
    
     
class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'
      
     
    def onchange_invoicing(self, cr, uid, ids, invoice_state, context=None):
        inv_obj = self.pool.get("account.invoice")
        stock_obj = self.pool.get("stock.picking")
        if not context:
            context = {}
        res = {}
        warning = ""
        pick_id = context.get("active_id", False)
        if pick_id:
            pick = stock_obj.browse(cr, uid, pick_id)
             
            if pick.invoice_state == "2binvoiced": 
#                 if pick_id not in inv_obj.origin:
                warning = {
                                 'title':_('Warning'),
                                        'message':_(' You are not supposed Refund, beacuse Invoice is not Created for this Record. So Please Select the No Invoicing Option. ')
                                                   
                          }
                res.update({
                            'invoice_state' : 'none',
                            })
            else:
                warning = {
                     'title':_('Warning'),
                            'message':_(' You are not supposed Select No Invoicing Option, beacuse Invoice is already Created for this Record. So Please Select the Refund Option Option. ')
                                            
                          }
                res.update({
                            'invoice_state' : '2binvoiced',
                           })
                  
        return{'value':res , 'warning':warning}

    # Overriden 
    # Original product qty minus returned product qty updating in wizard(default_get)          
    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        result1 = []
        if context is None:
            context = {}
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        uom_obj = self.pool.get('product.uom')
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        quant_obj = self.pool.get("stock.quant")
        stmv_obj = self.pool.get("stock.move")
        chained_move_exist = False
        if pick:
            if pick.state != 'done':
                raise osv.except_osv(_('Warning!'), _("You may only return pickings that are Done!"))

            for move in pick.move_lines:
                if move.move_dest_id:
                    chained_move_exist = True
                
                qty = 0
                # Returned product qty
                move_search = stmv_obj.search(cr, uid, [("origin_returned_move_id", '=', move.id),('location_id', 'child_of', move.location_dest_id.id)],context=context)
                rtqty = 0
                for rtmv in stmv_obj.browse(cr, uid, move_search):
                    rtqty += rtmv.product_uom_qty
                
                # Original product qty minus returned product qty updating in wizard(default_get)
                qty = move.product_uom_qty - rtqty
                qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, qty, move.product_uom.id)
                if qty > 0: 
                    result1.append({'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id})

            if len(result1) == 0:
                raise osv.except_osv(_('Warning!'), _("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': result1})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': chained_move_exist})
        return res


    """
    Overriden Return Shipment
    """
    def _create_returns(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        data_obj = self.pool.get('stock.return.picking.line')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        data = self.read(cr, uid, ids[0], context=context)
        returned_lines = 0

        # Cancel assignment of existing chained assigned moves
        moves_to_unreserve = []
        for move in pick.move_lines:
            to_check_moves = [move.move_dest_id] if move.move_dest_id.id else []
            while to_check_moves:
                current_move = to_check_moves.pop()
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    moves_to_unreserve.append(current_move.id)
                split_move_ids = move_obj.search(cr, uid, [('split_from', '=', current_move.id)], context=context)
                if split_move_ids:
                    to_check_moves += move_obj.browse(cr, uid, split_move_ids, context=context)

        if moves_to_unreserve:
            move_obj.do_unreserve(cr, uid, moves_to_unreserve, context=context)
            #break the link between moves in order to be able to fix them later if needed
            move_obj.write(cr, uid, moves_to_unreserve, {'move_orig_ids': False}, context=context)

        #Create new picking for returned products
        pick_type_id = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id.id or pick.picking_type_id.id
        new_picking = pick_obj.copy(cr, uid, pick.id, {
            'move_lines': [],
            'picking_type_id': pick_type_id,
            'state': 'draft',
            'origin': pick.name,
        }, context=context)
        
        for data_get in data_obj.browse(cr, uid, data['product_return_moves'], context=context):
            move = data_get.move_id
            if not move:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
            if new_qty:
                returned_lines += 1
                move_obj.copy(cr, uid, move.id, {
                    'product_id': data_get.product_id.id,
                    'product_uom_qty': new_qty,
                    'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                    'picking_id': new_picking,
                    'state': 'draft',
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': move.location_id.id,
                    'origin_returned_move_id': move.id,
                    'procure_method': 'make_to_stock',
                    'restrict_lot_id': data_get.lot_id.id,
                })

        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))

        pick_obj.action_confirm(cr, uid, [new_picking], context=context)
        pick_obj.action_assign(cr, uid, [new_picking], context)
        # Writing return_st = True for returned shipments
        context.update({'return_st':True})
        pick_obj.write(cr, uid, [new_picking], {'return_st' : True }, context=context)
        
        return new_picking, pick_type_id


stock_return_picking()
    
class stock_move(osv.osv):
    _inherit = "stock.move"
    
    _columns = {
    
                'available_qty'     : fields.float("Available Quantity", digits=(16, 4)),
                'product_image'     : fields.binary('Product Image'),
                
                'c_price'           : fields.related('product_id', 'standard_price', type="float", string="Price", store=True),
#                 'sub_total'         : fields.function(_amount_subtotal, type='float', string='Sub Total', store=True),
                
            }

    _order = 'id asc'
    
    # Overriden to update do_name in stock_picking(for old Records)
#     def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
#         """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
#         (and company). Those attributes are also given as parameters.
#         """
#         sale_obj = self.pool.get('sale.order')
#         pick_obj = self.pool.get("stock.picking")
#         picks = pick_obj.search(cr, uid, [
#                 ('group_id', '=', procurement_group),
#                 ('location_id', '=', location_from),
#                 ('location_dest_id', '=', location_to),
#                 ('state', 'in', ['draft', 'confirmed', 'waiting'])], context=context)
#         if picks:
#             pick = picks[0]
# 
#         else:
#             move = self.browse(cr, uid, move_ids, context=context)[0]
#             if procurement_group:
#                 sale_ids = sale_obj.search(cr, uid, [('procurement_group_id','=',procurement_group)])
#                 sale = sale_obj.browse(cr, uid, sale_ids)
#             values = {
#                 'origin': move.origin,
#                 'company_id': move.company_id and move.company_id.id or False,
#                 'move_type': move.group_id and move.group_id.move_type or 'direct',
#                 'partner_id': move.partner_id.id or False,
#                 'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
#                 # updating do_number from sale before creating DO
#                 'name' : sale.do_name
#             }
#             pick = pick_obj.create(cr, uid, values, context=context)
#         return self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)             

    
    
    """
    Updating Available qty & Product Image.
    """
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False):
        prod_obj = self.pool.get('product.product')
        result = super(stock_move, self).onchange_product_id(cr, uid, ids, prod_id=prod_id, loc_id=loc_id, loc_dest_id=loc_dest_id, partner_id=partner_id)
        prod = prod_obj.browse(cr, uid, [prod_id])[0]
#         qty = self.get_qty(cr, uid, prod_id, loc_id)
        qty = prod_obj._product_available(cr, uid, [prod_id], None, False)
        qty = qty[prod_id].get('qty_available',0)
        uos_id = prod.uos_id and prod.uos_id.id or False
        if result:
            result['value'].update({
                          'available_qty'   :   qty,
                          'product_image'   :   prod.image_medium,
                          })

        return result

    """ 
    Updating Customer Stock if there, else Updating Just Customer Location.
    Updating Company Stock while Incoming Shipment based on Company 
    """
         
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        stock_obj = self.pool.get("stock.picking")
        pick_type_obj = self.pool.get("stock.picking.type")
        partner_obj = self.pool.get("res.partner")
        loc_obj = self.pool.get("stock.location")
        location_id = vals.get('location_id')
        location_dest_id = vals.get('location_dest_id')
         
#         origin = vals.get('origin',False)
#         if 'SO' not in str(origin) or 'PO' not in str(origin):
#             if location_id:
#                 loc_id = loc_obj.search(cr, uid, [('location_id', '=', location_id)])
#                 if loc_id:
#                     raise osv.except_osv(_('Warning'), _('You cant Select This Location, Please Select Stock / Output !'))
#               
#             if location_dest_id:
#                 loc_id = loc_obj.search(cr, uid, [('location_id', '=', location_dest_id)])
#                 if loc_id:
#                     raise osv.except_osv(_('Warning'), _('You cant Select This Location, Please Select Stock / Output !'))
        partner_id = vals.get('partner_id', '')
        partner = partner_obj.browse(cr, uid, partner_id)
        if partner_id:
            part_stock = partner.source_location_id.id
#             print "Partner Stock.....",part_stock
            pick_type_id = vals.get("picking_type_id")
            # This proces should work only if they create through Sale or Delivery Order not Through Stock moves
            if pick_type_id and not vals.get("picking_id"):
                pick_type = pick_type_obj.browse(cr, uid, [pick_type_id])
            # Update Customer Stock
                if part_stock and pick_type.code == "outgoing":
                    vals.update({
                                 'location_dest_id' : part_stock
                                })
                # Return delivery Order update Company Location    
                if part_stock and pick_type.code == "incoming":
                    vals.update({
                                 'location_dest_id' : location_dest_id
                                })
                else:            
                    if pick_type.code == "outgoing" and context.get('origin_returned_move_id') is False  and not part_stock:    
                        custloc_id = loc_obj.search(cr, uid, [('complete_name', '=', 'Partner Locations / Customers / Stock')])
                        if custloc_id:
                            custloc_id = custloc_id[0]
                        vals.update({
                                     'location_dest_id' : custloc_id
                                     })

        if vals.get("product_id"):
            destloc_id = vals.get("location_dest_id")
            if destloc_id:
                loc = loc_obj.browse(cr, uid, vals.get("location_dest_id"))
                if  loc.company_id:
                    vals.update({
                                 'company_id'   : loc.company_id.id,       
                                 })

            
        return super(stock_move, self).create(cr, uid, vals, context) 
   
    def write(self, cr, uid, ids, vals, context=None):
        prod_obj = self.pool.get("product.product")
        for move in self.browse(cr, uid, ids):
            qty = prod_obj._product_available(cr, uid, [move.product_id.id], None, False, context)
            qty = qty[move.product_id.id].get('qty_available',0)
#             qty = self.get_qty(cr, uid, move.product_id.id, move.location_id.id)
            cr.execute("update stock_move set available_qty=" + str(qty) + " where id =" + str(move.id))
        return super(stock_move, self).write(cr, uid, ids, vals, context)
    
    """
    Should not Select the Location which as  Children
    """
    def onchange_location_id(self, cr, uid, ids, location_id=False, location_dest_id=False, context=None):
        if not context:
            context = {}
        res = {}
        warning = ""
        loc_obj = self.pool.get("stock.location")
#         if context.get('type'): 
        if location_id:
            loc_ids = loc_obj.search(cr, uid, [('location_id', '=', location_id)])
            if loc_ids:
                res['location_id'] = False
                warning = {
                                             'title':_('Location Warning'),
                                                    'message':_(' You cant Select This Location, Please Select Stock / Output ')
                                                 }
        if location_dest_id:
            loc_ids = loc_obj.search(cr, uid, [('location_id', '=', location_dest_id)])
            if loc_ids:
                res['location_dest_id'] = False
                warning = {
                                             'title':_('Location Warning'),
                                                    'message':_(' You cant Select This Location, Please Select Stock / Output ')
                                                 }
                 
        return{'value':res , 'warning':warning}
        
 
    """ 
    Creating Invoice in which 
    some products are Returned.
    """
    
    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        pick_obj = self.pool.get("stock.picking")
        move_obj = self.pool.get("stock.move")
        soline_obj = self.pool.get("sale.order.line")
        invline_obj = self.pool.get("account.invoice.line")
        stkrtn_obj = self.pool.get("stock.return.picking")
        so_obj = self.pool.get("sale.order")
        sl_obj = self.pool.get("sale.order.line")
        update_line = False
        if not context:
            context = {}
           
           
        inv_lines = super(stock_move,self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)

        # updating tax for old dc's (coz, for old records procurement_id will not be there) TO BE UNCOMENT AFTER PROCESSING ALL OLD DCS   
        if  not move.procurement_id:    
            sale_tax = []
            cr.execute("select sale_line_id from stock_move where id=" + str(move.id))
            sl_id = cr.fetchone()
            if sl_id: 
                for tax in  sl_obj.browse(cr, uid, sl_id[0]).tax_id:
                    sale_tax.append(tax.id)
                if sale_tax:
                    inv_lines.update({'invoice_line_tax_id' : [(6, 0, sale_tax)]})

        
        hstry = stkrtn_obj.default_get(cr, uid,  ['product_return_moves', 'move_dest_exists', 'invoice_state'], context=context)

        pick_id = context.get('active_id',False)
        if pick_id:
            pick = pick_obj.browse(cr, uid,[pick_id])
            
        for m in hstry['product_return_moves']:
            if move.id in [x.id for x in pick.move_lines]: 
                if m['move_id'] == move.id:
                        if m['quantity'] <= move.product_qty:
                            inv_lines.update({
                                                    'quantity' : m['quantity']
                                                })
                            update_line = True
                            break
                        else:
                            update_line = False
                else:
                    update_line = False
            else:
                update_line = True    
                    
        if inv_lines:
            pick_id = context.get('active_id',False)
            if pick_id:
                pick = pick_obj.browse(cr, uid, [pick_id])
         
            if pick and pick.picking_type_id.code == 'outgoing':
                sale = pick.sale_id
                if sale:
                    for sol in  sale.order_line:
                        if sol.id == move.procurement_id.sale_line_id.id and (sol.reference or sol.discount):
                            inv_lines.update({
                                                 'reference'    :   sol.reference or '',
                                                 # Commented for Pricelist Concept
                                                'discount'     :   0.00,
                                                 })
                            
                 
        if update_line:                
            return inv_lines
        else:
            return False
     

stock_move()

class stock_warehouse_orderpoint(osv.osv):
    """
    Defines Minimum stock rules.
    """
    _inherit = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"
    _columns = {
#                 'body_text' : fields.text("Body Text"),
                   'prod_body' : fields.text("Products"),
                   'minqty_body' : fields.text("Minimum Quanity") 
                }
    
    """
    Sending a Mail to Warehouse,Sales,Purchase Managers 
    Every day if Stock Reaches the minimum Level
    """
    def send_mail(self, cr, uid, ids, context=None):
        to_emails = ''
        subject = ''
#         body = ''
        case = self.browse(cr, uid, ids)[0]
        mail_obj = self.pool.get("mail.mail")
        partner_obj = self.pool.get("res.partner")
        email_obj = self.pool.get('mail.template')
         
        cr.execute("""
                        select distinct rp.email
                            from res_groups_users_rel gu 
                            inner join res_groups g on g.id = gu.gid
                            inner join res_users ru on ru.id = gu.uid
                            inner join res_partner rp on rp.id = ru.partner_id
                            and g.category_id in (select id from ir_module_category where name in('Purchases','Warehouse','Sales'))
                            and g.name ='Manager' and rp.email is not null
                """)
         
        managers = [x[0] for x in cr.fetchall()]
        if managers:
            for m in managers:
                to_emails += m + ',' 
         
        template = self.pool.get('ir.model.data').get_object(cr, uid, 'magicemart', 'email_template_record_rule')
        email_obj.write(cr, uid, [template.id], {'email_to'      :  to_emails[:-1]})
        assert template._name == 'mail.template'
        mail_id = self.pool.get('mail.template').send_mail(cr, uid, template.id, case.id, True, context=context)
        return True

    """
    Schedular for Stock Re-Ordering
    """
    def do_stock_reorder(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
#     def do_stock_reorder(self, cr, uid, ids, context=None):
        print "inside schedular"
        mail_obj = self.pool.get("mail.mail")
        product_obj = self.pool.get("product.product")
        move_obj = self.pool.get("stock.move")
        reorder_ids = self.search(cr, uid, [])
        b = ''
        c = ''
        
        if reorder_ids:
            for case in self.browse(cr, uid, reorder_ids):
                available_qty = product_obj._product_available(cr, uid, [case.product_id.id], None, False, context)
                available_qty = available_qty[case.product_id.id].get('qty_available',0)
#                 available_qty = move_obj.get_qty(cr, uid, case.product_id.id, case.location_id.id)
                if available_qty <= case.product_min_qty:
                    b += case.product_id.name + '\n'
                    c += str(case.product_min_qty) + '\n'
            self.write(cr, uid, reorder_ids, {'prod_body': b , 'minqty_body': c})
            self.send_mail(cr, uid, [case.id], context=context)
        return True 
    


stock_warehouse_orderpoint()


class procurement_order(osv.osv):
    _inherit = "procurement.order"

    def run(self, cr, uid, ids, autocommit=False, context=None):
        new_ids = [x.id for x in self.browse(cr, uid, ids, context=context) if x.state not in ('running', 'done', 'cancel')]
        new_ids.sort()
        res = super(procurement_order, self).run(cr, uid, new_ids, autocommit=autocommit, context=context)

        #after all the procurements are run, check if some created a draft stock move that needs to be confirmed
        #(we do that in batch because it fasts the picking assignation and the picking state computation)
        move_to_confirm_ids = []
        for procurement in self.browse(cr, uid, new_ids, context=context):
            if procurement.state == "running" and procurement.rule_id and procurement.rule_id.action == "move":
                move_to_confirm_ids += [m.id for m in procurement.move_ids if m.state == 'draft']
        if move_to_confirm_ids:
            self.pool.get('stock.move').action_confirm(cr, uid, move_to_confirm_ids, context=context)
        return res


procurement_order()


# TO be Comment After Going To Live
# 
# class stock_warehouse(osv.osv):
#     _inherit = "stock.warehouse"
#     
#     def _create_locations_4oldRecords(self, cr, uid, ids, vals, context=None):
#         if context is None:
#             context = {}
#         if vals is None:
#             vals = {}
#             
#         data_obj = self.pool.get('ir.model.data')
#         seq_obj = self.pool.get('ir.sequence')
#         picking_type_obj = self.pool.get('stock.picking.type')
#         location_obj = self.pool.get('stock.location')
#         result = {}
#         
#         for warehouse in self.browse(cr, uid, ids, context):
#             # need Check Condition if Location Created Means Dont create again
#             if not warehouse.wh_input_stock_loc_id and not warehouse.wh_qc_stock_loc_id \
#                 and not warehouse.wh_pack_stock_loc_id and not warehouse.wh_output_stock_loc_id:
#                 #create view location for warehouse
#                 loc_vals = {
#                         'name': _(vals.get('code', warehouse.code)),
#                         'usage': 'view',
#                         'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_locations')[1],
#                 }
#                 if vals.get('company_id', warehouse.company_id.id):
#                     loc_vals['company_id'] = vals.get('company_id', warehouse.company_id.id)
#                 wh_loc_id = location_obj.create(cr, uid, loc_vals, context=context)
#                 vals['view_location_id'] = wh_loc_id
#                 
#                 #create all location
#                 def_values = self.default_get(cr, uid, {'reception_steps', 'delivery_steps'})
#                 reception_steps = vals.get('reception_steps',  def_values['reception_steps'])
#                 delivery_steps = vals.get('delivery_steps', def_values['delivery_steps'])
#                 context_with_inactive = context.copy()
#                 context_with_inactive['active_test'] = False
#                 
#                 sub_locations = [
#                     {'name': _('Stock'), 'active': True, 'field': 'lot_stock_id'},
#                     {'name': _('Input'), 'active': reception_steps != 'one_step', 'field': 'wh_input_stock_loc_id'},
#                     {'name': _('Quality Control'), 'active': reception_steps == 'three_steps', 'field': 'wh_qc_stock_loc_id'},
#                     {'name': _('Output'), 'active': delivery_steps != 'ship_only', 'field': 'wh_output_stock_loc_id'},
#                     {'name': _('Packing Zone'), 'active': delivery_steps == 'pick_pack_ship', 'field': 'wh_pack_stock_loc_id'},
#                 ]
#                 for values in sub_locations:
#                     loc_vals = {
#                         'name': values['name'],
#                         'usage': 'internal',
#                         'location_id': wh_loc_id,
#                         'active': values['active'],
#                     }
#                     if vals.get('company_id', warehouse.company_id.id):
#                         loc_vals['company_id'] = vals.get('company_id', warehouse.company_id.id)
#                     location_id = location_obj.create(cr, uid, loc_vals, context=context_with_inactive)
#                     vals[values['field']] = location_id
#                 self.write(cr, uid, ids, vals, context=context)
#                 
#                 new_objects_dict = self.create_routes(cr, uid, warehouse.id, warehouse, context=context)
#                 self.write(cr, uid, ids, new_objects_dict, context=context)
#             return True
#   # TO be Comment After Going To Live  
#     def write(self, cr, uid, ids, vals, context=None):
#         if context is None:
#             context = {}
#         if vals is None:
#             vals = {}
#         result = {}
#         result = super(stock_warehouse,self).write(cr, uid, ids, vals, context=context)
#         for warehouse in self.browse(cr, uid, ids, context):
#             
#             if warehouse.id in (2,3,4):
#                 if ('wh_input_stock_loc_id' not in vals or 'wh_qc_stock_loc_id' not in vals or  
#                     'wh_output_stock_loc_id' not in vals or 'wh_pack_stock_loc_id' not in vals ):
#                     self._create_locations_4oldRecords(cr, uid, [warehouse.id], vals, context)
#                     
#                 if not warehouse.in_type_id and not warehouse.int_type_id and not warehouse.pick_type_id \
#                     and not warehouse.pack_type_id and not warehouse.out_type_id:    
#                     self.create_sequences_and_picking_types(cr, uid, warehouse, context=context)
#     
#         return result
#   
# stock_warehouse()
