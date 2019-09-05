from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import GraphQLView

from gql.schema import schema


@csrf_exempt
def graphql_view(request):
    resp = GraphQLView.as_view(graphiql=settings.SHOW_GRAPHQL_DOC, schema=schema)(
        request
    )
    return resp
