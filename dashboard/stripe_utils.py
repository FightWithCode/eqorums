import stripe
from django.conf import settings
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_package(name, price, company_id):
    obj = stripe.Product.create(
        name=name,
        active=True,
        description="Subscription for company: {}".format(company_id),
        default_price_data={
            "currency": "USD",
            "unit_amount_decimal": price,
            "recurring": {
                "interval": "day",

            }
        }
    )
    print(obj)


def get_price_from_package_id(product_id):
    price = None
    prices = stripe.Price.list()
    for i in prices:
        if i["product"] == product_id:
            price = i
            break
    return price


def create_checkout_session(user_id, price_id):
    domain_url = 'http://localhost:8000/'
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            client_reference_id=user_id,
            success_url=domain_url + 'success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + 'cancel/',
            payment_method_types=['card'],
            mode='subscription',
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                }
            ]
        )
        return checkout_session['id']
    except Exception as e:
        return None


def create_strip_customer(user):
    try:
        customer_obj = stripe.Customer.create(
            # address={
            #     "city": "New Delhi",
            #     "country": "India",
            #     "line1": "New Delhi",
            #     "line2": "New Delhi",
            #     "postal_code": "110046",
            #     "state": "Delhi"
            # },
            email=user.email,
            name=user.get_full_name(),
            phone=user.profile.phone_number,
        )
        user.profile.customer_id = customer_obj.id
        user.profile.save()
    except:
        return "Error while creating client!"


def get_or_create_stripe_customer(user):
    if user.profile.customer_id:
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            customer_obj = stripe.Customer.retrieve(user.profile.customer_id)
            return customer_obj["id"]
        except Exception as e:
            print(e)
            create_strip_customer(user)
            return user.profile.customer_id
    else:
        create_strip_customer(user)
        return user.profile.customer_id


def get_payment_method(customer):
    try:
        payment_methods = stripe.Customer.list_payment_methods(customer, type="card")
        for i in payment_methods:
            return i["id"]
    except:
        return None


def create_subscription(customer, price, default_payment_method):
    try:
        subscription = stripe.Subscription.create(
            customer=customer,
            items=[{"price": price}],
            default_payment_method=default_payment_method,
            trial_period_days=1
        )
        return subscription
    except Exception as e:
        print(e)
        return None


def create_price(name, amount):
    try:
        price = stripe.Price.create(unit_amount=int(amount * 100), currency='usd', recurring={"interval": "day"}, product_data={"name": "Starter for RK Studios"})
        return price["id"]
    except Exception as e:
        print(e)
        return None
