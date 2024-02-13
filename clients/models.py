from django.db import models
from dashboard.models import Profile

def get_json_default():
    return []

SUBS_STATUS = (
    ("active", "Active"),
    ("inactive", "Inactive"),
)

CLIENT_STATUS = (
    ("active", "Active"),
    ("hold", "Hold"),
    ("inactive", "Inactive"),
)

class Client(models.Model):
    """
        Used to store Client Information. 
    """
    old_id = models.IntegerField(default=0)
    company_name = models.CharField(max_length=100)
    company_website = models.CharField(max_length=255, default="None", null=True, blank=True)
    company_linkedin = models.CharField(max_length=255, default="None", null=True, blank=True)
    company_contact_full_name = models.CharField(max_length=255, default="None", null=True, blank=True)
    company_contact_phone = models.CharField(max_length=255, default="None", null=True, blank=True)
    company_contact_email = models.CharField(max_length=255, default="None", null=True, blank=True)
    
    logo = models.FileField(upload_to="logo", null=True, blank=True)
    # Client Admin Details
    ca_profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="ca_profile")
    
    # HR Details
    hr_first_name = models.CharField(max_length=255, blank=True, null=True)
    hr_last_name = models.CharField(max_length=255, blank=True, null=True)
    hr_contact_phone_no = models.CharField(max_length=50, blank=True, null=True)
    hr_contact_skype_id = models.CharField(max_length=512, blank=True, null=True)
    hr_contact_email = models.CharField(max_length=100, blank=True, null=True)

    # CTO Details
    cto_first_name = models.CharField(max_length=255, blank=True, null=True)
    cto_last_name = models.CharField(max_length=255, blank=True, null=True)
    cto_phone_no = models.CharField(max_length=50, blank=True, null=True)
    cto_skype_id = models.CharField(max_length=512, blank=True, null=True)
    cto_email = models.CharField(max_length=100, blank=True, null=True)

    # Billing Person Details
    billing_first_name = models.CharField(max_length=255, blank=True, null=True)
    billing_last_name = models.CharField(max_length=255, blank=True, null=True)
    billing_phone_no = models.CharField(max_length=50, blank=True, null=True)
    billing_email = models.CharField(max_length=100, blank=True, null=True)
    billing_addr_line_1 = models.TextField(default=None, blank=True, null=True)
    billing_addr_line_2 = models.TextField(default=None, blank=True, null=True)
    billing_city = models.CharField(max_length=255, default=None, blank=True, null=True)
    billing_state = models.CharField(max_length=255, default=None, blank=True, null=True)
    billing_pincode = models.CharField(max_length=10, default=None, blank=True, null=True)

    addr_line_1 = models.TextField(default=None, blank=True, null=True)
    addr_line_2 = models.TextField(default=None, blank=True, null=True)
    city = models.CharField(max_length=255, default=None, blank=True, null=True)
    state = models.CharField(max_length=255, default=None, blank=True, null=True)
    pincode = models.CharField(max_length=10, default=None, blank=True, null=True)

    special_req = models.CharField(max_length=500, null=True, blank=True)

    # Account Manager which is assinged - In Qorums it is Qorum Support and only visible to SA
    ae_assigned = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="ae_assigned")
    disabled = models.BooleanField(default=False)
    status = models.CharField(max_length=255, choices=CLIENT_STATUS, default="active")
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Package(models.Model):
    name = models.CharField(max_length=255)
    key_masters_accounts = models.IntegerField(default=1)
    senior_managers = models.IntegerField(default=1)
    hiring_managers = models.IntegerField(default=1)
    hiring_team_members = models.IntegerField(default=1)
    contributors = models.IntegerField(default=1)
    open_positions = models.IntegerField(default=3)
    multilevel_onboarding = models.BooleanField(default=True)
    muli_company = models.BooleanField(default=False)
    price = models.IntegerField(default=50000)
    current_charge_tooltip = models.CharField(max_length=255, default=None, null=True, blank=True)
    future_charge_tooltip = models.CharField(max_length=255, default=None, null=True, blank=True)

class ClientPackage(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)
    is_trial = models.BooleanField(default=False)
    trial_expired  = models.DateField(default=None, null=True, blank=True)
    # stripe details
    strip_subs_id = models.CharField(max_length=255, default=None, null=True, blank=True)
    strip_subs_status = models.CharField(max_length=255, choices=SUBS_STATUS, default="inactive", null=True, blank=True)
    old_status = models.CharField(max_length=255, choices=SUBS_STATUS, default=None, null=True, blank=True)
    # extra counts
    km_accounts = models.IntegerField(default=1)
    senior_managers = models.IntegerField(default=1)
    hiring_managers = models.IntegerField(default=1)
    hiring_team_members = models.IntegerField(default=1)
    contributors = models.IntegerField(default=1)
    open_positions = models.IntegerField(default=3)
    overall_price = models.IntegerField(default=50000)


class OTPRequested(models.Model):
    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE, related_name="otp_client")
    otp = models.CharField(max_length=6)


class ExtraAccountsPrice(models.Model):
    package = models.ForeignKey("clients.Package", on_delete=models.CASCADE, related_name="for_package")
    sm_count = models.IntegerField(default=1)
    sm_price = models.FloatField(default=1)
    hm_count = models.IntegerField(default=1)
    hm_price = models.FloatField(default=1)
    htm_count = models.IntegerField(default=1)
    htm_price = models.FloatField(default=1)
    tc_count = models.IntegerField(default=1)
    tc_price = models.FloatField(default=1)


class BillingDetail(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="billing_profile")
    # addr details
    billing_contact = models.CharField(max_length=255, default="None", blank=True, null=True)
    billing_email = models.CharField(max_length=255, default="None", blank=True, null=True)
    billing_phone = models.CharField(max_length=255, default="None", blank=True, null=True)
    addr_line_1 = models.TextField(default=None, blank=True, null=True)
    addr_line_2 = models.TextField(default=None, blank=True, null=True)
    city = models.CharField(max_length=255, default=None, blank=True, null=True)
    state = models.CharField(max_length=255, default=None, blank=True, null=True)
    pincode = models.CharField(max_length=10, default=None, blank=True, null=True)
    # cards details
    card_number = models.CharField(max_length=50, default=None, blank=True, null=True)
    name_on_card = models.CharField(max_length=100, default=None, blank=True, null=True)
    exp_date = models.CharField(max_length=5, default=None, blank=True, null=True)
    security = models.CharField(max_length=3, default=None, blank=True, null=True)

# handled for invoicing
class StripePayments(models.Model):
    customer = models.CharField(max_length=255)
    client = models.ForeignKey("clients.Client", on_delete=models.SET_NULL, default=None, blank=True, null=True, related_name="paying_client")
    payment_id = models.CharField(max_length=255, default=None, null=True, blank=True)
    payment_secret = models.CharField(max_length=255, default=None, null=True, blank=True)
    type = models.CharField(max_length=255, default="one-time")
    cycle = models.CharField(max_length=255, default=None, null=True, blank=True)
    amount = models.FloatField(default=0.0)
    created = models.DateTimeField(auto_now=True)
    updated = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, choices=SUBS_STATUS, default='incomplete')
    data = models.JSONField(default=get_json_default)
    price_breakdown = models.JSONField(default=get_json_default)


class StripeWebhookData(models.Model):
    data = models.JSONField()
    created = models.DateTimeField(auto_now=True)
    updated = models.DateTimeField(auto_now_add=True)
