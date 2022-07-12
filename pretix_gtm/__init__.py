from django.utils.translation import gettext_lazy

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")

__version__ = "0.0.1"


class PluginApp(PluginConfig):
    name = "pretix_gtm"
    verbose_name = "Google Tag Manager"

    class PretixPluginMeta:
        name = gettext_lazy("Google Tag Manager")
        author = "Raymond Jia"
        description = gettext_lazy("Provides support for Google Tag Manager.")
        visible = True
        version = __version__
        category = "INTEGRATION"
        compatibility = "pretix>=4.9.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = "pretix_gtm.PluginApp"
