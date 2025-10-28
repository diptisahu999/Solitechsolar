# -*- coding: utf-8 -*-
import base64
import re
import json
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
            Extract key details from this business card image in *pure JSON* format.
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
            gpt_output = re.sub(r"```(?:json)?|```", "", gpt_output).strip()

            try:
                parsed_data = json.loads(gpt_output)
            except json.JSONDecodeError:
                parsed_data = {"error": "Invalid JSON", "raw_response": gpt_output}

            self.extracted_text = json.dumps(parsed_data, indent=4, ensure_ascii=False)

        except Exception as e:
            self.extracted_text = f"GPT API Error: {str(e)}"

        return self._open_self_form()

    # ---------------------------------------------------------
    # Action: Create Lead from Extracted GPT Data
    # ---------------------------------------------------------
    def action_create_lead(self):
        """Parse GPT JSON and create a CRM Lead."""
        self.ensure_one()

        if not self.extracted_text:
            self.extracted_text = "No data extracted yet."
            return self._open_self_form()

        try:
            parsed = json.loads(self.extracted_text)
        except Exception:
            self.extracted_text = "Invalid extracted data format (not JSON)."
            return self._open_self_form()

        # Safely map fields
        lead_vals = {
            'name': parsed.get('name') or 'Lead from Business Card',
            'partner_name': parsed.get('company'),
            'contact_name': parsed.get('name'),
            'email_from': (parsed.get('emails') or [None])[0],
            'phone': (parsed.get('phone_numbers') or [None])[0],
            'mobile': (parsed.get('phone_numbers') or [None, None])[1] if len(parsed.get('phone_numbers', [])) > 1 else None,
            'website': parsed.get('website'),
            'function': parsed.get('designation'),
            'street': parsed.get('address') or '',
            'description': json.dumps(parsed, indent=4),
        }

        lead = self.env['crm.lead'].create(lead_vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'res_id': lead.id,
            'view_mode': 'form',
            'target': 'current',
            'name': _('Lead Created'),
        }

    # ---------------------------------------------------------
    # Helper: Return Form View
    # ---------------------------------------------------------
    def _open_self_form(self):
        """Reopen wizard form."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'name': _('Business Card Scanner (GPT)'),
        }
    
