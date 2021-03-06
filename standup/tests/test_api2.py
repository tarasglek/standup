import simplejson as json
from flask import render_template_string
from nose.tools import eq_
from standup.apps.api2.decorators import api_key_required
from standup.tests import BaseTestCase, project, status, team, user
from urllib import urlencode


class DecoratorsTestCase(BaseTestCase):
    def setUp(self):
        super(DecoratorsTestCase, self).setUp()

        @self.app.route('/_tests/_api/_protected', methods=['POST'])
        @api_key_required
        def protected():
            return render_template_string('Success!')

    def test_api_key_required(self):
        """Test the API key required decorator"""

        # Test with API key
        data = json.dumps({
            'api_key': self.app.config.get('API_KEY')})
        response = self.client.post('/_tests/_api/_protected', data=data,
                                    content_type='application/json')

        eq_(response.status_code, 200)

        # Test without API key
        data = json.dumps({})
        response = self.client.post('/_tests/_api/_protected', data=data,
                                    content_type='application/json')

        eq_(response.status_code, 403)


class TimelinesMixin(object):
    """Mixin to test standard timeline params."""

    def _url(self, query=None):
        if query:
            self.query.update(query)
        return '%s?%s' % (self.url, urlencode(self.query))

    def test_timeline(self):
        """Test the home_timeline endpoint"""
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            status(user=u, project=p, save=True)
        response = self.client.get(self._url())
        eq_(response.status_code, 200)
        eq_(response.content_type, 'application/json')

    def test_timeline_count(self):
        """Test the count parameter of home_timeline"""
        self.app.config['API2_TIMELINE_MAX_RESULTS'] = 50
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            for i in range(60):
                status(project=p, user=u, save=True)

        response = self.client.get(self._url())
        data = json.loads(response.data)
        eq_(len(data), 20)

        # Test with an acceptable count
        response = self.client.get(self._url(dict(count=50)))
        data = json.loads(response.data)
        eq_(len(data), 50)

        # Test with a count that is too large
        response = self.client.get(self._url(dict(count=60)))
        eq_(response.status_code, 400)

        # Test with a count that is too small
        response = self.client.get(self._url(dict(count=0)))
        eq_(response.status_code, 400)

        # Test with an invalid count
        response = self.client.get(self._url(dict(count='a')))
        eq_(response.status_code, 400)

    def test_timeline_since_id(self):
        """Test the since_id parameter of home_timeline"""
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            for i in range(30):
                status(project=p, user=u, save=True)

        response = self.client.get(self._url(dict(since_id=10, count=20)))
        data = json.loads(response.data)
        eq_(data[19]['id'], 11)

        response = self.client.get(self._url(dict(since_id=10, count=10)))
        data = json.loads(response.data)
        eq_(data[9]['id'], 21)

        response = self.client.get(self._url(dict(since_id=10, count=30)))
        data = json.loads(response.data)
        eq_(len(data), 20)
        eq_(data[19]['id'], 11)

        response = self.client.get(self._url(dict(since_id=0)))
        eq_(response.status_code, 400)

        response = self.client.get(self._url(dict(since_id='a')))
        eq_(response.status_code, 400)

    def test_timeline_max_id(self):
        """Test the max_id parameter of home_timeline"""
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            for i in range(30):
                status(project=p, user=u, save=True)

        response = self.client.get(self._url(dict(max_id=10, count=20)))
        data = json.loads(response.data)
        eq_(len(data), 10)
        eq_(data[0]['id'], 10)

        response = self.client.get(self._url(dict(max_id=10, since_id=5)))
        data = json.loads(response.data)
        eq_(len(data), 5)

        response = self.client.get(self._url(dict(max_id=0)))
        eq_(response.status_code, 400)

        response = self.client.get(self._url(dict(max_id='a')))
        eq_(response.status_code, 400)

    def test_timeline_trim_user(self):
        """Test the trim_user parameter of home_timeline"""
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            status(user=u, project=p, save=True)

        response = self.client.get(self._url())
        data = json.loads(response.data)
        eq_(data[0]['user'], u.dictify())

        response = self.client.get(self._url(dict(trim_user=1)))
        data = json.loads(response.data)
        eq_(data[0]['user'], u.id)

    def test_timeline_trim_project(self):
        """Test the trim_project parameter of home_timeline"""
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            status(user=u, project=p, save=True)

        response = self.client.get(self._url())
        data = json.loads(response.data)
        eq_(data[0]['project'], p.dictify())

        response = self.client.get(self._url(dict(trim_project=1)))
        data = json.loads(response.data)
        eq_(data[0]['project'], p.id)

    def test_timeline_include_replies(self):
        """Test the include_replies parameter of home_timeline"""
        with self.app.app_context():
            u = user(save=True, team={})
            p = project(save=True)
            for i in range(10):
                s = status(project=p, user=u, save=True)
            for i in range(10):
                status(project=p, user=u, reply_to=s, save=True)

        response = self.client.get(self._url())
        data = json.loads(response.data)
        eq_(len(data), 10)

        response = self.client.get(self._url(dict(include_replies=1)))
        data = json.loads(response.data)
        eq_(len(data), 20)


class HomeTimelinesTestCase(BaseTestCase, TimelinesMixin):
    def setUp(self):
        super(HomeTimelinesTestCase, self).setUp()
        self.url = '/api/v2/statuses/home_timeline.json'
        self.query = {}


class UserTimelinesTestCase(BaseTestCase, TimelinesMixin):
    def setUp(self):
        super(UserTimelinesTestCase, self).setUp()
        self.url = '/api/v2/statuses/user_timeline.json'
        self.query = {'screen_name': 'jdoe'}

    def test_no_user_query(self):
        self.query = {}
        response = self.client.get(self._url())
        eq_(response.status_code, 400)

    def test_user_404(self):
        self.query = {'screen_name': 'xxx'}
        response = self.client.get(self._url())
        eq_(response.status_code, 404)

    def test_timeline_filters_user(self):
        """Test the timeline only shows the passed in user."""
        with self.app.app_context():
            u = user(save=True)
            status(user=u, project=None, save=True)
            u2 = user(username='janedoe', email='jane@doe.com',
                      slug='janedoe', save=True)
            status(user=u2, project=None, save=True)

        response = self.client.get(self._url())
        data = json.loads(response.data)
        eq_(len(data), 1)
        eq_(data[0]['user'], u.dictify())

    def test_timeline_filter_by_user_id(self):
        with self.app.app_context():
            u = user(save=True)
        self.query = {'user_id': u.id}
        response = self.client.get(self._url())
        eq_(response.status_code, 200)


class ProjectTimelinesTestCase(BaseTestCase, TimelinesMixin):
    def setUp(self):
        super(ProjectTimelinesTestCase, self).setUp()
        self.url = '/api/v2/statuses/project_timeline.json'
        self.query = {'slug': 'test-project'}

    def test_no_project_query(self):
        self.query = {}
        response = self.client.get(self._url())
        eq_(response.status_code, 400)

    def test_project_404(self):
        self.query = {'slug': 'xxx'}
        response = self.client.get(self._url())
        eq_(response.status_code, 404)

    def test_timeline_filters_project(self):
        """Test the timeline only shows the passed in project."""
        with self.app.app_context():
            u = user(save=True)
            p = project(save=True)
            status(user=u, project=p, save=True)
            p2 = project(name='Test Project 2', slug='test-project-2',
                         save=True)
            status(user=u, project=p2, save=True)

        response = self.client.get(self._url())
        data = json.loads(response.data)
        eq_(len(data), 1)
        eq_(data[0]['project'], p.dictify())

    def test_timeline_filter_by_project_id(self):
        with self.app.app_context():
            p = project(save=True)
        self.query = {'project_id': p.id}
        response = self.client.get(self._url())
        eq_(response.status_code, 200)


class TeamTimelinesTestCase(BaseTestCase, TimelinesMixin):
    def setUp(self):
        super(TeamTimelinesTestCase, self).setUp()
        self.url = '/api/v2/statuses/team_timeline.json'
        self.query = {'slug': 'test-team'}

    def test_no_team_query(self):
        self.query = {}
        response = self.client.get(self._url())
        eq_(response.status_code, 400)

    def test_team_404(self):
        self.query = {'slug': 'xxx'}
        response = self.client.get(self._url())
        eq_(response.status_code, 404)

    def test_timeline_filters_team(self):
        """Test the timeline only shows the passed in team."""
        with self.app.app_context():
            u = user(save=True, team={})
            u2 = user(username='janedoe', email='jane@doe.com',
                      slug='janedoe', save=True, team={'name': 'XXX',
                                                       'slug': 'xxx'})
            p = project(save=True)
            status(user=u, project=p, save=True)
            status(user=u2, project=p, save=True)

        response = self.client.get(self._url(dict(team_id=u.teams[0].id)))
        data = json.loads(response.data)
        eq_(len(data), 1)
        eq_(data[0]['user'], u.dictify())

    def test_timeline_filter_by_team_id(self):
        with self.app.app_context():
            t = team(save=True)
        self.query = {'team_id': t.id}
        response = self.client.get(self._url())
        eq_(response.status_code, 200)
