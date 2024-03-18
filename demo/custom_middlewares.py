# models import
from dashboard.models import UserActivity

ACTIVITY_URLS = [
    "dashboard-api/login"
    "clients/client-data"
    "clients/delete-clients"
    "clients/suspend-clients"
    "clients/activate-clients"
]

class UserLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # logic that needs to be executed before the view is called. equivalent to process_request
        
        response = self.get_response(request)
        
        # logic that needs to be executed before the view is called  equivalent to process_response
        user_obj = response.data.get("user")
        if request.path_info in ACTIVITY_URLS and response.status_code in [200, 201]:
            UserActivity.objects.create(
                user=user_obj,
                activity_name=response.data.get("msg"),
                resp_data=response.data
            )
        return response

