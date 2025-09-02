/** @odoo-module **/

import {patch} from "@web/core/utils/patch";
import {ListController} from "@web/views/list/list_controller";
import {useService} from "@web/core/utils/hooks";

patch(ListController.prototype, {
    /**
     * @override
     */

    async setup() {
        super.setup();
        this.orm = useService("orm");

        const currentUser = await this.orm.call(
            "res.users",
            "get_is_hide_archive_and_applied_models"
        );
        this.is_hide_archive = currentUser.is_hide_archive;
        this.applied_models = currentUser.applied_archive_models_ids;

        if (
            this.props.resModel &&
            this.applied_models.some(
                (modelData) => modelData[1] === this.props.resModel
            )
        ) {
            self.model = this.props.resModel;
        }
    },

    get actionMenuItems() {
        const actionMenus = super.actionMenuItems;

        if (this.props.resModel === self.model) {
            const {action} = actionMenus;

            const filteredAction = action.filter((item) => item.key !== "archive");

            actionMenus.action = filteredAction;
        }

        if (this.is_hide_archive) {
            const {action} = actionMenus;

            const filteredAction = action.filter((item) => item.key !== "archive");

            actionMenus.action = filteredAction;
        }

        return actionMenus;
    },
});
