from odoo import models, fields, api
from datetime import datetime, timedelta
import re

class InheritProductTemplate(models.Model):
    _inherit = "product.template"
    _order = 'default_code asc'

    extra_charges = fields.Boolean("Extra Charges")
    name = fields.Char('Name', index='trigram', required=True, translate=True,tracking=True)
    list_price = fields.Float(
        'Sales Price', default=1.0,
        digits='Product Price',
        help="Price at which the product is sold to customers.",tracking=True)
    standard_price = fields.Float(
        'Cost', compute='_compute_standard_price',
        inverse='_set_standard_price', search='_search_standard_price',
        digits='Product Price', groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""",tracking=True)
    default_code = fields.Char(
        'Internal Reference', compute='_compute_default_code',
        inverse='_set_default_code', store=True,tracking=True)
    barcode = fields.Char('Barcode', compute='_compute_barcode', inverse='_set_barcode', search='_search_barcode',tracking=True)
    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id', help="Default taxes used when selling the product.", string='Customer Taxes',
        domain=[('type_tax_use', '=', 'sale')],
        default=lambda self: self.env.companies.account_sale_tax_id or self.env.companies.root_id.sudo().account_sale_tax_id,tracking=True)
    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", help="Harmonized System Nomenclature/Services Accounting Code",tracking=True)
    sampling_ok = fields.Boolean('Sampling Possible')
    returnable_ok = fields.Boolean('Returnable')
    last_seq =  fields.Integer("Last Sequence",copy=False,tracking=True)
    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')],
        string="Tracking", required=True, default='serial',
        compute='_compute_tracking', store=True, readonly=False, precompute=True,tracking=True,
        help="Ensure the traceability of a storable product in your warehouse.")
    print_ok = fields.Boolean('Barcode Printed')
    no_discount_ok = fields.Boolean('No Discount')
    ecommerce_ok = fields.Boolean('Ecommerce Product')
    shortly_discontinue = fields.Boolean('Shortly Discontinue')
    dead_stock = fields.Boolean('Dead stock')
    width = fields.Float(string="Width")
    is_width = fields.Boolean(related='categ_id.is_width')
    is_not_check_stock = fields.Boolean('Process without Stock Check')
    is_tile = fields.Boolean('Tile')
    tile_width = fields.Float(string="Tile Width (mm)")
    tile_length = fields.Float(string="Tile Length (mm)")
    tiles_per_box = fields.Integer(string="Tile per Box")
    action_link = fields.Html(string='View', compute='_compute_action_link', sanitize=False)
    upstock_qty = fields.Char(string='UP Stock', compute='_compute_upstock_qty')
    reserved_qty = fields.Float(string="Reserved QTY")
    minimum_stock = fields.Integer("Minimum Stock")
    is_recommended = fields.Boolean('Recommended Product')
    is_order = fields.Boolean('Make to Order')
    is_customization = fields.Boolean('Make to Customization')
    is_color_coating = fields.Boolean('Color Coating Possible')
    is_discontinue = fields.Boolean('Discontinue')
    wattage = fields.Float(string="Wattage (Wp)")
    product_subsidy_type = fields.Selection([
        ('dcr', 'DCR'),
        ('non_dcr', 'Non DCR')
    ], string='Product Category', default='non_dcr', index=True)

    min_unit_price_watt = fields.Float(
        string='Unit Price (₹/Wp)',
        default=0.0,
        help='Minimum allowed unit price (₹/Wp). If Sales Price is below this, Price Approval is required.'
    )

    dcr_rate = fields.Float(
        string="DCR Price",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('crm_17.global_dcr_rate', 0.0))
    )
    non_dcr_rate = fields.Float(
        string="NON-DCR Price",
        default=lambda self: float(self.env['ir.config_parameter'].sudo().get_param('crm_17.global_non_dcr_rate', 0.0))
    )

    def action_update_dcr_logic(self):
        # Update selected products
        # If called from a button or server action, 'self' contains the recordset.
        # Fallback to search([]) only if self is empty (e.g. called from a scheduled action without context)
        products = self or self.search([])
        for product in products:
            if product.name and 'DCR' in product.name.upper():
                product.product_subsidy_type = 'dcr'
            else:
                product.product_subsidy_type = 'non_dcr'

    def action_print_products_details(self):       
        return self.env.ref('crm_17.action_techv_product_template_pricelist').report_action(self)

    @api.depends('name')
    def _compute_action_link(self):
        menu_id = self.env.ref('stock.menu_product_variant_config_stock').id
        for record in self:
            url = f'/web#id={record.id}&model=product.template&view_type=form&cids={record.company_id.id}&menu_id={menu_id}'
            record.action_link = f'<a href="{url}" target="_blank">View</a>'

    def _compute_upstock_qty(self):
        for pro in self.sudo():
            products = self.env['product.product'].sudo().search([('product_tmpl_id', '=', pro.id)])
            if products:
                upcoming_stock = self.env['upcoming.stock'].sudo().search(
                    [('product_id', 'in', products.ids)],
                    order='id desc', limit=1
                )
                if upcoming_stock:
                    formatted_date = upcoming_stock.date.strftime('%d/%m/%Y') if upcoming_stock.date else ''
                    pro.upstock_qty = f"{int(upcoming_stock.qty)} Qty. ({formatted_date})"
                else:
                    pro.upstock_qty = False
            else:
                pro.upstock_qty = False

                # grouped_data = self.env['reserved.stock'].sudo().read_group(
                #     domain=[('product_id', '=', product.id), ('reserved_type', '=', 'reserved')],
                #     fields=['reserved_qty'],
                #     groupby=['product_id']
                # )

                # if grouped_data:
                #     reserved_qty = grouped_data[0]['reserved_qty'] or 0
                # else:
                #     reserved_qty = 0

                # pro.reserved_qty = pro.qty_available - reserved_qty

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # Clear cache dynamically to reflect changes immediately
        #self.env['ir.model.fields'].clear_caches()
        fields_info = super().fields_get(allfields, attributes)

        has_page_access = self.env.user.has_group('crm_17.group_product_page_access')
        has_price_access = self.env.user.has_group('crm_17.group_product_price')

        if not has_page_access:
            for field in fields_info:
                if field == 'list_price' and has_price_access:
                    continue
                fields_info[field]['readonly'] = True
                fields_info[field]['force_save'] = True
        
        if has_page_access and not has_price_access:
            if 'list_price' in fields_info:
                fields_info['list_price']['readonly'] = True
                fields_info['list_price']['force_save'] = True

        return fields_info
    
    def update_last_seq(self):
        for pro in self.search([]):
            product = self.env['product.product'].sudo().search([('product_tmpl_id', '=', pro.id)])
            lot_rec = self.env['stock.lot'].sudo().search([('product_id', '=', product.id),('name', '!=', False)], order='name desc', limit=1)
           
            if lot_rec and lot_rec.name:
                match = re.search(r'\d+$', lot_rec.name[-5:])
                if match:
                    pro.last_seq = int(match.group())
            else:
                pro.last_seq = 0

class InheritProductProduct(models.Model):
    _inherit = "product.product"

    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
                (do not use for purchases or other display reasons that don't intend to use "description_sale").
            It will often be used as the default description of a sale order line referencing this product.
        """
        if self.description_sale:
            name = self.description_sale if self.description_sale else ''
        else:
            name = self.name
        # if self.description_sale:
        #     name += '\n' + self.description_sale
        return name

class InheritProductCategory(models.Model):
    _inherit = "product.category"

    is_width = fields.Boolean("Is Width Required")

