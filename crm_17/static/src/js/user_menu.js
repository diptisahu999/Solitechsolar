/** @odoo-module **/

import { registry } from "@web/core/registry";
import "@web/webclient/user_menu/user_menu_items";

const userMenuItems = registry.category("user_menuitems");

// Remove unwanted items
userMenuItems.remove("documentation");
userMenuItems.remove("support");
userMenuItems.remove("odoo_account");