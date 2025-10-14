/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DiscussService } from "@mail/core/common/discuss_service";
import { markup } from "@odoo/owl";

/**
 * Patches Odoo's notification service to forward messages to our Flutter app.
 */
patch(DiscussService.prototype, "my_flutter_bridge", {
    
    /**
     * Odoo calls this method to display a new notification. We will intercept it.
     * @override
     */
    notify(notification, options = {}) {
        // First, call the original Odoo function to let the web UI show the notification as usual.
        const result = super.notify(...arguments);

        // Now, check if our special bridge channel exists.
        // This 'OdooNotificationBridge' is what we will create in Flutter.
        if (window.OdooNotificationBridge && window.OdooNotificationBridge.postMessage) {
            try {
                // The notification message can be HTML. We need to strip the HTML tags
                // to get a clean string for the mobile notification.
                let cleanMessage = notification.message || "You have a new notification.";
                if (typeof cleanMessage === 'object' && cleanMessage.trustedHTML) {
                    cleanMessage = cleanMessage.trustedHTML;
                }

                // Create a temporary div to parse HTML and extract text content.
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = cleanMessage;
                const messageText = tempDiv.textContent || tempDiv.innerText || "";
                
                console.log(`[Flutter Bridge] Sending notification: ${messageText}`);
                
                // Send the clean text message to our Flutter app.
                // The message must be a string.
                window.OdooNotificationBridge.postMessage(messageText.trim());

            } catch (e) {
                console.error("[Flutter Bridge] Failed to post message to Flutter:", e);
            }
        } else {
            console.log("[Flutter Bridge] Not running inside the Flutter WebView or bridge is not available.");
        }
        
        return result;
    }
});