# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, tools
from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    # ---------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------

    def _to_partners(self, partners):
        """Accept recordset OR list of ids and return res.partner recordset"""
        if not partners:
            return self.env["res.partner"]
        if isinstance(partners, list):
            return self.env["res.partner"].browse(partners)
        return partners

    def _format_emails(self, partners):
        partners = self._to_partners(partners)
        emails = []
        for p in partners:
            email = p.email or p.email_normalized
            if email:
                emails.append(tools.formataddr((p.name or "", email)))
        return ", ".join(emails)

    def _format_emails_raw(self, partners):
        partners = self._to_partners(partners)
        emails = [p.email or p.email_normalized for p in partners if p.email or p.email_normalized]
        return ", ".join(emails)

    # ---------------------------------------------------------
    # Core override
    # ---------------------------------------------------------

    def _prepare_outgoing_list(self, mail_server=False, doc_to_followers=None):
        res = super()._prepare_outgoing_list(
            mail_server=mail_server,
            doc_to_followers=doc_to_followers,
        )

        # Only apply to single mail coming from composer
        if len(self.ids) > 1 or not self.env.context.get("is_from_composer"):
            return res

        # Prepare TO, CC, BCC partners
        partner_to = self.recipient_ids - (self.recipient_cc_ids | self.recipient_bcc_ids)
        partner_cc = self.recipient_cc_ids
        partner_bcc = self.recipient_bcc_ids

        # Format emails using email_normalized fallback
        email_to = self._format_emails(partner_to)
        email_to_raw = self._format_emails_raw(partner_to)
        email_cc = self._format_emails(partner_cc)
        email_bcc = self._format_emails(partner_bcc)

        # Update each mail in the outgoing list
        for m in res:
            # Ensure headers exist
            m.setdefault("headers", {})

            # If any TO recipient is also in BCC, mark header
            to_emails = set(extract_rfc2822_addresses(email_to))
            bcc_emails = set(extract_rfc2822_addresses(email_bcc))
            for e in to_emails & bcc_emails:
                m["headers"]["X-Odoo-Bcc"] = e

            # Update the mail object with proper TO, CC, BCC
            m.update({
                "email_to": email_to,
                "email_to_raw": email_to_raw,
                "email_cc": email_cc,
                "email_bcc": email_bcc,
            })

        return res
