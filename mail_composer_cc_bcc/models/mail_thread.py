
from odoo import models

# from .mail_mail import format_emails


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # ------------------------------------------------------------
    # MAIL.MESSAGE HELPERS
    # ------------------------------------------------------------

    def _get_message_create_valid_field_names(self):
        """
        add cc and bcc field to create record in mail.mail
        """
        field_names = super()._get_message_create_valid_field_names()
        field_names.update({"recipient_cc_ids", "recipient_bcc_ids"})
        return field_names

    # ------------------------------------------------------
    # NOTIFICATION API
    # ------------------------------------------------------

    def _notify_by_email_get_base_mail_values(self, message, recipients_data, additional_values=None):
        """
        This is to add cc, bcc addresses to mail.mail objects so that email
        can be sent to those addresses.
        """
        res = super()._notify_by_email_get_base_mail_values(
            message, recipients_data, additional_values=additional_values
        )
        context = self.env.context
        mail_mail = self.env["mail.mail"]
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            res["email_cc"] = mail_mail._format_emails(partners_cc)

        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            res["email_bcc"] = mail_mail._format_emails(partners_bcc)

        return res

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        """
        Add CC / BCC recipients coming from mail composer,
        ensuring main TO partner is included.
        """
        ResPartner = self.env["res.partner"]
        MailFollowers = self.env["mail.followers"]

        rdata = super()._notify_get_recipients(message, msg_vals, **kwargs)

        context = self.env.context
        if not context.get("is_from_composer"):
            return rdata

        # Get main TO partner IDs from rdata
        main_partner_ids = [d['id'] for d in rdata if d.get('id')]

        # Context contains CC/BCC IDs
        cc_ids = context.get("partner_cc_ids", [])
        bcc_ids = context.get("partner_bcc_ids", [])

        # Combine all unique partner IDs
        all_partner_ids = list(set(main_partner_ids + cc_ids + bcc_ids))
        partners_cc_bcc = ResPartner.browse(all_partner_ids)

        # Build recipients dict for all these partners
        message_type = msg_vals.get("message_type") if msg_vals else message.sudo().message_type
        subtype_id = msg_vals.get("subtype_id") if msg_vals else message.sudo().subtype_id.id

        recipients_data = MailFollowers._get_recipient_data(None, message_type, subtype_id, partners_cc_bcc.ids)

        # Flatten and merge into rdata
        for _, pdata_dict in recipients_data.items():
            for partner_id, pdata in pdata_dict.items():
                if not any(d.get("id") == partner_id for d in rdata):
                    partner = ResPartner.browse(partner_id)
                    rdata.append({
                        "id": partner.id,
                        "name": partner.name,
                        "uid": partner.user_ids[:1].id or False,
                        "active": pdata.get("active"),
                        "share": pdata.get("share"),
                        "notif": pdata.get("notif") or "email",
                        "type": "customer",
                        "is_follower": pdata.get("is_follower"),
                        "email_normalized": partner.email_normalized,
                    })

        return rdata

    # def _notify_get_recipients(self, message, msg_vals, **kwargs):
    #     """
    #     Add CC / BCC recipients coming from mail composer.
    #     """
    #     ResPartner = self.env["res.partner"]
    #     MailFollowers = self.env["mail.followers"]

    #     rdata = super()._notify_get_recipients(message, msg_vals, **kwargs)

    #     print("rdata in _notify_get_recipients:------------", rdata)

    #     context = self.env.context
    #     print("Context in _notify_get_recipients:------------", context)
    #     if not context.get("is_from_composer"):
    #         return rdata

    #     # Ensure existing recipients are marked correctly
    #     for pdata in rdata:
    #         pdata["type"] = "customer"

    #     # Context contains ID lists
    #     cc_ids = context.get("partner_cc_ids", [])
    #     bcc_ids = context.get("partner_bcc_ids", [])

    #     # Get main TO partner IDs from rdata
    #     main_partner_ids = [d['id'] for d in rdata if d.get('id')]

    #     # Combine all unique partner IDs (TO + CC + BCC)
    #     all_partner_ids = list(set(cc_ids + bcc_ids + main_partner_ids))

    #     if not all_partner_ids:
    #         return rdata

    #     # Browse all partners together
    #     partners_cc_bcc = ResPartner.browse(all_partner_ids)
    #     print("Partners CC BCC:------------", partners_cc_bcc)

    #     msg_sudo = message.sudo()
    #     message_type = msg_vals.get("message_type") if msg_vals else msg_sudo.message_type
    #     subtype_id = msg_vals.get("subtype_id") if msg_vals else msg_sudo.subtype_id.id

    #     recipients_cc_bcc = MailFollowers._get_recipient_data(
    #         None, message_type, subtype_id, partners_cc_bcc.ids
    #     )
    #     print("Recipients CC BCC:------------", recipients_cc_bcc)
    #     for _, value in recipients_cc_bcc.items():
    #         for _, data in value.items():
    #             partner_id = data.get("id")
    #             if not partner_id:
    #                 continue

    #             partner = ResPartner.browse(partner_id)

    #             existing_ids = {r["id"] for r in rdata if r.get("id")}

    #             if partner.id not in existing_ids:
    #                 rdata.append({
    #                     "id": partner.id,
    #                     "name": partner.name,
    #                     "uid": partner.user_ids[:1].id or False,
    #                     "active": data.get("active"),
    #                     "share": data.get("share"),
    #                     "notif": data.get("notif") or "email",
    #                     "type": "customer",
    #                     "is_follower": data.get("is_follower"),
    #                     "email_normalized": partner.email_normalized,
    #                 })
    #     return rdata

    # def _notify_get_recipients(self, message, msg_vals, **kwargs):
    #     """
    #     This is to add cc, bcc recipients so that they can be grouped with
    #     other recipients.
    #     """
    #     ResPartner = self.env["res.partner"]
    #     MailFollowers = self.env["mail.followers"]
    #     rdata = super()._notify_get_recipients(message, msg_vals, **kwargs)
    #     context = self.env.context
    #     is_from_composer = context.get("is_from_composer", False)
    #     if not is_from_composer:
    #         return rdata
    #     for pdata in rdata:
    #         pdata["type"] = "customer"
    #     partners_cc_bcc = context.get("partner_cc_ids", ResPartner)
    #     partners_cc_bcc += context.get("partner_bcc_ids", ResPartner)
    #     msg_sudo = message.sudo()
    #     message_type = (
    #         msg_vals.get("message_type") if msg_vals else msg_sudo.message_type
    #     )
    #     subtype_id = msg_vals.get("subtype_id") if msg_vals else msg_sudo.subtype_id.id
    #     recipients_cc_bcc = MailFollowers._get_recipient_data(
    #         None, message_type, subtype_id, partners_cc_bcc.ids
    #     )
    #     for _, value in recipients_cc_bcc.items():
    #         for _, data in value.items():
    #             if not data.get("id"):
    #                 continue
    #             if not data.get(
    #                 "notif"
    #             ):  # notif is False, has no user, is therefore customer
    #                 notif = "email"
    #             msg_type = "customer"
    #             pdata = {
    #                 "id": data.get("id"),
    #                 "active": data.get("active"),
    #                 "share": data.get("share"),
    #                 "notif": data.get("notif") and data.get("notif") or notif,
    #                 "type": msg_type,
    #                 "is_follower": data.get("is_follower"),
    #             }
    #             rdata.append(pdata)
    #     return rdata

    def _notify_get_recipients_classify(
        self, message, recipients_data, model_description, msg_vals=None
    ):
        res = super()._notify_get_recipients_classify(
            message, recipients_data, model_description, msg_vals=msg_vals
        )

        if not self.env.context.get("is_from_composer"):
            return res

        ids = []
        customer_data = None

        for rcpt_data in res:
            if rcpt_data.get("notification_group_name") == "customer":
                customer_data = rcpt_data
            else:
                ids += rcpt_data.get("recipients_ids", [])

        if not customer_data:
            customer_data = res[0]
            customer_data["notification_group_name"] = "customer"

        # 🔴 Normalize recipients key safely
        customer_data.setdefault(
            "recipients",
            customer_data.get("recipients_ids", []).copy(),
        )

        customer_data["recipients"] += ids

        return [customer_data]

