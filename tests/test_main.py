from datetime import datetime, timezone
from django_scopes import scopes_disabled
from pretix.base.middleware import _merge_csp, _parse_csp, _render_csp
from pretix.base.models import Event, Item, Organizer, Team, User

from pretix_gtm.signals import GTM_CSP_DIRECTIVES

from . import SoupTest, extract_form_fields


class CheckinListFormTest(SoupTest):
    @scopes_disabled()
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("dummy@dummy.dummy", "dummy")
        self.orga = Organizer.objects.create(name="CCC", slug="ccc")
        self.event = Event.objects.create(
            organizer=self.orga,
            name="30C3",
            slug="30c3",
            date_from=datetime(2030, 12, 26, tzinfo=timezone.utc),
            plugins="plugins.pretix-gtm",
        )
        self.event.settings.timezone = "US/Pacific"
        t = Team.objects.create(
            organizer=self.orga, can_change_event_settings=True, can_view_orders=True
        )
        t.members.add(self.user)
        t.limit_events.add(self.event)
        self.client.login(email="dummy@dummy.dummy", password="dummy")
        self.item_ticket = Item.objects.create(
            event=self.event, name="Ticket", default_price=23, admission=True
        )

        store_front = self.client.get("/{}/{}/".format(self.orga.slug, self.event.slug))
        self.csp_baseline = _parse_csp(
            store_front.headers.get("Content-Security-Policy", default="")
        )

    def test_default_value(self):
        doc = self.get_doc(
            "/control/event/{}/{}/settings/gtm/".format(self.orga.slug, self.event.slug)
        )
        form_data = extract_form_fields(doc.select(".container-fluid form")[0])
        assert form_data["gtm_custom_csp_header"] == ""
        for k, v in GTM_CSP_DIRECTIVES.items():
            if k == "gtm_container_id" or k == "gtm_floodlight_config_id":
                assert form_data[k] == ""
            else:
                assert form_data.get(k, False) == False



        # store_front = self.client.get('/{}/{}/'.format(self.orga.slug, self.event.slug))
        # print(store_front.headers)

    # def test_create(self):
    #     doc = self.get_doc('/control/event/%s/%s/checkinlists/add' % (self.orga1.slug, self.event1.slug))
    #     form_data = extract_form_fields(doc.select('.container-fluid form')[0])
    #     form_data['name'] = 'All'
    #     form_data['all_products'] = 'on'
    #     doc = self.post_doc('/control/event/%s/%s/checkinlists/add' % (self.orga1.slug, self.event1.slug), form_data)
    #     assert doc.select(".alert-success")
    #     self.assertIn("All", doc.select("#page-wrapper table")[0].text)
    #     with scopes_disabled():
    #         assert self.event1.checkin_lists.get(
    #             name='All', all_products=True
    #         )

    # def test_update(self):
    #     doc = self.get_doc('/control/event/%s/%s/gtm/' % (self.orga1.slug, self.event1.slug))
    #     form_data = extract_form_fields(doc.select('.container-fluid form')[0])
    #     form_data['container_id'] = ''
    #     form_data['limit_products'] = str(self.item_ticket.pk)
    #     doc = self.post_doc('/control/event/%s/%s/checkinlists/%s/change' % (self.orga.slug, self.event.slug, cl.id),
    #                         form_data)
    #     assert doc.select(".alert-success")
    #     cl.refresh_from_db()
    #     assert not cl.all_products
    #     with scopes_disabled():
    #         assert list(cl.limit_products.all()) == [self.item_ticket]
