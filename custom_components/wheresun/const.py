"""Constants for the WhereSun integration."""

DOMAIN = "wheresun"
DOMAIN_META = "wheresun_meta"
UNIQUE_ID = "wheresun"
SUBENTRY_HOUSE = "house"

CONF_ADDRESS = "address"
CONF_BLOCKS = "blocks"
CONF_BLOCKS_JSON = "blocks_json"
CONF_SHAPE = "shape"
CONF_DISPLAY_NAME = "display_name"
CONF_TIMEZONE = "timezone"

CONF_UPDATE_INTERVAL = "update_interval"
CONF_OUTPUT_PATH = "output_path"
CONF_WIDTH = "width"
CONF_HEIGHT = "height"
CONF_BG_COLOR = "bg_color"
CONF_PRIMARY_COLOR = "primary_color"
CONF_LIGHT_COLOR = "light_color"
CONF_SUN_COLOR = "sun_color"
CONF_MOON_COLOR = "moon_color"
CONF_SUN_RADIUS = "sun_radius"
CONF_MOON_RADIUS = "moon_radius"

DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_OUTPUT_PATH = "www/wheresun.svg"
DEFAULT_WIDTH = 100
DEFAULT_HEIGHT = 100
DEFAULT_BG_COLOR = "#1a1919"
DEFAULT_PRIMARY_COLOR = "#1b3024"
DEFAULT_LIGHT_COLOR = "#26bf75"
DEFAULT_SUN_COLOR = "#ffff66"
DEFAULT_MOON_COLOR = "#999999"
DEFAULT_SUN_RADIUS = 5
DEFAULT_MOON_RADIUS = 3

URL_BASE = "/wheresun"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "WhereSun-HomeAssistant/0.1.0"

PLATFORMS = ["sensor", "camera"]
