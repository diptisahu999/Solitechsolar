# -- coding: utf-8 --
import base64
import re
import json
import requests
import urllib.parse
from odoo import models, fields, _
from openai import OpenAI
import os

# =========================================================
# ✅ GPT-Powered Business Card Scanner (No Tesseract)
# =========================================================

class BusinessCardScannerWizard(models.TransientModel):
    _name = 'business.card.scanner.wizard'
    _description = 'Business Card Scanner Wizard (GPT Powered)'

    business_card_image = fields.Binary(string="Business Card Image", required=True)
    extracted_text = fields.Text(string="Extracted JSON", readonly=True)
    scan_mode = fields.Selection([
        ('lead', 'Lead'),
        ('contact', 'Contact')
    ], string="Scan Mode", default='lead')

    # ---------------------------------------------------------
    # Action: Scan Card with GPT Vision
    # ---------------------------------------------------------
    def _get_openai_api_key(self):
        """Retrieve OpenAI API key safely."""
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        return key

    # ---------------------------------------------------------
    # Action: Scan Card with GPT Vision
    # ---------------------------------------------------------
    def action_scan_card(self):
        self.ensure_one()

        if not self.business_card_image:
            self.extracted_text = "No image uploaded."
            return self._open_self_form()

        try:
            # ✅ 1. Convert Odoo base64 to image data
            image_data = base64.b64decode(self.business_card_image)
            image_b64 = base64.b64encode(image_data).decode('utf-8')

            # ✅ 2. Get API Key safely
            api_key = self._get_openai_api_key()

            # ✅ 3. Initialize OpenAI client securely
            client = OpenAI(api_key=api_key)

            prompt = """
            You are a professional OCR and data extraction expert.
            Extract key details from this business card image in pure JSON format.
            Use this structure exactly:

            {
              "name": "",
              "designation": "",
              "company": "",
              "phone_numbers": [],
              "emails": [],
              "website": "",
              "address": ""
            }

            Return only valid JSON (no markdown or text outside the JSON).
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You extract business card details from images."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                        ],
                    },
                ],
                temperature=0.2,
            )

            gpt_output = response.choices[0].message.content
            gpt_output = re.sub(r"(?:json)?|", "", gpt_output).strip()

            try:
                parsed_data = json.loads(gpt_output)
            except json.JSONDecodeError:
                parsed_data = {"error": "Invalid JSON", "raw_response": gpt_output}

            self.extracted_text = json.dumps(parsed_data, indent=4, ensure_ascii=False)

        except Exception as e:
            self.extracted_text = f"GPT API Error: {str(e)}"

        return self._open_self_form()

    # ---------------------------------------------------------
    # ✅ Clean Mobile Number
    # ---------------------------------------------------------
    def _sanitize_mobile_for_webhook(self, raw_mobile: str) -> str:
        if not raw_mobile:
            return ''

        digits = re.sub(r'\D', '', raw_mobile)
        if not digits:
            return ''

        digits = digits.lstrip('0')

        # If 10 digits → assume Indian number
        if len(digits) == 10:
            digits = '91' + digits

        return digits

    # ---------------------------------------------------------
    # ✅ Send WhatsApp Message via Webhook
    # ---------------------------------------------------------
    def _send_whatsapp_webhook(self, mobile_number: str, parsed: dict) -> dict:
        try:
            if not mobile_number:
                return {'ok': False, 'error': 'No mobile found'}

            mobile = self._sanitize_mobile_for_webhook(mobile_number)
            print(f"Sanitized mobile for webhook: {mobile}")

            if not mobile:
                print("❌ Invalid mobile number after sanitizing")
                return {'ok': False, 'error': 'Invalid phone number'}

            base_url = 'https://webhook.whatapi.in/webhook/69032eee1b9845c02d42d75c'

            params = {
                'number': mobile,
                'title1': "Dear User",
                'title2': "Thank you for showing interest in SolitechSolar Pvt. Ltd.",
                'title3': "We are excited to connect with you and assist you with Product.",
                'title4': "SolitechSolar Pvt. Ltd.",
                'title5': "Thank you 🙏",
                'title6': " ",
                'title7': " ",

            }

            encoded = urllib.parse.urlencode(params)
            full_url = f"{base_url}?{encoded}"

            # ✅ Do NOT let this raise an exception
            try:
                resp = requests.get(full_url, timeout=10)

                # ✅ SUCCESS PRINT HERE 📌
                print(f"✅ WhatsApp message sent successfully to {mobile} | Status: {resp.status_code}")

                return {
                    'ok': True,
                    'status_code': resp.status_code,
                    'response': resp.text,
                    'url': full_url,
                }

            except Exception as e:
                print(f"❌ WhatsApp webhook error: {str(e)}")
                return {'ok': False, 'error': str(e), 'url': full_url}

        except Exception as e:
            print(f"❌ Unexpected error while sending WhatsApp: {str(e)}")
            return {'ok': False, 'error': str(e)}



    # ---------------------------------------------------------
    # ✅ Create Lead + Send WhatsApp message
    # ---------------------------------------------------------
    def action_create_lead(self):
        self.ensure_one()

        if not self.extracted_text:
            self.extracted_text = "No extracted data."
            return self._open_self_form()

        try:
            parsed = json.loads(self.extracted_text)
        except:
            self.extracted_text = "Invalid JSON data."
            return self._open_self_form()

        # Create tag "Card Scan"
        tag = self.env['crm.tag'].search([('name', '=', 'Card Scan')], limit=1)
        if not tag:
            tag = self.env['crm.tag'].create({'name': 'Card Scan'})

        lead_vals = {
            'name': parsed.get('name') or 'Lead From Business Card',
            'partner_name': parsed.get('company'),
            'contact_name': parsed.get('name'),
            'email_from': (parsed.get('emails') or [None])[0],
            'phone': (parsed.get('phone_numbers') or [None])[0],
            'mobile': (parsed.get('phone_numbers') or [None])[1] if len(parsed.get('phone_numbers', [])) > 1 else None,
            'website': parsed.get('website'),
            'function': parsed.get('designation'),
            'street': parsed.get('address'),
            'description': json.dumps(parsed, indent=4),
            'tag_ids': [(6, 0, [tag.id])],
        }

        lead = self.env['crm.lead'].create(lead_vals)

        # ✅ Choose best mobile number
        mobile = None
        if parsed.get('phone_numbers'):
            mobile = parsed['phone_numbers'][0]
        if not mobile:
            mobile = lead.phone or lead.mobile

        # ✅ Send WhatsApp webhook
        webhook_result = self._send_whatsapp_webhook(mobile, parsed)

        # ✅ Show webhook result inside wizard
        final_json = parsed
        final_json["_whatsapp_webhook"] = webhook_result

        self.extracted_text = json.dumps(final_json, indent=4, ensure_ascii=False)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
            'name': _('Lead Created'),
        }

    # ---------------------------------------------------------
    # ✅ Create Contact + Send WhatsApp message
    # ---------------------------------------------------------
    def action_create_contact(self):
        self.ensure_one()

        if not self.extracted_text:
            self.extracted_text = "No extracted data."
            return self._open_self_form()

        try:
            parsed = json.loads(self.extracted_text)
        except:
            self.extracted_text = "Invalid JSON data."
            return self._open_self_form()

        # Handle Company (Parent)
        company_name = parsed.get('company')
        parent_id = False
        if company_name:
            # Search for existing company or create it
            partner_company = self.env['res.partner'].search([('name', '=', company_name), ('is_company', '=', True)], limit=1)
            if partner_company:
                parent_id = partner_company.id
            else:
                # Optional: create the company if it doesn't exist? 
                # For now let's just set it if found, or maybe create it. 
                # Let's create it to be helpful.
                partner_company = self.env['res.partner'].create({
                    'name': company_name,
                    'is_company': True,
                    'street': parsed.get('address'),
                    'website': parsed.get('website'),
                })
                parent_id = partner_company.id

        partner_vals = {
            'name': parsed.get('name') or 'Unknown Contact',
            'person_contacts': parsed.get('name') or 'Unknown Contact',
            'parent_id': parent_id,
            'function': parsed.get('designation'),
            'email': (parsed.get('emails') or [None])[0],
            'phone': (parsed.get('phone_numbers') or [None])[0],
            'mobile': (parsed.get('phone_numbers') or [None])[1] if len(parsed.get('phone_numbers', [])) > 1 else None,
            'website': parsed.get('website'),
            'street': parsed.get('address'),
            'comment': json.dumps(parsed, indent=4),
            'type': 'contact',
        }

        # Use the first phone as mobile if mobile is empty but phone is set (common in parsing)
        if not partner_vals['mobile'] and partner_vals['phone']:
             partner_vals['mobile'] = partner_vals['phone']

        partner = self.env['res.partner'].create(partner_vals)

        # ✅ Choose best mobile number
        mobile = None
        if parsed.get('phone_numbers'):
            mobile = parsed['phone_numbers'][0]
        if not mobile:
            mobile = partner.mobile or partner.phone

        # ✅ Send WhatsApp webhook
        webhook_result = self._send_whatsapp_webhook(mobile, parsed)

        # ✅ Show webhook result inside wizard (if we were staying, but we are closing)
        final_json = parsed
        final_json["_whatsapp_webhook"] = webhook_result
        self.extracted_text = json.dumps(final_json, indent=4, ensure_ascii=False)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
            'name': _('Contact Created'),
        }

    # ---------------------------------------------------------
    # ✅ Reopen Wizard
    # ---------------------------------------------------------
    def _open_self_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'name': _('Business Card Scanner (GPT)'),
        }