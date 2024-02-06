from datetime import datetime

import requests
from jinja2 import Environment, FileSystemLoader

from api.buyer.services import BaseBuyerService
from api.document.services.document_v2 import DocumentServiceV2
from api.user.services import UserService
from core.utils.mail import send_mail
from emailer.utils import format_amount_with_commas

jinja_environment = Environment(loader=FileSystemLoader("templates"))


class OrderConfirmationEmail:
    def __init__(self):
        pass

    async def send(self, data):
        """
        Function to send email for Order Confirmation
        Args:
            data (dict): Data to trigger email
                user_id (UUID)
                document_id (UUID)
                tenant_id (UUID)
                document_url (str)

        """

        order_details = await DocumentServiceV2()._get_document_by_id(
            tenant_id=data["tenant_id"],
            user_id=data["user_id"],
            document_id=data["document_id"],
        )

        user_details = await UserService().get_user(order_details["created_by"])
        user_email = user_details.get("email", "__email__")
        buyer_details = await BaseBuyerService().get_buyer(order_details["buyer_id"])
        buyer_name = buyer_details.get("display_name", "buyer_name")
        # contact_details = await get_contact_details_from_buyer_id(
        #     order_details.get("buyer_id")
        # )
        # fname = contact_details.get("first_name", "there")
        # to_email = contact_details.get("email", "__email__")

        # wholesaler_name = await get_wholesaler_name_from_tenant_id(data["tenant_id"])

        order_value = order_details.get("total_value", "N/A")
        if order_value != "N/A":
            order_value = format_amount_with_commas(order_value)
        total_items = order_details.get("cart_details", {}).get("items", {})
        total_items = len(total_items.keys()) if total_items else "N/A"

        document_url = data.get("document_url")
        if document_url:
            document_content = requests.get(document_url).content

        order_creation_date = datetime.now()
        order_creation_date = order_creation_date.strftime("%m/%d/%Y")

        notification_email_ids = order_details.get("notification_email_ids", [])
        if not isinstance(notification_email_ids, list):
            notification_email_ids = []
        # notification_email_ids = (
        #     notification_email_ids if notification_email_ids else []
        # )
        # notification_email_ids = []
        if data.get("customer_service_email", ""):
            notification_email_ids.append(data["customer_service_email"])
        notification_email_ids.append(user_email)

        to_email = ",".join(notification_email_ids)
        to_email = to_email.strip(",")

        admin_list = [email_data.get("email") for email_data in data["internal_emails"]]
        admin_list = ",".join(admin_list) if admin_list else ""

        support_email_id = data.get("support_email")
        branding_image = data.get("branding_image")
        from_email = data.get("from_email")

        emailer_settings = {}   
        tenant_id = data.get("tenant_id")
        if tenant_id:
            emailer_settings = await SettingsUtils().get_settings_by_key(tenant_id, Emailer.EMAILER_SETTINGS)

        payload = {
            "order_number": order_details.get("system_id"),
            "buyer_name": buyer_name,
            "order_creation_date": order_creation_date,
            "order_value": order_value,
            "total_items": total_items,
            "support_email_id": support_email_id,
            "branding_image": branding_image,
        }
        template = jinja_environment.get_template("order_confirmation.html")
        output = template.render(payload)

        await send_mail(
            tenant_id=data.get("tenant_id", ""),
            from_mail=from_email,
            to_mail=to_email,
            cc_mail=admin_list,
            bcc_mail=[],
            subject_mail=f"Order confirmation - #{payload.get('order_number')} for {payload.get('buyer_name')}",
            file=output,
            attachment=[("attachment", ("OrderForm.pdf", document_content))]
            if document_url
            else None,
        )
