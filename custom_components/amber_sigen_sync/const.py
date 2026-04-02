DOMAIN = "amber_sigen_sync"

SIGEN_AUTH_URL    = "https://api-aus.sigencloud.com/auth/oauth/token"
SIGEN_TARIFF_URL  = "https://api-aus.sigencloud.com/device/stationelecsetprice/save"

SIGEN_AUTH_HEADERS = {
    "Content-Type":   "application/x-www-form-urlencoded",
    "authorization":  "Basic c2lnZW46c2lnZW4=",
    "auth-client-id": "sigen",
    "client-server":  "aus",
    "sg-bui":         "1",
    "sg-env":         "1",
    "sg-pkg":         "sigen_app",
    "origin":         "https://app-aus.sigencloud.com",
}

SIGEN_POST_HEADERS = {
    "auth-client-id": "sigen",
    "client-server":  "aus",
    "sg-bui":         "1",
    "sg-env":         "1",
    "sg-pkg":         "sigen_app",
    "origin":         "https://app-aus.sigencloud.com",
}

CONF_SIGEN_USER       = "sigen_user"
CONF_SIGEN_PASS_ENC   = "sigen_pass_enc"
CONF_SIGEN_DEVICE_ID  = "sigen_device_id"
CONF_STATION_ID       = "station_id"
CONF_GENERAL_SENSOR   = "general_price_sensor"
CONF_FEED_IN_SENSOR   = "feed_in_price_sensor"
CONF_PLAN_NAME        = "plan_name"

DEFAULT_GENERAL_SENSOR  = "sensor.amber_express_home_general_price_detailed"
DEFAULT_FEED_IN_SENSOR  = "sensor.amber_express_home_feed_in_price_detailed"
DEFAULT_PLAN_NAME       = "Amber Live"
DEFAULT_STATION_ID      = None
