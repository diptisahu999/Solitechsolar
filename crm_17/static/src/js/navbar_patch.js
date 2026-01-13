/** @odoo-module */

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onPatched, useState, onWillDestroy } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.user = useService("user");

        // Use useState to make it reactive if we were using it in the template, 
        // but here we are using it to trigger effect/DOM update manually.
        this.approvalState = useState({
            adminCount: 0,
            myCount: 0
        });

        this.updateApprovalCount = async () => {
            try {
                // 1. Admin Count: All orders in 'price_approval'
                const adminCount = await this.orm.searchCount("sale.order", [
                    ["state", "=", "price_approval"]
                ]);

                // 2. My Count: My orders in 'price_approval'
                // We use the user service to get the current user ID
                const myCount = await this.orm.searchCount("sale.order", [
                    ["state", "=", "price_approval"],
                    ["user_id", "=", this.user.userId]
                ]);

                this.approvalState.adminCount = adminCount;
                this.approvalState.myCount = myCount;

                this.renderApprovalBadge();
            } catch (e) {
                // Silent fail if access denied or other issue
                console.debug("Could not fetch approval count:", e);
            }
        };

        onMounted(() => {
            this.updateApprovalCount();
            // Poll every 10 seconds
            this.approvalInterval = setInterval(this.updateApprovalCount, 10000);
        });

        onPatched(() => {
            this.renderApprovalBadge();
        });

        onWillDestroy(() => {
            if (this.approvalInterval) {
                clearInterval(this.approvalInterval);
            }
        });
    },

    renderApprovalBadge() {
        this._renderBadgeForMenu("crm_17.menu_sale_price_approval", "Price Approvals", this.approvalState.adminCount);
        this._renderBadgeForMenu("crm_17.menu_sale_my_price_requests", "My Approvals", this.approvalState.myCount);
    },

    _renderBadgeForMenu(xmlId, fallbackText, count) {
        // Target the specific menu item by its XML ID
        // Note: The XML ID must be fully qualified.
        let menuElement = document.querySelector(`a[data-menu-xmlid="${xmlId}"]`);

        // Fallback: Try finding by text content inside nav entries if attribute missing
        if (!menuElement) {
            const links = document.querySelectorAll('.o_nav_entry, .dropdown-item');
            for (const link of links) {
                if (link.textContent.includes(fallbackText)) {
                    menuElement = link;
                    break;
                }
            }
        }

        if (menuElement) {
            // Check if badge already exists
            let badge = menuElement.querySelector('.o_approval_badge');

            // Create if missing and we have count
            if (!badge) {
                badge = document.createElement('span');
                badge.classList.add('badge', 'rounded-pill', 'bg-danger', 'ms-1', 'o_approval_badge');
                badge.style.fontSize = "0.7em";
                badge.style.verticalAlign = "top";
                badge.style.marginLeft = "5px"; // Force spacing
                menuElement.appendChild(badge);
            }

            if (count > 0) {
                badge.innerText = count;
                badge.style.display = 'inline-block';
                // Add a little visual pop?
                badge.classList.remove('d-none');
            } else {
                badge.style.display = 'none';
                badge.classList.add('d-none');
            }
        }
    }
});
