/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { DiscussService } from "@mail/core/common/discuss_service";
import { NotificationService } from "@web/core/notifications/notification_service";

/**
 * A helper function to process and forward a notification to the Flutter bridge.
 * This avoids code duplication in our patches.
 * @param {string | object} messageContent The message from the notification.
 */
function _forwardToFlutter(messageContent) {
    // Check if our special bridge channel exists.
    if (window.OdooNotificationBridge && window.OdooNotificationBridge.postMessage) {
        try {
            let cleanMessage = messageContent || "You have a new notification.";

            // Handle cases where the message is an object (e.g., from Owl components)
            if (typeof cleanMessage === 'object' && cleanMessage.trustedHTML) {
                cleanMessage = cleanMessage.trustedHTML;
            }

            // Create a temporary div to parse any potential HTML and extract clean text.
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = cleanMessage;
            const messageText = (tempDiv.textContent || tempDiv.innerText || "").trim();
            
            if (messageText) {
                console.log(`[Flutter Bridge] Forwarding notification: ${messageText}`);
                // Send the clean text message to our Flutter app.
                window.OdooNotificationBridge.postMessage(messageText);
            }
        } catch (e) {
            console.error("[Flutter Bridge] Failed to post message to Flutter:", e);
        }
    }
}

/**
 * Patch 1: The Discuss Service
 * This catches notifications related to mail threads, activities, etc.
 */
patch(DiscussService.prototype, "my_flutter_bridge.DiscussService", {
    notify(notification, options = {}) {
        const result = super.notify(...arguments);
        _forwardToFlutter(notification.message);
        return result;
    },
});

/**
 * Patch 2: The Core Notification Service
 * This is a more generic service that catches many other UI notifications,
 * including those from direct messages in Discuss.
 */
patch(NotificationService.prototype, "my_flutter_bridge.NotificationService", {
    add(props, options = {}) {
        const result = super.add(...arguments);
        // The structure here is different. The message is often in props.message or props.title.
        // We combine title and message for a more complete notification.
        const message = props.message ? `${props.title}: ${props.message}` : props.title;
        _forwardToFlutter(message);
        return result;
    },
});