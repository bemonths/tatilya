"""Built-in installation profiles, independent of runtime destination selection."""
from . import thirty_a
DEFAULT_PROFILE = thirty_a
DEFAULT_DESTINATION_ID = DEFAULT_PROFILE.METADATA["id"]
# Profile assets (such as a reviewed beach-neighborhood mapping) are looked up by destination id.
PROFILES = {DEFAULT_DESTINATION_ID: DEFAULT_PROFILE}
