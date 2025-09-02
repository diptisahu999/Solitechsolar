# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route, Controller


class ProductCatalogController(Controller):

    @route('/product/catalog/update_order_line_info', auth='user', type='json')
    def product_catalog_update_order_line_info(self, res_model, order_id, product_id, quantity=0, **kwargs):
        """ Update order line information on a given order for a given product.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param int product_id: The product, as a `product.product` id.
        :return: The unit price price of the product, based on the pricelist of the order and
                 the quantity selected.
        :rtype: float
        """
        order = request.env[res_model].browse(order_id)
        return order.with_context(is_catlog_product=True).with_company(order.company_id)._update_order_line_info(
            product_id, quantity, **kwargs,
        )
