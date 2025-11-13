from werkzeug.routing import Rule
from retail.api.controllers.pet_service import services_list

service_rules = [
    Rule("/appointment/services", methods=["GET"], endpoint=services_list),
]
