import logging
from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
from pretix.base.middleware import _merge_csp, _parse_csp, _render_csp
from pretix.base.models import Event
from pretix.control.signals import nav_event_settings
from pretix.presale.signals import html_head, html_page_header, process_response

logger = logging.getLogger(__name__)

GTM_SNIPPET_HEAD1 = """
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','"""

GTM_SNIPPET_HEAD2 = """');</script>
<!-- End Google Tag Manager -->
"""

GTM_SNIPPET_BODY = """
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
"""

GTM_CSP_DIRECTIVES = {
    "gtm_container_id": {
        "script-src": ["'unsafe-inline'", "https://www.googletagmanager.com"],
        "img-src": ["www.googletagmanager.com"],
    },
    "gtm_custom_js_variables": {
        "script-src": ["'unsafe-eval'"],
    },
    "gtm_preview_mode": {
        "script-src": ["https://tagmanager.google.com"],
        "style-src": ["https://tagmanager.google.com", "https://fonts.googleapis.com"],
        "img-src": ["https://ssl.gstatic.com", "https://www.gstatic.com"],
        "font-src": ["https://fonts.gstatic.com", "data:"],
    },
    "gtm_tag_ga4": {
        "script-src": ["*.googletagmanager.com"],
        "img-src": ["*.google-analytics.com", "*.googletagmanager.com"],
        "connect-src": [
            "*.google-analytics.com",
            "*.analytics.google.com",
            "*.googletagmanager.com",
        ],
    },
    "gtm_tag_ua": {
        "script-src": [
            "https://www.google-analytics.com",
            "https://ssl.google-analytics.com",
        ],
        "img-src": ["https://www.google-analytics.com"],
        "connect-src": ["https://www.google-analytics.com"],
    },
    "gtm_tag_google_optimize": {
        "script-src": ["https://www.google-analytics.com"],
    },
    "gtm_tag_google_ads_conversion": {
        "script-src": ["https://www.googleadservices.com", "https://www.google.com"],
        "img-src": ["https://googleads.g.doubleclick.net", "https://www.google.com"],
    },
    "gtm_tag_google_ads_remarketing": {
        "script-src": [
            "https://www.googleadservices.com",
            "https://googleads.g.doubleclick.net",
            "https://www.google.com",
        ],
        "img-src": ["https://www.google.com"],
        "frame-src": ["https://bid.g.doubleclick.net"],
    },
    "gtm_floodlight_config_id": {
        "img-src": [
            "https://{floodlight_config_id}.fls.doubleclick.net",
            "https://ad.doubleclick.net",
            "https://ade.googlesyndication.com",
        ],
        "frame-src": ["https://{floodlight_config_id}.fls.doubleclick.net"],
    },
}


@receiver(nav_event_settings, dispatch_uid="gtm_nav_settings")
def navbar_settings(sender, request, **kwargs):
    url = resolve(request.path_info)
    return [
        {
            "label": _("Tag Manager"),
            "url": reverse(
                "plugins:pretix_gtm:settings",
                kwargs={
                    "event": request.event.slug,
                    "organizer": request.organizer.slug,
                },
            ),
            "active": url.namespace == "plugins:pretix_gtm"
            and url.url_name.startswith("settings"),
        }
    ]


@receiver(html_head, dispatch_uid="gtm_html_head")
def html_head(sender: Event, **kwargs):
    container_id = sender.settings.get("gtm_container_id")
    if container_id:
        return GTM_SNIPPET_HEAD1 + container_id + GTM_SNIPPET_HEAD2


@receiver(html_page_header, dispatch_uid="gtm_html_page_header")
def html_page_header(sender: Event, **kwargs):
    container_id = sender.settings.get("gtm_container_id")
    if container_id:
        return GTM_SNIPPET_BODY.format(container_id)


@receiver(process_response, dispatch_uid="gtm_process_response")
def process_response(sender: Event, request, response, **kwargs):
    features = [
        "gtm_tag_ga4",
        "gtm_tag_ua",
        "gtm_tag_google_optimize",
        "gtm_tag_google_ads_conversion",
        "gtm_tag_google_ads_remarketing",
        "gtm_custom_js_variables",
        "gtm_preview_mode",
    ]
    h = {}
    if sender.settings.get("gtm_container_id"):
        _merge_csp(h, GTM_CSP_DIRECTIVES["gtm_container_id"])

        for feature in features:
            if sender.settings.get(feature, as_type=bool, default=False):
                _merge_csp(h, GTM_CSP_DIRECTIVES[feature])

        floodlight_config_id = sender.settings.get("gtm_floodlight_config_id")
        if floodlight_config_id:
            fld = {}
            for key, values in GTM_CSP_DIRECTIVES["gtm_floodlight_config_id"].items():
                fld[key] = [
                    v.format(floodlight_config_id=floodlight_config_id) for v in values
                ]
            _merge_csp(h, fld)

        custom_directives = sender.settings.get("gtm_custom_csp_header")
        if custom_directives:
            _merge_csp(h, _parse_csp(custom_directives))

        response["Content-Security-Policy"] = _render_csp(h)

    return response
