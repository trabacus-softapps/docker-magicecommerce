import datetime
from lxml import etree
import math
import pytz
import re
import time
from dateutil import parser
from lxml import etree
from dateutil import parser
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import openerp
from openerp import SUPERUSER_ID
from openerp import pooler, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from openerp.tools import html2plaintext
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
import base64
import xmlrpclib
from openerp.tools import config
host = str(config["xmlrpc_interface"])  or str("localhost"),
port = str(config["xmlrpc_port"])
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (host[0], port))


class mail_compose_message(osv.TransientModel):
    _name = 'mail.compose.message'
    _inherit = 'mail.compose.message'
    _description = 'Email composition wizard'
    _log_access = True
   
    _columns = {
                'm_attachment_id':fields.many2one('ir.attachment', 'Required Documents'),
        'partner_cc_ids': fields.many2many('res.partner',
            'mail_compose_message_res_partner_cc_rel',
            'wizard_id', 'partner_id', 'Recipients-CC'),
        'partner_bcc_ids': fields.many2many('res.partner',
            'mail_compose_message_res_partner_bcc_rel',
            'wizard_id', 'partner_id', 'Recipients-BCC'),
                }
    
    def onchange_attachments(self, cr, uid, ids, m_attachment_id, attachment_ids, context=None):
        res = {}
        s = set()
        for attach in [m_attachment_id]:
            s.add(attach)
        for at in attachment_ids:
            s.add(at[1])
        attach_ids = list(s)
        res['attachment_ids'] = [(4, attach_ids)]
        return{'value':res}    

# It Will Attach The Attachment Automatically Form The Report When YOu Click The  Send By Mail
    def onchange_template_id(self, cr, uid, ids, template_id, composition_mode, model, res_id, context=None):
        res = {}
        user_obj = self.pool.get('res.users')
        for user in user_obj.browse(cr, uid, [uid]):
            USERPASS = user.password
              
        partner_obj = self.pool.get('res.partner')
        model_obj = context.get('active_model', False)
        data = context.get('active_res_id', False)
        temp_obj = self.pool.get('mail.template')
        sale_obj = self.pool.get('sale.order')
        attch_obj = self.pool.get('ir.attachment') 
        po_obj = self.pool.get("purchase.order")
        temp_name = temp_obj.browse(cr, uid, template_id)
        vlus = super(mail_compose_message, self).onchange_template_id(cr, uid, ids, template_id, composition_mode, model, res_id, context=context)
        if vlus:
            res = vlus['value']
                 
            if not context:
                return vlus
              
            if model_obj == 'sale.order':
                if template_id:
                    if temp_name.name == 'Sales Order - Send by Email' or temp_name.name == 'Sale Order - Send By Email(Customer Portal)':
                        for ln in sale_obj.browse(cr, uid, [res_id]):
                            id = ln.id
                          
            if model_obj == 'purchase.order':
                  if template_id:
                      if temp_name.name in ('Purchase Order - Send by Email', "Purchase Order - Send By Email(Supplier Portal)"):
                          for ln in po_obj.browse(cr, uid, [res_id]):
                              id = ln.id
            return {'value':res}
                    
#                         report_name = "Sales Quotation" +" - "+ ln.name 
#                         report_service = "report." + 'Sales Quotation'
#                         service = netsvc.LocalService(report_service)
#                         (result, format) = service.create(cr, uid, [res_id], {'model': 'sale.order'}, context)
#                         result = base64.b64encode(result)
#                         if not report_name:
#                             report_name = report_service
#                         ext = "." + format
#                         if not report_name.endswith(ext):
#                             report_name += ext
#                             
#                         aId = attch_obj.search(cr, uid,[('res_id','=',res_id),('res_model', '=', 'sale.order'), ('name', '=', str(report_name))])
# #                         print "Res..........",('res_id', '=', str(res_id)), ('res_model', '=', 'sale.order'), ('name', '=', str(report_name))
# #                         aId = sock.execute(cr.dbname, uid, USERPASS, 'ir.attachment' , 'search', [('res_id', '=', str(res_id)), ('res_model', '=', 'sale.order'), ('name', '=', str(report_name))])
#                         for usr in user_obj.browse(cr, uid, [uid]):
#                             partner = usr.partner_id.id
#                        
#                         if not aId:
#                             attach_ids = attch_obj.create(cr, uid,
#                                 {
#                                 'res_model'  : 'sale.order',
#                                 'res_name'   : report_name,
#                                 'res_id'     : res_id,
#                                 'datas'      : result ,
#                                 'type'       : 'binary',
#                                 'datas_fname': report_name,
#                                 'name'       : report_name,
#                                 'partner_id' : partner,
#                                  },
#                             context=context) 
#                             res['attachment_ids'] = [(4, attach_ids)]
#                         else:
#                             print "AID........",aId
#                             attach_ids = { 
#                                     'datas'   :result ,
#                                     }
#                             attach_ids = attch_obj.write(cr, uid, aId, attach_ids, context=context) 
#                             res['attachment_ids'] = [(4, aId[0])]
# #                         temp_obj.write(cr,uid,[temp_name.id],{'attachment_ids':res['attachment_ids']},context)    
#                          
#             if model_obj == 'purchase.order':
#                   if template_id:
#             #                     print "template ", temp_name.name
#                       if temp_name.name in ('Purchase Order - Send by mail', "Purchase Order - Send By Email(Supplier Portal)"):
#                           for ln in po_obj.browse(cr, uid, [res_id]):
#                               id = ln.id
#                            # report name is the service name given in pentaho report menu
#                            
#                           report_name = "Purchase Order - " + ln.name 
#                           report_service = "report." + 'Purchase Order'
#                           service = netsvc.LocalService(report_service)
#                           (result, format) = service.create(cr, uid, [res_id], {'model': 'purchase.order'}, context)
#                           result = base64.b64encode(result)
#                           print 'esult',result
#                           if not report_name:
#                               report_name = report_service
#                           ext = "." + format
#                           if not report_name.endswith(ext):
#                               report_name += ext
#                            
#                           aId = sock.execute(cr.dbname, uid, USERPASS, 'ir.attachment' , 'search', [('res_id', '=', str(res_id)), ('res_model', '=', 'purchase.order'), ('name', '=', str(report_name))])
#                           for usr in user_obj.browse(cr, uid, [uid]):
#                               partner = usr.partner_id.id
#                          
#                           if not aId:
#                               attval = {
#                                   'res_model'  : 'purchase.order',
#                                   'res_name'   : str(report_name),
#                                   'res_id'     : str(res_id),
#                                   'datas'      : str(result) ,
#                                   'type'       : 'binary',
#                                   'datas_fname': str(report_name),
#                                   'name'       : str(report_name),
#                                   'partner_id' : partner,
#                                    }
#                              
#                               attach_ids = sock.execute(cr.dbname, uid, USERPASS, 'ir.attachment', 'create', attval)
#                               res['attachment_ids'] = [(4, attach_ids)]
#                           else:
#                                for f in aId:
#                                   attval = { 
#                                       'datas'   :str(result) ,
#                                       }
#                                   sock.execute(cr.dbname, uid, USERPASS, 'ir.attachment', 'write', aId, attval)
#                                   res['attachment_ids'] = [(4, aId)]
#  
 

    
    def send_mail(self, cr, uid, ids, context=None):
        context = context or {}
        sale_obj = self.pool.get('sale.order')
        res = super(mail_compose_message, self).send_mail(cr, uid, ids, context=context)
        
        cr.execute("""select uid from res_groups_users_rel where gid=
                      (select id  from res_groups where category_id in 
                      ( select id from ir_module_category where name = 'Customer Portal' ) and name = 'Manager') and uid = """+str(uid))
        print "ctx", context
        portal_user = cr.fetchone() 
        portal_group = portal_user and portal_user[0]
        
        if uid == portal_group:
            if context.get('active_id', False):
                sale_obj.write(cr, uid, [context.get('active_id')], {'sent_portal':True})
                
        if context.get('default_model') == 'sale.order' and context.get('default_res_id') and context.get('mark_so_as_sent'):
                context = dict(context, mail_post_autofollow=True)
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'sale.order', context['default_res_id'], 'quotation_sent', cr)
                
        return True
    
mail_compose_message()