from django.conf.urls import url
from portal.apps.users.views import SearchView, AuthenticatedView, UsageView, AllocationsView

app_name = 'users'
urlpatterns = [
    url(r'^$', SearchView.as_view(), name='user_search'),
    url(r'^auth/$', AuthenticatedView.as_view(), name='user_authenticated'),
    url(r'^allocations/$', AllocationsView.as_view(), name='user_allocations')
]
