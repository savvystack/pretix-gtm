from bs4 import BeautifulSoup
from datetime import datetime, timezone
from django_scopes import scopes_disabled
from pretix.base.middleware import _parse_csp
from pretix.base.models import Event, Item, Organizer, Team, User

from pretix_gtm.signals import GTM_CSP_DIRECTIVES

from . import SoupTest, extract_form_fields

TEST_CONTAINER_ID = "GTM-12345ABC"


class CheckinListFormTest(SoupTest):
    @scopes_disabled()
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("dummy@dummy.dummy", "dummy")
        self.orga1 = Organizer.objects.create(name="CCC", slug="ccc")
        self.event1 = Event.objects.create(
            organizer=self.orga1,
            name="30C3",
            slug="30c3",
            date_from=datetime(2030, 12, 26, tzinfo=timezone.utc),
            plugins="pretix_gtm",
        )
        self.event1.settings.timezone = "US/Pacific"
        t = Team.objects.create(
            organizer=self.orga1, can_change_event_settings=True, can_view_orders=True
        )
        t.members.add(self.user)
        t.limit_events.add(self.event1)
        self.client.login(email="dummy@dummy.dummy", password="dummy")
        self.item_ticket = Item.objects.create(
            event=self.event1, name="Ticket", default_price=23, admission=True
        )

        response = self.client.get("/{}/{}/".format(self.orga1.slug, self.event1.slug))
        self.csp_baseline = _parse_csp(
            response.headers.get("Content-Security-Policy", default="")
        )

    def test_default_values(self):
        doc = self.get_doc(
            "/control/event/{}/{}/settings/gtm/".format(
                self.orga1.slug, self.event1.slug
            )
        )
        form_data = extract_form_fields(doc.select(".container-fluid form")[0])
        assert form_data["gtm_custom_csp_header"] == ""
        for k, v in GTM_CSP_DIRECTIVES.items():
            if k == "gtm_container_id" or k == "gtm_floodlight_config_id":
                assert form_data[k] == ""
            else:
                assert not form_data.get(k, False)

    def test_update(self):
        doc = self.get_doc(
            "/control/event/{}/{}/settings/gtm/".format(
                self.orga1.slug, self.event1.slug
            )
        )
        form_data = extract_form_fields(doc.select(".container-fluid form")[0])
        form_data["gtm_container_id"] = TEST_CONTAINER_ID
        doc = self.post_doc(
            "/control/event/{}/{}/settings/gtm/".format(
                self.orga1.slug, self.event1.slug
            ),
            form_data,
        )
        assert doc.select(".alert-success")
        form_data = extract_form_fields(doc.select(".container-fluid form")[0])
        assert form_data["gtm_container_id"] == TEST_CONTAINER_ID

        # test the update is persisted
        self.event1.settings.flush()
        assert self.event1.settings.gtm_container_id == TEST_CONTAINER_ID

    def test_gtm_script(self):
        self.event1.settings.gtm_container_id = TEST_CONTAINER_ID

        response = self.client.get("/{}/{}/".format(self.orga1.slug, self.event1.slug))
        doc = BeautifulSoup(response.render().content, "lxml")

        # test the GTM script has been inserted to the <head> of the page
        scripts = doc.select("head script")
        gtm_snippet = "(window,document,'script','dataLayer','{}')".format(
            TEST_CONTAINER_ID
        )
        assert any([gtm_snippet in str(tag) for tag in scripts])

    def test_csp_base(self):
        self.event1.settings.gtm_container_id = TEST_CONTAINER_ID
        csp = self._get_csp()
        self._assert_baseline_directives(csp)
        self._assert_gtm_directives(csp)

    def test_csp_for_features(self):
        self.event1.settings.gtm_container_id = TEST_CONTAINER_ID

        for feature, definition in GTM_CSP_DIRECTIVES.items():
            if feature == "gtm_container_id":
                pass
            elif feature == "gtm_floodlight_config_id":
                self.event1.settings[feature] = "FLOODLIGHT-XYZ"
                csp = self._get_csp()
                self._assert_baseline_directives(csp)
                self._assert_gtm_directives(csp)
                self._assert_feature_directives(
                    csp,
                    {
                        "img-src": [
                            "https://FLOODLIGHT-XYZ.fls.doubleclick.net",
                            "https://ad.doubleclick.net",
                            "https://ade.googlesyndication.com",
                        ],
                        "frame-src": ["https://FLOODLIGHT-XYZ.fls.doubleclick.net"],
                    },
                )

            else:
                self.event1.settings[feature] = True
                csp = self._get_csp()
                self._assert_baseline_directives(csp)
                self._assert_gtm_directives(csp)
                self._assert_feature_directives(csp, definition)

    def test_csp_for_customer_header(self):
        self.event1.settings.gtm_container_id = TEST_CONTAINER_ID
        self.event1.settings.gtm_custom_csp_header = "img-src https://img.co; frame-src https://frame1.co https://frame2.co; script-src 'unsafe-eval'"
        csp = self._get_csp()
        self._assert_baseline_directives(csp)
        self._assert_gtm_directives(csp)
        self._assert_feature_directives(
            csp,
            {
                "img-src": ["https://img.co"],
                "frame-src": ["https://frame1.co", "https://frame2.co"],
                "script-src": ["'unsafe-eval'"],
            },
        )

    def _get_csp(self):
        response = self.client.get("/{}/{}/".format(self.orga1.slug, self.event1.slug))
        return _parse_csp(response.headers.get("Content-Security-Policy", default=""))

    def _assert_baseline_directives(self, csp):
        for k, directives in self.csp_baseline.items():
            assert all([d in csp[k] for d in directives])

    def _assert_gtm_directives(self, csp):
        assert "'unsafe-inline'" in csp["script-src"]
        assert "https://www.googletagmanager.com" in csp["script-src"]
        assert "www.googletagmanager.com" in csp["img-src"]

    def _assert_feature_directives(self, csp, definition):
        for k, directives in definition.items():
            assert all([d in csp[k] for d in directives])
