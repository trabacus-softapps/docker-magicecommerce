FROM softapps/docker-odoobase
MAINTAINER Arun T K <arun.kalikeri@xxxxxxxx.com>
ADD additional_addons/pentaho_reports /opt/odoo/additional_addons/pentaho_reports
ADD additional_addons/Trabacus_base  /opt/odoo/additional_addons/Trabacus_base
ADD additional_addons/Trabacus /opt/odoo/additional_addons/Trabacus
ADD additional_addons/Trabacus_ATE /opt/odoo/additional_addons/Trabacus_ATE
ADD additional_addons/Trabacus_API /opt/odoo/additional_addons/Trabacus_API
ADD additional_addons/Tr_Website /opt/odoo/additional_addons/Tr_Website
RUN chown -R odoo:odoo /opt/odoo/additional_addons/
