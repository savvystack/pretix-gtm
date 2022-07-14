from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from pretix.base.forms import SettingsForm
from pretix.base.models import Event
from pretix.control.views.event import EventSettingsViewMixin, EventSettingsFormView

class TagManagerSettingsForm(SettingsForm):
    gtm_container_id = forms.CharField(
        label=_('Container ID'),
        help_text=_('It looks like GTM-XXXXXXX, where X is an uppercase letter or a digit.'),
        required=True
    )
    gtm_tag_ga4 = forms.BooleanField(
        label=_('Google Analytics: GA4'),
        required=False
    )
    gtm_tag_ua = forms.BooleanField(
        label=_('Google Analytics: Universal Analytics'),
        required=False
    )
    gtm_tag_google_optimize = forms.BooleanField(
        label=_('Google Optimize'),
        required=False
    )
    gtm_tag_google_ads_conversion = forms.BooleanField(
        label=_('Google Ads Conversion Tracking'),
        required=False
    )
    gtm_tag_google_ads_remarketing = forms.BooleanField(
        label=_('Google Ads Remarketing'),
        required=False
    )
    gtm_floodlight_config_id = forms.CharField(
        label=_('Floodlight Advertiser ID'),
        required=False
    )
    gtm_custom_js_variables = forms.BooleanField(
        label=_('Custom JavaScript Variables'),
        required=False
    )
    gtm_preview_mode = forms.BooleanField(
        label=_('Preview Mode'),
        required=False
    )
    gtm_custom_csp_header = forms.CharField(
        label=_('Directives'),
        help_text=_("Use space to separate key and value, use semicolon to separate each directive, don't include quotes."),
        required=False
    )

class SettingsView(EventSettingsViewMixin, EventSettingsFormView):
    model = Event
    form_class = TagManagerSettingsForm
    template_name = 'pretix_gtm/settings.html'
    permission = 'can_change_event_settings'

    def get_success_url(self) -> str:
        return reverse('plugins:pretix_gtm:settings', kwargs={
            'organizer': self.request.event.organizer.slug,
            'event': self.request.event.slug
        })
