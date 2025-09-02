/** @odoo-module **/

import { registry } from "@web/core/registry";

const NOTIFICATION_TYPE = "odoos_notification";

// This service listens for our custom notification and uses Odoo's service to display a banner.
registry.category("services").add("uiNotificationService", {
    dependencies: ["bus_service", "notification"], // Add dependency on Odoo's notification service
    start(env, { bus_service, notification }) {
        console.log("--- DEBUG: uiNotificationService has started. ---");

        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            console.log("--- DEBUG: Bus service received a notification event:", notifications);

            for (const { payload, type } of notifications) {
                console.log(`--- DEBUG: Checking notification with type: ${type}`);
                
                if (type === NOTIFICATION_TYPE) {
                    console.log("--- DEBUG: Matched our notification type! Payload:", payload);
                    try {
                        notification.add(payload.message, {
                            title: payload.title,
                            type: payload.type,
                        });
                        console.log("--- DEBUG: Odoo notification.add() called successfully. ---");
                    } catch (e) {
                        console.error("--- DEBUG: Error calling notification.add():", e);
                    }
                }
            }
        });
    },
});